"""benchmark/runner.py -- production rollout orchestrator.

Runs one experiment (a batch of rollouts) against the REAL webclone apps.
Per rollout, the five-stage unit:

  SETUP     reset browser state (clear localStorage -> /config -> assert clean /finish)
  RUN       detached `claude -p` (never a subagent), experiment header + task prompt
  GATE      exit code + non-empty answer + minimum tool activity + throttle detection
  TEARDOWN  capture /finish byte-exact; copy the ~/.claude transcript verbatim
  EVALUATE  REAL's WebCloneEvaluator (jmespath exact; llm_boolean judged via claude)

Everything is timed (setup, run, teardown, eval; run is the headline number).
Artifacts per rollout: prompt.txt, result_raw.json, trajectory.jsonl, finish.json,
evaluation.json, timing.json. Logs are written for a human to tail.

Rate-limit policy (Claude Max 20x, shared 5h window + weekly caps): fixed buffer
between rollouts, reactive throttle detection with a parsed-or-default wait, and
throttled attempts re-queued rather than scored.

Usage:
  python3 runner.py preflight
  python3 runner.py run --experiment gen-experiential [--only TASK_ID] [--buffer 45]
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BENCH)
from harness import OC, read_finish_text, _diff_nonempty, _load_real_evaluator  # noqa: E402
from runner_common import (AGENT_EFFORT, AGENT_MODEL, DATA, LOGS,
    MANIFEST, WORKROOT)
from runner_experiments import EXPERIMENTS
from runner_rollout import run_rollout
from runner_study import cmd_p4study, cmd_p5warmup

def _tab_ids(oc):
    """Set of tab ids currently in the MCP group (best-effort)."""
    try:
        return set(int(x) for x in re.findall(r'"tabId":\s*(\d+)', oc.tabs() or ""))
    except Exception:
        return set()


from runner_util import Log, child_env, write_json

def cmd_run(a):
    manifest = json.load(open(MANIFEST))
    exp = EXPERIMENTS[a.experiment]
    if exp["system"] not in ("ocic", "cinc"):
        sys.exit("experiment %s: no adapter for system %s" % (a.experiment, exp["system"]))
    order = list(manifest[exp["split"]])
    if a.only:
        wanted = [x.strip() for x in a.only.split(",") if x.strip()]
        order = [t for t in order if t in wanted]
        if not order: sys.exit("task(s) %s not in %s" % (a.only, exp["split"]))
    if a.limit: order = order[:a.limit]
    tasks = manifest["tasks"]

    logpath = os.path.join(LOGS, "%s_%s.log" % (a.experiment, datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
    log = Log(logpath)
    log("EXPERIMENT %s: %d rollout(s), model=%s effort=%s, buffer=%ds" %
        (a.experiment, len(order), AGENT_MODEL, AGENT_EFFORT, a.buffer))
    log("log file: %s" % logpath)
    t0 = now()
    outcomes = {}
    for i, tid in enumerate(order, 1):
        try:
            outcomes[tid] = run_rollout(a.experiment, exp, tasks[tid], i, len(order), log, a.buffer)
        except Exception as e:
            # A rollout failure must never kill the experiment: log, mark, move on.
            log("  ERROR rollout %s: %r. Continuing with the next task." % (tid, e))
            outcomes[tid] = "error"
        write_json(os.path.join(DATA, a.experiment, "status.json"),
                   {"experiment": a.experiment, "done": i, "total": len(order),
                    "outcomes": outcomes, "updated": datetime.datetime.now().isoformat(timespec="seconds")})
        if i < len(order) and outcomes[tid] != "skipped":
            log("  buffer %ds (rate-limit headroom)" % a.buffer)
            time.sleep(a.buffer)
    total_min = (now() - t0) / 60.0
    completed = [t for t, o in outcomes.items() if o == "completed"]
    summary = {"experiment": a.experiment, "started": datetime.datetime.fromtimestamp(t0).isoformat(timespec="seconds"),
               "wall_clock_min": round(total_min, 2), "rollouts": outcomes,
               "completed": len(completed), "skipped": len(order) - len(completed)}
    write_json(os.path.join(DATA, a.experiment, "summary.json"), summary)
    log("EXPERIMENT %s DONE in %.1fmin (%d completed, %d skipped). summary.json written."
        % (a.experiment, total_min, summary["completed"], summary["skipped"]))

def cmd_preflight(_a):
    ok = True
    def chk(name, fn):
        nonlocal ok
        try:
            v = fn()
            print("  OK  %-34s %s" % (name, v if v is not True else ""))
        except Exception as e:
            ok = False
            print("  FAIL %-34s %s" % (name, e))
    print("preflight:")
    chk("manifest", lambda: "%d train / %d test" % (
        len(json.load(open(MANIFEST))["train_order"]), len(json.load(open(MANIFEST))["test_order"])))
    chk("claude CLI", lambda: subprocess.run(["claude", "--version"], capture_output=True, text=True,
                                             env=child_env()).stdout.strip())
    chk("effort flag", lambda: "--effort" in subprocess.run(["claude", "--help"], capture_output=True,
                                                            text=True, env=child_env()).stdout or exec('raise ValueError("missing")'))
    def _tabs():
        oc = OC()
        try:
            first = (oc.tabs() or "").strip().split("\n")[0]
            return "OCIC alive, %d tab(s)" % len(json.loads(first).get("availableTabs", []))
        finally:
            oc.close()
    chk("OCIC MCP (Brave)", _tabs)
    import urllib.request
    apps = {}
    try:
        man = json.load(open(MANIFEST))
        apps = {t["app"]: t["url"] for t in man["tasks"].values()}
    except Exception:
        pass
    for app, url in sorted(apps.items()):
        chk("app " + app, lambda u=url: urllib.request.urlopen(u, timeout=15).status)
    chk("jmespath", lambda: __import__("jmespath").__name__)
    chk("evaluator loads", lambda: bool(_load_real_evaluator()))
    chk("workroot", lambda: os.makedirs(WORKROOT, exist_ok=True) or WORKROOT)
    print("preflight:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preflight"); p.set_defaults(fn=cmd_preflight)
    r = sub.add_parser("run")
    r.add_argument("--experiment", required=True, choices=sorted(EXPERIMENTS))
    r.add_argument("--only", default=None)
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--buffer", type=int, default=45)
    r.set_defaults(fn=cmd_run)
    s4 = sub.add_parser("p4study")
    s4.add_argument("--arm", required=True, choices=["expert", "experiential"])
    s4.add_argument("--timeout", type=int, default=5400,
                    help="hard cap for the expert study session (s)")
    s4.add_argument("--effort", default=AGENT_EFFORT,
                    choices=["low", "medium", "high", "xhigh", "max"],
                    help="effort for the expert STUDY session only "
                         "(train segments and fork rollouts stay at %s)" % AGENT_EFFORT)
    s4.set_defaults(fn=cmd_p4study)
    s5 = sub.add_parser("p5warmup")
    s5.add_argument("--force", action="store_true")
    s5.set_defaults(fn=cmd_p5warmup)
    a = ap.parse_args()
    a.fn(a)

if __name__ == "__main__":
    main()
