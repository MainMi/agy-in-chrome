# Split out of runner.py — pure refactor, behavior unchanged.

from __future__ import annotations

import os, re, sys

BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BENCH)
from harness import OC, read_finish_text, _diff_nonempty, _load_real_evaluator  # noqa: E402

MANIFEST = os.path.join(BENCH, "tasks_manifest.json")
DATA = os.path.join(BENCH, "data")
LOGS = os.path.join(BENCH, "logs")
WORKROOT = os.path.expanduser("~/.bench_rollouts")  # outside any git repo: no project context leaks in

AGENT_MODEL = "sonnet"
AGENT_EFFORT = "medium"
JUDGE_MODEL = "sonnet"          # llm_boolean judge (REAL default is gpt-4o; no OPENAI_API_KEY here)
ROLLOUT_TIMEOUT_S = 1200        # hard cap per claude run
MIN_TOOL_CALLS = 3              # lazy-run gate
THROTTLE_RE = re.compile(
    r"usage limit|rate.?limit|limit (?:will )?reset|limit reached|overloaded|"
    r"weekly limit|too many requests|(?<!\d)429(?!\d)", re.I)
RESET_HINT_RE = re.compile(r"reset(?:s|ting)?\s+(?:at\s+)?([0-9]{1,2}(?::[0-9]{2})?\s*[ap]m)", re.I)
THROTTLE_DEFAULT_WAIT_S = 20 * 60
THROTTLE_MAX_WAIT_S = 65 * 60
