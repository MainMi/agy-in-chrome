# Split out of runner.py — pure refactor, behavior unchanged.

import json
import os
import re
import time

from runner_common import WORKROOT
from harness import read_finish_text, _diff_nonempty

def _tab_attachable(oc, tab):
    """A wedged tab (crashed page or a browser interstitial) rejects debugger
    attach; probe before trusting it."""
    try:
        r = oc.js(tab, "'ok'") or ""
        return "ok" in r and "attach" not in r.lower()
    except Exception:
        return False

def ocic_fresh_tab(oc, app_url):
    """Create a FRESH tab for every rollout — never reuse. A freshly created
    tab is the active/selected tab of its window, so it renders and its input
    is not throttled. Reuse is what caused the ~5s-per-click stalls: the
    extension now activates a tab only on creation, so a reused tab that has
    since been backgrounded (another origin's tab became active) drives slow.
    Fresh-per-rollout also removes any risk of adopting a stale/interstitial
    tab. The caller closes it on teardown (ocic_close_tab)."""
    made = oc.call("tabs_create_mcp", {})
    m = re.search(r"Tab ID:\s*(\d+)", made or "")
    if not m:
        raise RuntimeError("could not create a workspace tab: %r" % (made or "")[:200])
    # Do NOT probe attachability here: a fresh tab is on chrome://newtab, which
    # the debugger cannot attach to. ocic_seed navigates it to the app origin
    # (attachable) right after; a genuine failure surfaces there and the setup
    # retry handles it.
    return int(m.group(1))

def ocic_close_tab(oc, tab):
    """Best-effort close of a rollout's tab on teardown, so tabs do not pile up
    and nothing is left to reuse."""
    if tab is None:
        return
    try:
        oc.call("tabs_close_mcp", {"tabId": tab})
    except Exception:
        pass

def ocic_seed(oc, tab, app_url, run_id, task_id, log):
    """Full reset: root -> clear -> /config -> assert /finish clean -> back to root."""
    oc.navigate(tab, app_url + "/"); time.sleep(1.4)
    oc.js(tab, "localStorage.clear(); 'ok'"); time.sleep(0.4)
    oc.navigate(tab, "%s/config?run_id=%s&task_id=%s&latency=0" % (app_url, run_id, task_id)); time.sleep(1.8)
    txt = read_finish_text(oc, tab, app_url)
    env = json.loads(txt)
    dirty = _diff_nonempty(env)
    if dirty:
        log("  WARN seed found dirty buckets %s, clearing again" % dirty)
        oc.navigate(tab, app_url + "/"); time.sleep(1.0)
        oc.js(tab, "localStorage.clear(); 'ok'"); time.sleep(0.4)
        oc.navigate(tab, "%s/config?run_id=%s&task_id=%s&latency=0" % (app_url, run_id, task_id)); time.sleep(1.8)
        txt = read_finish_text(oc, tab, app_url)
        env = json.loads(txt)
        dirty = _diff_nonempty(env)
        if dirty:
            raise RuntimeError("environment not fresh after two resets: %s" % dirty)
    oc.navigate(tab, app_url + "/"); time.sleep(1.2)
    return True

def ocic_capture_finish(oc, tab, app_url, out_path):
    txt = read_finish_text(oc, tab, app_url)
    json.loads(txt)  # must be valid
    with open(out_path, "wb") as f:
        f.write(txt.encode("utf-8"))
    env = json.loads(txt)
    oc.navigate(tab, app_url + "/"); time.sleep(0.8)
    return env, len(txt)

# ---- browser (official Claude-in-Chrome adapter, EXP-1B) ---------------------
# The official extension has no spawnable MCP server, so seed/teardown run as
# tiny detached `claude --chrome` orchestration calls (chosen over an
# AppleScript toggle or a CDP relaunch). Documented caveat: /finish capture is
# model-mediated (the orchestration agent copies the JSON out), validated by
# json.loads + run_id + diff-structure checks, not byte-exact like OCIC's
# MCP read.

CINC_ORCH_DIR = os.path.join(WORKROOT, "_cinc_orchestration")
_FINISH_RE = re.compile(r"<FINISH_JSON>\s*(\{.*\})\s*</FINISH_JSON>", re.S)

