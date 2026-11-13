# Split out of runner.py — pure refactor, behavior unchanged.

import datetime
import json
import os
import re
import shutil
import sys
import tarfile
import time

from runner_common import (AGENT_EFFORT, AGENT_MODEL, BENCH, DATA,
    LOGS, MANIFEST, WORKROOT)
from runner_eval import evaluate, find_transcript
from runner_experiments import populate_experience
from runner_ocic import (ocic_capture_finish, ocic_close_tab,
    ocic_fresh_tab, ocic_seed)
from runner_prompts2 import (P4_EXPERT_STUDY_PROMPT, P4_TRAIN_CONT,
    P4_TRAIN_HEADER)
from runner_util import Log, claude_json, write_json
from harness import OC

def cmd_p4study(a):
    """Phase-4 study session: build the checkpoint that fork rollouts resume.

    --arm expert       one session, expert recordings mounted at ./experience/,
                       deep-internalization prompt; browser at its own
                       discretion (never mentioned); duration tracked.
    --arm experiential one session that PERFORMS the 6 train tasks
                       sequentially (standard per-task setup/seed/teardown;
                       plain --resume between segments keeps one session id).

    Output: data/phase4/<arm>_study/{study.json, trajectory.jsonl,
    workdir_snapshot.tar.gz, result artifacts}. Model/effort: the global
    AGENT_MODEL/AGENT_EFFORT — identical to every other experiment.
    """
    man = json.load(open(MANIFEST))
    arm = a.arm
    outdir = os.path.join(DATA, "phase4", "%s_study" % arm)
    os.makedirs(outdir, exist_ok=True)
    log = Log(os.path.join(LOGS, "p4study_%s_%s.log" % (
        arm, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))))
    workdir = os.path.join(WORKROOT, "p4_%s_study" % arm)
    shutil.rmtree(workdir, ignore_errors=True)
    os.makedirs(workdir, exist_ok=True)
    # Study effort is configurable (--effort); the expert internalization study
    # runs at "max" by request. Model is ALWAYS the global AGENT_MODEL (sonnet).
    # Train segments (experiential arm) and all fork rollouts stay at the
    # uniform AGENT_EFFORT (medium).
    study_effort = a.effort
    study = {"arm": arm, "workdir": workdir, "model": AGENT_MODEL,
             "effort": study_effort if arm == "expert" else AGENT_EFFORT,
             "started": datetime.datetime.now().isoformat(timespec="seconds")}
    t0 = now()

    if arm == "expert":
        populate_experience(workdir, "expert", log)
        oc = OC()
        try: tabs_before = _tab_ids(oc)
        finally: oc.close()
        log("expert study launched (model=%s effort=%s, timeout %ds); browser at its discretion"
            % (AGENT_MODEL, study_effort, a.timeout))
        parsed, out, err, code, dur = claude_json(
            P4_EXPERT_STUDY_PROMPT, cwd=workdir, timeout=a.timeout,
            effort=study_effort)
        open(os.path.join(outdir, "result_raw.json"), "w").write(out)
        if err.strip():
            open(os.path.join(outdir, "claude_stderr.log"), "w").write(err)
        sid = (parsed or {}).get("session_id")
        result = (parsed or {}).get("result") or ""
        if code != 0 or not sid or not result.strip():
            sys.exit("study session failed: exit=%s sid=%s empty_result=%s"
                     % (code, sid, not result.strip()))
        study.update(session_id=sid, study_run_s=round(dur, 1),
                     num_turns=(parsed or {}).get("num_turns"))
        # close any tabs the study opened (browser use was its own choice)
        oc = OC()
        try:
            opened = _tab_ids(oc) - tabs_before
            for t in sorted(opened):
                try: oc.call("tabs_close_mcp", {"tabId": t})
                except Exception: pass
        finally:
            oc.close()
        study["tabs_opened_during_study"] = len(opened)
        log("study done: %.1fmin, %s turns, sid %s, %d tab(s) opened by the agent"
            % (dur / 60.0, study["num_turns"], sid, len(opened)))
    elif arm == "experiential":
        tasks = man["tasks"]; order = list(man["train_order"])
        sid = None; segments = []
        for i, tid in enumerate(order, 1):
            task = tasks[tid]
            run_id = "p4study_%s" % tid
            oc = OC()
            try:
                tab = ocic_fresh_tab(oc, task["url"])
                ocic_seed(oc, tab, task["url"], run_id, tid, log)
            finally:
                oc.close()
            log("SEGMENT %d/%d %s (tab %d)" % (i, len(order), tid, tab))
            if sid is None:
                prompt = P4_TRAIN_HEADER.format(tab=tab, app_name=task["app"],
                                                app_url=task["url"], goal=task["goal"])
                extra = []
            else:
                prompt = P4_TRAIN_CONT.format(tab=tab, app_name=task["app"],
                                              app_url=task["url"], goal=task["goal"])
                extra = ["--resume", sid]
            parsed, out, err, code, dur = claude_json(prompt, extra_args=extra, cwd=workdir)
            open(os.path.join(outdir, "%s_result_raw.json" % tid), "w").write(out)
            if err.strip():
                open(os.path.join(outdir, "%s_stderr.log" % tid), "w").write(err)
            new_sid = (parsed or {}).get("session_id")
            result = (parsed or {}).get("result") or ""
            if code != 0 or not new_sid or not result.strip():
                sys.exit("segment %s failed: exit=%s sid=%s empty_result=%s"
                         % (tid, code, new_sid, not result.strip()))
            if sid is None:
                sid = new_sid
            elif new_sid != sid:
                sys.exit("session id changed on resume (%s -> %s); aborting" % (sid, new_sid))
            oc = OC()
            try:
                env_state, _ = ocic_capture_finish(
                    oc, tab, task["url"], os.path.join(outdir, "%s_finish.json" % tid))
                ocic_close_tab(oc, tab)
            finally:
                oc.close()
            try:
                ev = evaluate(tid, env_state, result)
            except Exception as e:
                ev = {"task_id": tid, "error": str(e)}
            write_json(os.path.join(outdir, "%s_evaluation.json" % tid), ev)
            segments.append({"task": tid, "passed": ev.get("passed"),
                             "run_s": round(dur, 1),
                             "num_turns": (parsed or {}).get("num_turns")})
            log("  segment done %.1fmin, eval %s" % (dur / 60.0, ev.get("passed")))
            if i < len(order):
                time.sleep(20)
        study.update(session_id=sid, segments=segments)
    else:
        sys.exit("unknown arm %r" % arm)

    traj = find_transcript(study["session_id"])
    if traj:
        shutil.copyfile(traj, os.path.join(outdir, "trajectory.jsonl"))
    else:
        log("WARN study transcript not found for %s" % study["session_id"])
    snap = os.path.join(outdir, "workdir_snapshot.tar.gz")
    with tarfile.open(snap, "w:gz") as tf:
        tf.add(workdir, arcname=".")
    study["duration_s"] = round(now() - t0, 1)
    study["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
    write_json(os.path.join(outdir, "study.json"), study)
    log("STUDY %s COMPLETE in %.1fmin: sid=%s. study.json + snapshot written to %s"
        % (arm, study["duration_s"] / 60.0, study["session_id"], os.path.relpath(outdir, BENCH)))

P5_WARMUP_TASKS = {"dashdish": "dashdish-4", "zilloft": "zilloft-8"}

def cmd_p5warmup(a):
    """Phase-5 atomic warm-ups: per website, ONE train task performed in ONE
    session (standard seed/teardown, silent single-task header), checkpointed
    for website-routed forking. Chosen tasks: dashdish-4 (broadest cart and
    checkout coverage) and zilloft-8 (broadest filter coverage); train set only.
    Output: data/phase5/warmup_<app>/{study.json, workdir_snapshot.tar.gz,
    trajectory.jsonl, finish/evaluation artifacts}."""
    man = json.load(open(MANIFEST))
    log = Log(os.path.join(LOGS, "p5warmup_%s.log" %
                           datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
    for app, tid in P5_WARMUP_TASKS.items():
        outdir = os.path.join(DATA, "phase5", "warmup_%s" % app)
        if os.path.isfile(os.path.join(outdir, "study.json")) and not a.force:
            log("warmup_%s already exists, skipping (use --force to redo)" % app)
            continue
        os.makedirs(outdir, exist_ok=True)
        task = man["tasks"][tid]
        workdir = os.path.join(WORKROOT, "p5_warmup_%s" % app)
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)
        run_id = "p5warmup_%s" % tid
        # A warm-up checkpoint must contain CLEAN experience: retry once on
        # any infrastructure failure (browser drop, dead tab, capture error)
        # and require the task to actually PASS. A session whose memory is
        # "the browser broke" would poison every fork that resumes it.
        ev = None; sid = None
        for attempt in (1, 2):
            workdir_ok = True
            shutil.rmtree(workdir, ignore_errors=True)
            os.makedirs(workdir, exist_ok=True)
            try:
                oc = OC()
                try:
                    tab = ocic_fresh_tab(oc, task["url"])
                    ocic_seed(oc, tab, task["url"], run_id, tid, log)
                finally:
                    oc.close()
                log("WARMUP %s: task %s attempt %d (tab %d)" % (app, tid, attempt, tab))
                prompt = P4_TRAIN_HEADER.format(tab=tab, app_name=task["app"],
                                                app_url=task["url"], goal=task["goal"])
                parsed, out, err, code, dur = claude_json(prompt, cwd=workdir)
                open(os.path.join(outdir, "result_raw.json"), "w").write(out)
                if err.strip():
                    open(os.path.join(outdir, "stderr.log"), "w").write(err)
                sid = (parsed or {}).get("session_id")
                result = (parsed or {}).get("result") or ""
                if code != 0 or not sid or not result.strip():
                    raise RuntimeError("run gate: exit=%s sid=%s" % (code, sid))
                oc = OC()
                try:
                    env_state, _ = ocic_capture_finish(oc, tab, task["url"],
                                                       os.path.join(outdir, "finish.json"))
                    ocic_close_tab(oc, tab)
                finally:
                    oc.close()
                ev = evaluate(tid, env_state, result)
                write_json(os.path.join(outdir, "evaluation.json"), ev)
                # A clean completion is valid warm-up experience whether or not
                # it PASSED: the fork inherits the experience of ATTEMPTING the
                # task (phase-4 kept its failed segments too). Retry only on
                # INFRASTRUCTURE failure (handled by the exceptions above:
                # browser drop, teardown error, empty result, exit != 0).
                log("  warmup %s completed (eval passed=%s) - accepting as experience"
                    % (app, ev.get("passed")))
                break
            except Exception as e:
                log("  warmup %s attempt %d failed: %r" % (app, attempt, e))
                if attempt == 2:
                    sys.exit("warmup %s failed twice; aborting" % app)
                time.sleep(60)
        traj = find_transcript(sid)
        if traj:
            shutil.copyfile(traj, os.path.join(outdir, "trajectory.jsonl"))
        snap = os.path.join(outdir, "workdir_snapshot.tar.gz")
        with tarfile.open(snap, "w:gz") as tf:
            tf.add(workdir, arcname=".")
        write_json(os.path.join(outdir, "study.json"),
                   {"arm": "warmup_%s" % app, "task": tid, "workdir": workdir,
                    "session_id": sid, "model": AGENT_MODEL, "effort": AGENT_EFFORT,
                    "run_s": round(dur, 1), "num_turns": (parsed or {}).get("num_turns"),
                    "passed": ev.get("passed"),
                    "created": datetime.datetime.now().isoformat(timespec="seconds")})
        log("WARMUP %s DONE: %.1fmin, %s turns, eval %s, sid %s" %
            (app, dur / 60.0, (parsed or {}).get("num_turns"), ev.get("passed"), sid))

