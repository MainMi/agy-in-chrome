# Split out of runner.py — pure refactor, behavior unchanged.

import datetime
import json
import os
import shutil
import tarfile
import time

from runner_common import (AGENT_EFFORT, AGENT_MODEL, BENCH, DATA,
    MIN_TOOL_CALLS, THROTTLE_RE, WORKROOT)
from runner_cinc import (cinc_capture_finish, cinc_capture_finish_parity,
    cinc_ensure_tab, cinc_seed, cinc_seed_parity)
from runner_eval import evaluate, find_transcript, trajectory_stats
from runner_experiments import populate_experience
from runner_ocic import (ocic_capture_finish, ocic_close_tab,
    ocic_fresh_tab, ocic_seed)
from runner_prompts2 import load_recipe
from runner_util import (claude_json, throttle_wait_s, throttled,
    write_json)
from harness import OC

def run_rollout(exp_name, exp, task, idx, total, log, buffer_s):
    task_id = task["id"]
    rollout_dir = os.path.join(DATA, exp_name, "%s_r1" % task_id)
    if os.path.exists(os.path.join(rollout_dir, "timing.json")) and \
       os.path.exists(os.path.join(rollout_dir, "evaluation.json")):
        log("ROLLOUT %d/%d %s SKIP (artifacts complete)" % (idx, total, task_id))
        return "skipped"
    os.makedirs(rollout_dir, exist_ok=True)
    fork_args = []
    if exp.get("phase4") or exp.get("p5route"):
        # Fork rollout: restore the study session's workdir VERBATIM at the
        # SAME absolute path (forks only resolve from the session's own
        # project cwd), then fork the checkpointed session. Wiped and
        # re-restored per rollout: independent rollouts, identical start.
        # phase4: fixed study env. p5route: website-matched atomic warm-up.
        if exp.get("p5route"):
            sdir = os.path.join(DATA, "phase5", "warmup_%s" % task["app"])
        else:
            sdir = os.path.join(DATA, "phase4", exp["phase4"] + "_study")
        study = json.load(open(os.path.join(sdir, "study.json")))
        workdir = study["workdir"]
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)
        with tarfile.open(os.path.join(sdir, "workdir_snapshot.tar.gz")) as tf:
            try:
                tf.extractall(workdir, filter="data")
            except TypeError:  # older python without the filter parameter
                tf.extractall(workdir)
        fork_args = ["--resume", study["session_id"], "--fork-session"]
        log("  fork of %s (%s), workdir snapshot restored" %
            (study["session_id"][:8],
             ("warmup_%s" % task["app"]) if exp.get("p5route") else exp["phase4"] + " study"))
    else:
        workdir = os.path.join(WORKROOT, exp_name, "%s_r1" % task_id)
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)
        if exp.get("experience"):
            populate_experience(workdir, exp["experience"], log)
    run_id = "%s_%s_r1" % (exp_name, task_id)
    T = {"task_id": task_id, "experiment": exp_name, "run_id": run_id, "attempts": []}

    attempt = 0
    while True:
        attempt += 1
        A = {"attempt": attempt}
        log("ROLLOUT %d/%d %s attempt %d (%s | %s | %s)" %
            (idx, total, task_id, attempt, task["difficulty"], task["challengeType"], task["grading"]))

        # 1 SETUP (transient page/MCP hiccups get one retry before the task errors out)
        A["t_setup_start"] = now()
        if exp["system"] == "cinc":
            tab = None
            try:
                if exp.get("cinc_parity"):
                    tab = cinc_ensure_tab(task["url"], log, force_new=(attempt > 1))
                    cinc_seed_parity(tab, task["url"], run_id, task_id, log)
                else:
                    cinc_seed(task["url"], run_id, task_id, log)
            except Exception as e:
                if attempt < 2:
                    log("  setup failed (%r), retrying rollout" % e)
                    A["outcome"] = "setup_failed"; T["attempts"].append(A)
                    time.sleep(15)
                    continue
                raise
        else:
            oc = OC()
            try:
                tab = ocic_fresh_tab(oc, task["url"])
                ocic_seed(oc, tab, task["url"], run_id, task_id, log)
            except Exception as e:
                if attempt < 2:
                    log("  setup failed (%r), retrying rollout" % e)
                    A["outcome"] = "setup_failed"; T["attempts"].append(A)
                    oc.close()
                    time.sleep(15)
                    continue
                raise
            finally:
                oc.close()
        A["t_setup_end"] = now()
        log("  setup ok, %s fresh, %.1fs" % ("chrome (cinc seed)" if tab is None else "tab %d" % tab,
                                             A["t_setup_end"] - A["t_setup_start"]))

        # 2 RUN
        fmt_kw = {}
        if exp.get("recipe"):
            # recipe text is passed as a format VALUE (its own braces, if any,
            # are never re-processed); authored by the isolated generator.
            fmt_kw["recipe"] = load_recipe(exp["recipe"], task["app"],
                                           exp.get("recipe_dir"))
        prompt = exp["header"].format(tab=tab, app_name=task["app"], app_url=task["url"],
                                      goal=task["goal"], **fmt_kw)
        open(os.path.join(rollout_dir, "prompt.txt"), "w").write(prompt)
        log("  claude launched (model=%s effort=%s)" % (AGENT_MODEL, AGENT_EFFORT))
        A["t_run_start"] = now()
        parsed, out, err, code, dur = claude_json(prompt, extra_args=exp["claude_args"] + fork_args, cwd=workdir)
        A["t_run_end"] = now()
        open(os.path.join(rollout_dir, "result_raw.json"), "w").write(out)
        if err.strip():
            open(os.path.join(rollout_dir, "claude_stderr.log"), "w").write(err)

        result_text = (parsed or {}).get("result") or ""
        session_id = (parsed or {}).get("session_id")
        num_turns = (parsed or {}).get("num_turns")
        is_error = bool((parsed or {}).get("is_error"))

        # throttle -> wait and retry, never scored. ONLY checked when the run
        # actually failed: a successful exit-0 run with a result is never a
        # throttle, and matching its stdout JSON invites false positives
        # (numbers like ttft_ms=1429 once matched a bare '429' pattern and
        # discarded a good rollout). Persist the RAW evidence (what matched,
        # full stdout/stderr/result) to a non-overwritten path so every event
        # is verifiable: real usage cap, 429 burst, 529 overload, or regex FP.
        run_failed = (code != 0) or is_error or not result_text.strip()
        if run_failed and throttled(out, err, result_text):
            wait = throttle_wait_s(out, err, result_text)
            blob = "%s\n%s\n%s" % (out or "", err or "", result_text or "")
            mm = THROTTLE_RE.search(blob)
            matched = mm.group(0) if mm else "?"
            evdir = os.path.join(BENCH, "throttle_evidence")
            os.makedirs(evdir, exist_ok=True)
            evp = os.path.join(evdir, "%s_%s_%s.txt" % (
                exp_name, task_id, datetime.datetime.now().strftime("%H%M%S")))
            open(evp, "w").write(
                "matched: %r\nexit=%s is_error=%s\n\n=== STDOUT ===\n%s\n\n=== STDERR ===\n%s\n\n=== RESULT ===\n%s\n"
                % (matched, code, is_error, out, err, result_text))
            log("  THROTTLED (regex matched %r). Waiting %dm then retrying. Attempt not scored. Evidence: %s"
                % (matched, wait // 60, os.path.relpath(evp, BENCH)))
            A["outcome"] = "throttled"; T["attempts"].append(A)
            time.sleep(wait)
            continue

        # 3 GATE
        gate = []
        if code != 0: gate.append("exit=%s" % code)
        if is_error: gate.append("is_error")
        if not result_text.strip(): gate.append("empty result")
        log("  run done, exit %s, %.1fmin, turns %s" % (code, dur / 60.0, num_turns))
        if gate and attempt < 2:
            log("  GATE FAILED (%s), one retry" % ", ".join(gate))
            A["outcome"] = "gate_failed:" + ",".join(gate); T["attempts"].append(A)
            time.sleep(20)
            continue

        # 4 TEARDOWN
        A["t_teardown_start"] = now()
        if exp["system"] == "cinc":
            if exp.get("cinc_parity"):
                env_state, fbytes = cinc_capture_finish_parity(
                    tab, task["url"], os.path.join(rollout_dir, "finish.json"), run_id)
            else:
                env_state, fbytes = cinc_capture_finish(task["url"],
                                                        os.path.join(rollout_dir, "finish.json"), run_id)
        else:
            oc = OC()
            try:
                env_state, fbytes = ocic_capture_finish(oc, tab, task["url"],
                                                        os.path.join(rollout_dir, "finish.json"))
                ocic_close_tab(oc, tab)  # teardown: remove the rollout's tab
            finally:
                oc.close()
        traj = find_transcript(session_id) if session_id else None
        stats = {"tool_calls": 0, "execute_code_calls": 0, "model": None}
        if traj:
            shutil.copyfile(traj, os.path.join(rollout_dir, "trajectory.jsonl"))
            stats = trajectory_stats(os.path.join(rollout_dir, "trajectory.jsonl"))
        else:
            log("  WARN transcript not found for session %s" % session_id)
        A["t_teardown_end"] = now()
        if stats["tool_calls"] < MIN_TOOL_CALLS:
            gate.append("suspect_lazy(tool_calls=%d)" % stats["tool_calls"])
        if stats["execute_code_calls"] and not exp["execute_code_allowed"]:
            gate.append("VIOLATION:execute_code_used=%d" % stats["execute_code_calls"])
        # cinc's header bans javascript_tool (its execute_code analog)
        if exp["system"] == "cinc" and stats["javascript_tool_calls"] and not exp["execute_code_allowed"]:
            gate.append("VIOLATION:javascript_tool_used=%d" % stats["javascript_tool_calls"])
        log("  teardown ok, finish %dB, steps %d, execute_code %d%s" %
            (fbytes, stats["tool_calls"], stats["execute_code_calls"],
             (", GATE FLAGS: " + ",".join(gate)) if gate else ""))

        # 5 EVALUATE
        A["t_eval_start"] = now()
        try:
            ev = evaluate(task_id, env_state, result_text)
        except RuntimeError as e:
            if "JUDGE_THROTTLED" in str(e):
                log("  judge throttled, waiting 15m and re-evaluating")
                time.sleep(900)
                ev = evaluate(task_id, env_state, result_text)
            else:
                ev = {"task_id": task_id, "error": str(e)}
        except Exception as e:
            ev = {"task_id": task_id, "error": str(e)}
        A["t_eval_end"] = now()
        write_json(os.path.join(rollout_dir, "evaluation.json"), ev)
        passed = ev.get("passed")
        log("  eval %s (%s)" % ("PASS" if passed else ("FAIL" if passed is False else "ERROR"),
            ", ".join("%s:%s" % (c["description"][:28], "ok" if c["passed"] else "X")
                      for c in ev.get("criteria", [])) or ev.get("error", "")[:80]))

        A["outcome"] = "completed"
        T["attempts"].append(A)
        T.update({
            "gate_flags": gate, "session_id": session_id, "exit_code": code,
            "num_turns": num_turns, "tool_calls": stats["tool_calls"],
            "execute_code_calls": stats["execute_code_calls"],
            "javascript_tool_calls": stats["javascript_tool_calls"], "agent_model": stats["model"],
            "passed": passed,
            "durations_s": {
                "setup": round(A["t_setup_end"] - A["t_setup_start"], 2),
                "run": round(A["t_run_end"] - A["t_run_start"], 2),
                "teardown": round(A["t_teardown_end"] - A["t_teardown_start"], 2),
                "eval": round(A["t_eval_end"] - A["t_eval_start"], 2),
                "rollout_total": round(A["t_eval_end"] - A["t_setup_start"], 2),
            },
        })
        write_json(os.path.join(rollout_dir, "timing.json"), T)
        log("  rollout total %.1fmin (run %.1fmin). artifacts -> %s" %
            (T["durations_s"]["rollout_total"] / 60.0, T["durations_s"]["run"] / 60.0,
             os.path.relpath(rollout_dir, BENCH)))
        return "completed"

# ---- commands ------------------------------------------------------------------

