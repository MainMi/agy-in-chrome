"""Benchmark rollout harness for the REAL web-clone tasks.

A model-free MCP stdio client to Open Claude in Chrome's `host/mcp-server.js`,
used for the orchestrator-side steps that must NOT be part of the agent's task prompt:

  - seed   : reset the app origin (localStorage.clear -> /config -> assert clean)
  - finish : read /finish and write the env_state to disk BYTE-EXACT (copy-free)
  - eval   : run REAL's own WebCloneEvaluator against a captured /finish

The task itself is run by a separate agent; this harness never does the task.

Usage:
  python harness.py seed   --tab 123 --app https://evals-networkin.vercel.app --run-id RID --task-id networkin-1
  python harness.py finish --tab 123 --app https://evals-networkin.vercel.app --out /path/finish.json
  python harness.py eval   --task-id networkin-1 --finish /path/finish.json --out /path/evaluation.json [--response-from-trajectory /path/traj.jsonl]
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time

# Paths are resolved relative to this file so the harness runs from anywhere in
# the repo. Override REAL_SRC / OCIC_NODE via env if your layout differs.
from harness_oc import OC

def _unwrap(s):
    """javascript_tool returns the last expression's value as text; strings arrive
    JSON-quoted. Unwrap one layer so we get the raw value."""
    s = (s or "").strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        try: return json.loads(s)
        except json.JSONDecodeError: pass
    return s


# ---- diff / freshness -------------------------------------------------------
_SUBKEYS = ("added", "updated", "deleted", "removed", "modified")

def _diff_nonempty(env_state):
    """Return {diffKey: {sub: count}} for any non-empty change bucket."""
    dirty = {}
    for k, v in env_state.items():
        if isinstance(v, dict):
            for sub in _SUBKEYS:
                val = v.get(sub)
                if val:
                    dirty.setdefault(k, {})[sub] = (len(val) if hasattr(val, "__len__") else val)
    return dirty


def read_finish_text(oc, tab, app, timeout_s=25):
    """Navigate to /finish and poll until the client-rendered <pre> holds valid
    JSON (first cold load of an app can take several seconds)."""
    oc.navigate(tab, app.rstrip("/") + "/finish")
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        time.sleep(1.2)
        last = oc.js(tab, "(document.querySelector('pre')||{}).innerText||'NO_PRE'")
        if last and last.strip().startswith("{"):
            try:
                json.loads(last)
                return last
            except json.JSONDecodeError:
                pass
    raise RuntimeError("finish page never yielded JSON (last=%r)" % (last or "")[:120])


# ---- commands ---------------------------------------------------------------
def cmd_seed(a):
    oc = OC()
    try:
        app = a.app.rstrip("/")
        oc.navigate(a.tab, app + "/"); time.sleep(1.3)
        oc.js(a.tab, "localStorage.clear(); 'ok'"); time.sleep(0.4)
        oc.navigate(a.tab, "%s/config?run_id=%s&task_id=%s&latency=0" % (app, a.run_id, a.task_id)); time.sleep(1.8)
        txt = read_finish_text(oc, a.tab, app)
        env = json.loads(txt)
        dirty = _diff_nonempty(env)
        oc.navigate(a.tab, app + "/"); time.sleep(1.0)   # leave the tab on the feed for the agent
        out = {"tab": a.tab, "run_id": a.run_id, "task_id": a.task_id,
               "fresh": not dirty, "dirty_buckets": dirty, "diff_keys": list(env.keys())}
        print(json.dumps(out, indent=2))
        return 0 if not dirty else 3
    finally:
        oc.close()


def cmd_finish(a):
    oc = OC()
    try:
        txt = read_finish_text(oc, a.tab, a.app)
        if txt == "NO_PRE" or not txt.strip().startswith("{"):
            print("ERROR: no /finish JSON (got %r)" % txt[:80]); return 2
        json.loads(txt)  # validate
        data = txt.encode("utf-8")
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "wb") as f: f.write(data)
        h = 0
        for ch in txt: h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        env = json.loads(txt)
        print(json.dumps({"out": a.out, "bytes": len(data), "chars": len(txt), "hash": h,
                          "diff_keys": list(env.keys()),
                          "nonempty": _diff_nonempty(env)}, indent=2))
        return 0
    finally:
        oc.close()


def _ser(x):
    if isinstance(x, dict): return {k: _ser(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [_ser(v) for v in x]
    return x


def _last_assistant_text(traj_path):
    """Best-effort: the final assistant text in a subagent transcript."""
    last = ""
    try:
        for line in open(traj_path, encoding="utf-8"):
            try: rec = json.loads(line)
            except Exception: continue
            msg = rec.get("message") or rec
            if (rec.get("type") == "assistant" or msg.get("role") == "assistant"):
                c = msg.get("content")
                if isinstance(c, str): last = c
                elif isinstance(c, list):
                    t = "".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
                    if t.strip(): last = t
    except FileNotFoundError:
        pass
    return last


def _load_real_evaluator():
    """Load REAL's EXACT WebCloneEvaluator + TaskConfig by file path, stubbing only
    the unused LLM util so we bypass the heavy agisdk package chain (gymnasium /
    playwright). The grading code that runs is REAL's own, unmodified."""
    import importlib.util, types
    WC = os.path.join(REAL_SRC, "agisdk/REAL/browsergym/webclones")
    for name in ["agisdk", "agisdk.REAL", "agisdk.REAL.browsergym", "agisdk.REAL.browsergym.webclones"]:
        if name not in sys.modules:
            m = types.ModuleType(name); m.__path__ = []; sys.modules[name] = m
    utils = types.ModuleType("agisdk.REAL.browsergym.webclones.utils")
    def generate_from_model(prompt=None, model=None, **k):
        raise RuntimeError("LLM judge unavailable in offline harness (jmespath tasks unaffected)")
    utils.generate_from_model = generate_from_model
    sys.modules["agisdk.REAL.browsergym.webclones.utils"] = utils
    try:
        import requests  # noqa: F401
    except Exception:
        sys.modules["requests"] = types.ModuleType("requests")
    def _load(modname, path):
        spec = importlib.util.spec_from_file_location(modname, path)
        mod = importlib.util.module_from_spec(spec); sys.modules[modname] = mod
        spec.loader.exec_module(mod); return mod
    tc = _load("agisdk.REAL.browsergym.webclones.task_config", os.path.join(WC, "task_config.py"))
    ev = _load("agisdk.REAL.browsergym.webclones.evaluate", os.path.join(WC, "evaluate.py"))
    return tc.TaskConfig, ev.WebCloneEvaluator


def cmd_eval(a):
    TaskConfig, WebCloneEvaluator = _load_real_evaluator()
    import io, contextlib

    env_state = json.load(open(a.finish))
    model_response = a.response or ""
    if a.response_from_trajectory:
        model_response = _last_assistant_text(a.response_from_trajectory)

    tc = TaskConfig(a.task_id)
    ev = WebCloneEvaluator(task_config=tc)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        reward, done, message, info = ev.evaluate(env_state=env_state, model_response=model_response)

    evals = tc.get_evals()
    results = info.get("results", []) if isinstance(info, dict) else []
    crit = []
    for i, e in enumerate(evals):
        r = results[i] if i < len(results) else (None, None)
        crit.append({"description": getattr(e, "description", ""), "type": e.type,
                     "query": getattr(e, "query", ""), "rubric": getattr(e, "rubric", ""),
                     "expected_value": e.expected_value, "passed": bool(r[0]),
                     "detail": _ser(r[1])})
    passed = bool(crit) and all(c["passed"] for c in crit)
    out = {"task_id": a.task_id, "evaluator": "agisdk.REAL WebCloneEvaluator",
           "reward": reward, "passed": passed, "done": bool(done), "message": message,
           "model_response": model_response, "criteria": crit,
           "grader_stdout": buf.getvalue()}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=2)
    print(json.dumps({"out": a.out, "task_id": a.task_id, "reward": reward,
                      "passed": passed, "criteria": [(c["description"], c["passed"]) for c in crit]}, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seed"); s.add_argument("--tab", type=int, required=True)
    s.add_argument("--app", required=True); s.add_argument("--run-id", dest="run_id", required=True)
    s.add_argument("--task-id", dest="task_id", required=True); s.set_defaults(fn=cmd_seed)
    f = sub.add_parser("finish"); f.add_argument("--tab", type=int, required=True)
    f.add_argument("--app", required=True); f.add_argument("--out", required=True); f.set_defaults(fn=cmd_finish)
    e = sub.add_parser("eval"); e.add_argument("--task-id", dest="task_id", required=True)
    e.add_argument("--finish", required=True); e.add_argument("--out", required=True)
    e.add_argument("--response", default=""); e.add_argument("--response-from-trajectory", dest="response_from_trajectory", default="")
    e.set_defaults(fn=cmd_eval)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()

