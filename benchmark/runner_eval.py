# Split out of runner.py — pure refactor, behavior unchanged.

import json
import os
import re
import sys
import time

from runner_common import JUDGE_MODEL
from runner_util import claude_json, now, throttled
from harness import _load_real_evaluator

def find_transcript(session_id, timeout_s=30):
    """Locate <session_id>.jsonl under ~/.claude/projects (slug-independent)."""
    root = os.path.expanduser("~/.claude/projects")
    deadline = now() + timeout_s
    while now() < deadline:
        for dirpath, _dirs, files in os.walk(root):
            if session_id + ".jsonl" in files:
                return os.path.join(dirpath, session_id + ".jsonl")
        time.sleep(1.5)
    return None

def trajectory_stats(path):
    steps = 0; exec_code = 0; js_tool = 0; model = None
    try:
        for line in open(path, encoding="utf-8"):
            try: rec = json.loads(line)
            except Exception: continue
            msg = rec.get("message") or {}
            if rec.get("type") == "assistant":
                model = msg.get("model") or model
                for b in (msg.get("content") or []):
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        steps += 1
                        name = b.get("name") or ""
                        if "execute_code" in name:
                            exec_code += 1
                        elif "javascript_tool" in name:
                            js_tool += 1
    except FileNotFoundError:
        pass
    return {"tool_calls": steps, "execute_code_calls": exec_code,
            "javascript_tool_calls": js_tool, "model": model}

# ---- evaluation --------------------------------------------------------------

_EVAL_CACHE = {}

def evaluate(task_id, env_state, model_response):
    """REAL's evaluator, exact code; llm_boolean judged through claude."""
    if "cls" not in _EVAL_CACHE:
        TaskConfig, WebCloneEvaluator = _load_real_evaluator()
        evmod = sys.modules["agisdk.REAL.browsergym.webclones.evaluate"]
        def judge(prompt="", model=None, **kw):
            parsed, out, err, code, _d = claude_json(
                prompt + "\n\nAnswer with only the number.",
                extra_args=[], timeout=120, model=JUDGE_MODEL, effort="low")
            if throttled(out, err):
                raise RuntimeError("JUDGE_THROTTLED")
            txt = (parsed or {}).get("result", "") if isinstance(parsed, dict) else ""
            m = re.search(r"[01](?:\.\d+)?", txt or "")
            if not m:
                raise RuntimeError("judge returned no number: %r" % (txt or out)[:120])
            return m.group(0)
        evmod.generate_from_model = judge
        _EVAL_CACHE["cls"] = (TaskConfig, WebCloneEvaluator)
    TaskConfig, WebCloneEvaluator = _EVAL_CACHE["cls"]
    import io, contextlib
    tc = TaskConfig(task_id)
    ev = WebCloneEvaluator(task_config=tc)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        reward, done, message, info = ev.evaluate(env_state=env_state, model_response=model_response)
    evals = tc.get_evals(); results = info.get("results", [])
    crit = []
    for i, e in enumerate(evals):
        r = results[i] if i < len(results) else (None, None)
        detail = r[1]
        if isinstance(detail, tuple): detail = list(detail)
        crit.append({"description": getattr(e, "description", ""), "type": e.type,
                     "query": getattr(e, "query", ""), "rubric": getattr(e, "rubric", ""),
                     "expected_value": e.expected_value, "passed": bool(r[0])})
    return {"task_id": task_id, "evaluator": "agisdk.REAL WebCloneEvaluator",
            "judge_model": "claude:" + JUDGE_MODEL + " (REAL default gpt-4o unavailable, no OPENAI_API_KEY)",
            "reward": reward, "passed": all(c["passed"] for c in crit) and bool(crit),
            "message": message, "model_response": model_response,
            "criteria": crit, "grader_stdout": buf.getvalue()}

# ---- the rollout unit ---------------------------------------------------------

