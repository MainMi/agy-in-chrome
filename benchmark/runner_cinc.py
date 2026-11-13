# Split out of runner.py — pure refactor, behavior unchanged.

import datetime
import json
import os
import re
import time

from runner_common import AGENT_MODEL, DATA
from runner_ocic import CINC_ORCH_DIR, _FINISH_RE
from runner_util import claude_json, write_json

def cinc_orch_call(prompt, timeout=300):
    os.makedirs(CINC_ORCH_DIR, exist_ok=True)
    parsed, out, err, code, dur = claude_json(
        prompt, extra_args=["--chrome"], timeout=timeout, cwd=CINC_ORCH_DIR,
        model=AGENT_MODEL, effort="low")
    return (parsed or {}).get("result") or "", code, out, err, dur

def cinc_seed(app_url, run_id, task_id, log):
    prompt = """I'm testing my own demo web app and need its browser state reset before a
test run. Please do this with the "claude-in-chrome" browser tools (load them
with one ToolSearch call if they are deferred):

1. Get the tab context (createIfEmpty true) and create a fresh tab.
2. In that tab, open %s/
3. Clear the app's storage: run localStorage.clear(); sessionStorage.clear()
   with javascript_tool.
4. Open %s/config?run_id=%s&task_id=%s&latency=0
   (this URL seeds the app's test fixture; it is part of the app).
5. After ~2 seconds, open %s/finish and read the JSON it shows (get_page_text).
6. Check both: config.run_id equals "%s", and every bucket under
   "differences" has empty added/deleted/updated. If any bucket is dirty,
   repeat steps 2-5 once.
7. Close the tab you created.

End your reply with the single line "SEED OK" if the check passed, otherwise
"SEED FAIL: <one-line reason>.""" % (app_url, app_url, run_id, task_id, app_url, run_id)
    text, code, out, err, _dur = cinc_orch_call(prompt)
    if code != 0 or "SEED OK" not in text or "SEED FAIL" in text:
        tail = (text.strip().splitlines() or [""])[-1]
        raise RuntimeError("cinc seed failed (exit %s): %s" % (code, (tail or err)[:200]))
    return True

_CINC_TAB_CACHE = os.path.join(DATA, "exp1b-cinc-parity", "workspace_tab.json")

def cinc_ensure_tab(app_url, log, force_new=False):
    """Parity setup: ONE persistent workspace tab for the whole experiment.
    Returns its tabId. Reuses the cached tab when possible; the seed step
    verifies it is actually usable (a dead tab fails the seed, and the retry
    path calls this again with force_new=True). The tab is created ONCE so the
    operator can manually focus it and it stays the window's active tab for
    every rollout (no tab churn, no visibility ambiguity)."""
    if not force_new and os.path.isfile(_CINC_TAB_CACHE):
        try:
            tab = json.load(open(_CINC_TAB_CACHE))["tab"]
            log("  cinc parity: reusing workspace tab %s" % tab)
            return tab
        except Exception:
            pass
    prompt = """I'm setting up a browser test. Using the "claude-in-chrome" browser tools
(load them with one ToolSearch call if they are deferred):

1. Get the tab context (createIfEmpty true).
2. If the tab group already has a tab, pick the FIRST one and navigate it to
   %s/ . Otherwise create ONE new tab and navigate it to %s/ .
3. Do not create any additional tabs. Do not close anything.

End your reply with the single line "TAB_ID: <number>" for the tab you used.""" % (app_url, app_url)
    text, code, out, err, _dur = cinc_orch_call(prompt)
    m = re.search(r"TAB_ID:\s*(\d+)", text or "")
    if code != 0 or not m:
        raise RuntimeError("cinc parity tab setup failed (exit %s): %s" % (code, (text or err)[-200:]))
    tab = int(m.group(1))
    os.makedirs(os.path.dirname(_CINC_TAB_CACHE), exist_ok=True)
    write_json(_CINC_TAB_CACHE, {"tab": tab, "created": datetime.datetime.now().isoformat(timespec="seconds")})
    log("  cinc parity: workspace tab %d ready on %s" % (tab, app_url))
    return tab

def cinc_seed_parity(tab, app_url, run_id, task_id, log):
    """Seed IN the persistent workspace tab; never create or close tabs.
    Leaves the tab parked on the app root, ready for the agent."""
    prompt = """I'm testing my own demo web app and need its browser state reset before a
test run. Use the "claude-in-chrome" browser tools (load them with one
ToolSearch call if they are deferred). Work ONLY in the existing tab with
tabId %d. Do NOT create, close, or switch tabs.

1. Navigate tabId %d to %s/
2. Clear the app's storage there: run localStorage.clear(); sessionStorage.clear()
   with javascript_tool.
3. Navigate to %s/config?run_id=%s&task_id=%s&latency=0
   (this URL seeds the app's test fixture; it is part of the app).
4. After ~2 seconds, navigate to %s/finish and read the JSON shown (get_page_text).
5. Check both: config.run_id equals "%s", and every bucket under
   "differences" has empty added/deleted/updated. If any bucket is dirty,
   repeat steps 1-4 once.
6. Navigate tabId %d back to %s/ and stop.

End your reply with the single line "SEED OK" if the check passed, otherwise
"SEED FAIL: <one-line reason>.""" % (tab, tab, app_url, app_url, run_id, task_id,
                                     app_url, run_id, tab, app_url)
    text, code, out, err, _dur = cinc_orch_call(prompt)
    if code != 0 or "SEED OK" not in text or "SEED FAIL" in text:
        tail = (text.strip().splitlines() or [""])[-1]
        raise RuntimeError("cinc parity seed failed (exit %s): %s" % (code, (tail or err)[:200]))
    return True

def cinc_capture_finish_parity(tab, app_url, out_path, run_id):
    """Read /finish IN the persistent workspace tab, then park it back on the
    app root. The tab is never closed."""
    prompt = """I'm testing my own demo web app and need to read its end-of-run state.
Use the "claude-in-chrome" browser tools (load them with one ToolSearch call
if they are deferred). Work ONLY in the existing tab with tabId %d. Do NOT
create, close, or switch tabs.

1. Navigate tabId %d to %s/finish and read the JSON it shows with
   get_page_text (if it is not valid JSON yet, wait 2 seconds and read again).
2. Give me back the COMPLETE raw JSON exactly as shown, character for
   character, no commentary and no truncation, wrapped like this:
<FINISH_JSON>
{ ...the json... }
</FINISH_JSON>
3. Navigate tabId %d back to %s/ and stop.""" % (tab, tab, app_url, tab, app_url)
    last_text = ""
    for attempt in (1, 2):
        text, code, out, err, _dur = cinc_orch_call(prompt)
        last_text = text or err
        m = _FINISH_RE.search(text or "")
        if m:
            try:
                env = json.loads(m.group(1))
                if (env.get("config") or {}).get("run_id") == run_id:
                    raw = m.group(1)
                    open(out_path, "wb").write(raw.encode("utf-8"))
                    return env, len(raw)
            except Exception:
                pass
        time.sleep(4)
    raise RuntimeError("cinc parity finish capture failed twice: %s" % last_text[-200:])

def cinc_capture_finish(app_url, out_path, run_id):
    prompt = """I'm testing my own demo web app and need to read its end-of-run state.
Please do this with the "claude-in-chrome" browser tools (load them with one
ToolSearch call if they are deferred):

1. Get the tab context (createIfEmpty true) and create a fresh tab.
2. Open %s/finish in it and read the JSON it shows with get_page_text (if it
   is not valid JSON yet, wait 2 seconds and read again).
3. Give me back the COMPLETE raw JSON exactly as shown, character for
   character, no commentary and no truncation, wrapped like this:
<FINISH_JSON>
{ ...the json... }
</FINISH_JSON>
4. Close the tab you created.""" % app_url
    last_text = ""
    for attempt in (1, 2):
        text, code, out, err, _dur = cinc_orch_call(prompt)
        last_text = text or err
        m = _FINISH_RE.search(text or "")
        if m:
            try:
                env = json.loads(m.group(1))
                if (env.get("config") or {}).get("run_id") == run_id:
                    raw = m.group(1)
                    open(out_path, "wb").write(raw.encode("utf-8"))
                    return env, len(raw)
            except Exception:
                pass
        time.sleep(4)
    raise RuntimeError("cinc finish capture failed twice: %s" % last_text[-200:])

# ---- transcript --------------------------------------------------------------

