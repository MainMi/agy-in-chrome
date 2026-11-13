# Split out of runner.py — pure refactor, behavior unchanged.

import datetime
import json
import os
import re
import signal
import subprocess
import time

from runner_common import (AGENT_EFFORT, AGENT_MODEL, RESET_HINT_RE,
    ROLLOUT_TIMEOUT_S, THROTTLE_DEFAULT_WAIT_S, THROTTLE_MAX_WAIT_S,
    THROTTLE_RE)

def now(): return time.time()

def ts(): return datetime.datetime.now().strftime("%H:%M:%S")

class Log:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.f = open(path, "a", buffering=1)
    def __call__(self, msg):
        line = "[%s] %s" % (ts(), msg)
        self.f.write(line + "\n")
        print(line, flush=True)

def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)

def child_env():
    """Env for nested claude: strip the CLAUDECODE markers or the child refuses/nests wrong."""
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("CLAUDECODE") or k.startswith("CLAUDE_CODE"):
            env.pop(k, None)
    return env

def claude_json(prompt, extra_args=None, timeout=ROLLOUT_TIMEOUT_S, cwd=None,
                model=AGENT_MODEL, effort=AGENT_EFFORT):
    """Run one detached `claude -p` and return (parsed_result_dict, raw_stdout, stderr, exit, dur_s)."""
    cmd = ["claude", "-p", prompt, "--model", model, "--effort", effort,
           "--output-format", "json", "--dangerously-skip-permissions"]
    cmd += (extra_args or [])
    t0 = now()
    proc = subprocess.Popen(cmd, cwd=cwd, env=child_env(), text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception: pass
        out, err = proc.communicate()
        return None, out or "", (err or "") + "\n[runner] TIMEOUT after %ss" % timeout, -9, now() - t0
    dur = now() - t0
    parsed = None
    try:
        parsed = json.loads(out)
    except Exception:
        m = re.search(r"\{.*\}", out or "", re.S)
        if m:
            try: parsed = json.loads(m.group(0))
            except Exception: pass
    return parsed, out or "", err or "", proc.returncode, dur

def throttled(*texts):
    return any(t and THROTTLE_RE.search(t) for t in texts)

def throttle_wait_s(*texts):
    """Parse a reset-time hint if present, else default. Capped."""
    for t in texts:
        if not t: continue
        m = RESET_HINT_RE.search(t)
        if m:
            try:
                hint = m.group(1).replace(" ", "")
                nowdt = datetime.datetime.now()
                fmt = "%I:%M%p" if ":" in hint else "%I%p"
                tgt = datetime.datetime.strptime(hint.upper(), fmt).replace(
                    year=nowdt.year, month=nowdt.month, day=nowdt.day)
                if tgt <= nowdt: tgt += datetime.timedelta(days=1)
                return min(max((tgt - nowdt).total_seconds() + 120, 300), THROTTLE_MAX_WAIT_S)
            except Exception:
                pass
    return THROTTLE_DEFAULT_WAIT_S

# ---- browser (OCIC adapter) --------------------------------------------------

