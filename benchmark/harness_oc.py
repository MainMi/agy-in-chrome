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
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # benchmark/ -> repo root
HOST = os.path.join(_REPO, "host")
REAL_SRC = os.environ.get("REAL_SRC") or os.path.join(_REPO, "REAL", "src")
NODE = os.environ.get("OCIC_NODE") or "node"


class OC:
    """Minimal MCP stdio client to mcp-server.js (the 18 raw OCIC tools)."""

    def __init__(self):
        self.p = subprocess.Popen(
            [NODE, "mcp-server.js"], cwd=HOST,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1)
        self._id = 0
        self._rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                 "clientInfo": {"name": "bench-harness", "version": "0.1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, o): self.p.stdin.write(json.dumps(o) + "\n"); self.p.stdin.flush()

    def _rpc(self, method, params):
        self._id += 1; mid = self._id
        self._send({"jsonrpc": "2.0", "id": mid, "method": method, "params": params})
        while True:
            ln = self.p.stdout.readline()
            if not ln: raise RuntimeError("mcp-server closed the pipe")
            try: msg = json.loads(ln)
            except json.JSONDecodeError: continue
            if msg.get("id") == mid:
                if "error" in msg: raise RuntimeError("MCP error: %s" % msg["error"])
                return msg.get("result") or {}

    def call(self, name, args):
        r = self._rpc("tools/call", {"name": name, "arguments": args})
        return "".join(p.get("text", "") for p in (r.get("content") or []))

    def js(self, tab, text):
        return _unwrap(self.call("javascript_tool",
                                 {"action": "javascript_exec", "tabId": tab, "text": text}))

    def navigate(self, tab, url): return self.call("navigate", {"url": url, "tabId": tab})
    def tabs(self): return self.call("tabs_context_mcp", {})

    def close(self):
        try: self.p.terminate(); self.p.wait(timeout=5)
        except Exception:
            try: self.p.kill()
            except Exception: pass


