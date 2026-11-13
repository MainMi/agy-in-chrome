// Sandboxed runCode plumbing + execute_code description builders, split
// out of common.js — pure refactor, behavior unchanged.
import { spawn } from "node:child_process";
import { watchParent } from "../parent-watch.js";
import { log } from "./cm-util.js";

export const DEFAULT_EXECUTE_TIMEOUT_MS = 300_000;

export function makeRunCode({ workerPort, callbackUrl, tools, namespace }) {
  const toolNames = tools.map((t) => t.name);
  return async function runCode(code, { timeoutMs } = {}) {
    const res = await fetch(`http://127.0.0.1:${workerPort}/execute`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        code,
        toolNames,
        callbackUrl,
        namespace,
        timeoutMs: timeoutMs ?? DEFAULT_EXECUTE_TIMEOUT_MS
      })
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`worker error ${res.status}: ${text}`);
    }
    return res.json();
  };
}

// Send a no-op through the worker so its first real call doesn't pay
// the V8 isolate cold-start. Best-effort: any error is swallowed.
export async function prewarmSandbox(runCode) {
  try {
    const t0 = Date.now();
    await runCode("async () => 0", { timeoutMs: 30_000 });
    log(`sandbox prewarmed in ${Date.now() - t0}ms`);
  } catch (err) {
    log(`sandbox prewarm failed (non-fatal): ${err.message}`);
  }
}

export async function generateApiBlock({ workerPort, tools, namespace }) {
  const payload = {
    tools: tools.map((t) => ({
      name: t.name,
      description: t.description,
      inputSchema: t.inputSchema
    })),
    namespace
  };
  const res = await fetch(`http://127.0.0.1:${workerPort}/generate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    throw new Error(`/generate failed: ${res.status} ${await res.text()}`);
  }
  const { apiBlock } = await res.json();
  return apiBlock;
}

// L1 — the MCP `instructions` field. System-prompt-adjacent, present every
// turn regardless of which tool is being chosen. It does two jobs: frame what
// this server IS (the operator's OWN live browser, driven on any site), then
// describe the one feature that is NOT intuitive, execute_code, for what it
// actually is: a full JavaScript sandbox where the browser tools are functions.
// Describing it honestly (any algorithm, no ceiling) liberates the model more
// than prescribing a narrow use would; recognize-then-batch is given as its
// highest-value application, not its definition. Kept general: true of every
// site and task, no workflow baked in. The full execute_code mechanics live in
// its own description (L4); this is the trigger that has to fire at
// action-selection time, which a buried tool description never does.
export const SERVER_INSTRUCTIONS = `agy-in-chrome drives the operator's real browser: their actual sessions, logins, and cookies, not a sandbox, so your actions have real effects.

The tool that is not obvious is \`execute_code\`: a real JavaScript sandbox where every other tool is exposed as a function (\`chrome.navigate(...)\`, \`chrome.computer(...)\`, \`chrome.find(...)\`, and the rest), so you can run loops, logic, and a whole sequence of actions in one call. Its highest-value use, and the one you most easily miss, is collapsing repetition. The moment you are about to repeat a sequence you have already hand-stepped earlier in this same session, stop: your next call should be that one \`execute_code\`, not another click. Hand-step a flow the first time through; only batch a repeat. You just did this by hand and the page has not changed, so the most reliable batch replays the exact positions you already used (find each element with \`chrome.find(...)\` instead only when the targets may have shifted). Reaching for a screenshot to begin a flow you have run before is the tell that you are about to hand-step it again, so write the execute_code instead. Batch only a deterministic run, where every step is known before you act; where the next move depends on what the page does, look first, then decide. After a batch, verify you landed where you expected, and if not, step manually to find the divergence and retry. The trigger is repetition, not the first pass.

The other tools (open / switch / close tabs, navigate, click, type, scroll, screenshot, read the page) are self-explanatory: use them the obvious way, normally one action per turn, looking at the page whenever the next move depends on what is on screen.`;

export function buildExecuteCodeDescription({ apiBlock, namespace, extraNotes }) {
  const notes = extraNotes ?? "";
  return `Run browser automation as one async arrow function. Every tool is a function on \`${namespace}\` (\`${namespace}.navigate(...)\`, \`${namespace}.computer(...)\`, \`${namespace}.find(...)\`, \`${namespace}.get_page_text(...)\`, and the rest), so a whole sequence (loops and logic included) runs in one call instead of a round-trip per step. Bare names like \`computer(...)\` are NOT defined and throw \`ReferenceError\`; always prefix with \`${namespace}.\`. The win is largest on a flow you have already hand-stepped once this session: replay it as a single call rather than clicking through it again.

## How to write it
- One async arrow body that returns the value you need to see at the end. No TypeScript, no named functions; write it inline.
- Every \`${namespace}.<tool>()\` call resolves to that tool's raw return value — never wrapped. \`javascript_exec\` resolves straight to the evaluated expression (no \`.result\`); \`find\` resolves straight to its own array (no assumed field like \`.elements\`). The types below show \`Output = unknown\` because shapes vary by tool; if unsure, probe with a trivial call (e.g. \`await ${namespace}.javascript_tool({..., text: "1+1"})\`) before relying on a field name.
- Wait with \`${namespace}.computer({ action: "wait", duration: <seconds>, tabId })\`, never \`setTimeout\` (the sandbox rejects it). Prefer waiting on a condition (poll that an element is ready, read a value back to confirm) over a fixed delay; a fixed wait fires too early on a slow render and the action is lost.
- Locate a target by purpose with \`${namespace}.find(...)\` when it may have moved; the returned \`ref\` works anywhere a \`coordinate\` does. When the page has not changed since you stepped it, replay the exact actions you just used.
- End a batch at the first step that depends on what the page did, returning the value (from \`${namespace}.get_page_text(...)\`, \`${namespace}.find(...)\`, or a small query) you need to decide the next step.
- Screenshots are not visible from inside the sandbox; use the top-level screenshot tool for those. Errors thrown inside come back in the result; read them and retry with corrected code.
- If a batch comes back wrong, harden it (wait on the real condition, retry the flaked step, find-by-reference instead of a stale coordinate) rather than dropping back to hand-stepping.

## Full TypeScript API

${apiBlock}
${notes}`;
}

export function packExecuteResult(result) {
  // result is { result, error?, logs?, latencyMs?, calls? }
  const lines = [];
  if (typeof result.latencyMs === "number") {
    lines.push(`Execution: ${result.latencyMs}ms`);
  }
  if (Array.isArray(result.calls) && result.calls.length) {
    const parts = result.calls.map((c) => `${c.tool} (${c.latencyMs}ms)`);
    lines.push(`Tool calls (${result.calls.length}): ${parts.join(", ")}`);
  }
  if (result.error) {
    lines.push(`Error: ${result.error}`);
  }
  if (result.logs && result.logs.length) {
    lines.push(`Logs:`);
    for (const l of result.logs) lines.push(`  ${l}`);
  }
  lines.push(`Result:`);
  lines.push(
    typeof result.result === "string"
      ? result.result
      : JSON.stringify(result.result, null, 2)
  );
  return {
    content: [{ type: "text", text: lines.join("\n") }],
    isError: !!result.error
  };
}

export function installCleanup({ wranglerProc, callbackServer, upstreamClient }) {
  let cleaned = false;
  // wranglerProc may be a live process, a getter function (returning the
  // process if/when wrangler eventually came up), or null. Lazy-startup
  // servers pass a getter so cleanup picks up whatever exists at exit.
  const getProc =
    typeof wranglerProc === "function" ? wranglerProc : () => wranglerProc;
  const cleanup = () => {
    if (cleaned) return;
    cleaned = true;
    try {
      // Take down wrangler + workerd + any intermediates, not just the
      // wrapper. On POSIX wrangler leads its own process group (spawned
      // detached), so signal the group (-pid). Windows has no process groups;
      // taskkill /T walks the child tree down from the shell's pid.
      const proc = getProc();
      if (proc?.pid) {
        if (process.platform === "win32") {
          spawn("taskkill", ["/pid", String(proc.pid), "/T", "/F"], {
            stdio: "ignore"
          });
        } else {
          process.kill(-proc.pid, "SIGTERM");
        }
      }
    } catch {}
    try { callbackServer?.close(); } catch {}
    try { upstreamClient?.close(); } catch {}
  };
  process.on("SIGTERM", () => { cleanup(); process.exit(0); });
  process.on("SIGINT", () => { cleanup(); process.exit(0); });
  process.on("exit", cleanup);
  // The MCP stdio transport reads from stdin; when the client closes the
  // pipe (e.g. Claude Code restarts), nothing else exits the event loop
  // because wrangler + the callback HTTP server + the upstream client all
  // keep it alive. Tear down on EOF.
  process.stdin.on("end", () => { cleanup(); process.exit(0); });
  // ...and when EOF never comes because someone else holds a copy of the write
  // end, watch the parent directly. This server keeps a wrangler tree alive, so
  // an undetected orphan here costs several processes, not one.
  watchParent(() => { cleanup(); process.exit(0); });
  return cleanup;
}
