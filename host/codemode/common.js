// Shared lifecycle and codemode plumbing for both code-mode-only
// and hybrid MCP frontends. Sits between Claude Code and the existing
// host/mcp-server.js — spawning a workerd sidecar (via `wrangler dev`)
// to run sandboxed code, and proxying tool calls from the sandbox back
// to the upstream MCP server.

import http from "node:http";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { watchParent } from "../parent-watch.js";

import {
  init as runtimeInit,
  callTool as runtimeCallTool,
  shutdown as runtimeShutdown
} from "../tool-runtime.js";
import { toolsAsJsonSchemaList } from "../tool-definitions.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const WORKER_DIR = path.join(__dirname, "worker");

const log = (...args) => process.stderr.write(`[codemode] ${args.join(" ")}\n`);

export async function pickFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const port = srv.address().port;
      srv.close(() => resolve(port));
    });
  });
}

export async function connectUpstream() {
  // Talk to the tool runtime in-process — no child mcp-server.js, no extra
  // stdio MCP framing layer. The shim mirrors the old McpServer client API
  // (callTool / close) so the rest of common.js doesn't have to care.
  await runtimeInit();
  const tools = toolsAsJsonSchemaList();
  log(`runtime ready with ${tools.length} tools`);
  const client = {
    callTool: ({ name, arguments: args }) => runtimeCallTool(name, args),
    close: () => runtimeShutdown()
  };
  return { client, tools };
}

function extractText(result) {
  const blocks = result?.content;
  if (!Array.isArray(blocks)) return null;
  return blocks
    .filter((b) => b?.type === "text" && typeof b.text === "string")
    .map((b) => b.text)
    .join("\n") || null;
}

// Try to parse `text` as JSON, including the common case where the upstream
// tool emits a JSON object/array followed by a human-readable trailing
// section. Returns { value, trailing } or null when no JSON was found.
function parseLeadingJson(text) {
  if (typeof text !== "string" || text.length === 0) return null;
  // Skip leading whitespace.
  let i = 0;
  while (i < text.length && /\s/.test(text[i])) i++;
  const first = text[i];
  if (first !== "{" && first !== "[") return null;
  const close = first === "{" ? "}" : "]";
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let j = i; j < text.length; j++) {
    const c = text[j];
    if (escape) { escape = false; continue; }
    if (c === "\\" && inString) { escape = true; continue; }
    if (c === '"') { inString = !inString; continue; }
    if (inString) continue;
    if (c === first) depth++;
    else if (c === close) {
      depth--;
      if (depth === 0) {
        const candidate = text.slice(i, j + 1);
        try {
          const value = JSON.parse(candidate);
          const trailing = text.slice(j + 1).trim();
          return { value, trailing };
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

// Collapse an MCP CallToolResult envelope into the most useful shape for
// sandbox code. Single text block → the parsed JSON if the text is or
// starts with JSON (trailing human-readable text is preserved as `_text`
// only when the JSON value is an object), otherwise the raw string.
// Multiple blocks → an array. Image and resource blocks become opaque
// markers since their content isn't visible from inside execute_code.
export function unwrapMcpResult(result) {
  const blocks = result?.content;
  if (!Array.isArray(blocks)) return result;
  if (blocks.length === 1 && blocks[0]?.type === "text") {
    const t = blocks[0].text;
    const parsed = parseLeadingJson(t);
    if (parsed) {
      if (parsed.trailing && typeof parsed.value === "object" && parsed.value !== null && !Array.isArray(parsed.value)) {
        return { ...parsed.value, _text: parsed.trailing };
      }
      return parsed.value;
    }
    return t;
  }
  return blocks.map((b) => {
    if (b?.type === "text") {
      const parsed = parseLeadingJson(b.text);
      return { type: "text", value: parsed ? parsed.value : b.text };
    }
    if (b?.type === "image") {
      return {
        type: "image",
        mimeType: b.mimeType,
        note: "image data not visible from inside execute_code"
      };
    }
    if (b?.type === "resource") {
      return { type: "resource", uri: b.resource?.uri };
    }
    return b;
  });
}

export function startCallbackServer(upstream) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(async (req, res) => {
      const m = req.url && req.url.match(/^\/tool\/(.+)$/);
      if (!m || req.method !== "POST") {
        res.writeHead(404).end();
        return;
      }
      const name = decodeURIComponent(m[1]);
      let body = "";
      for await (const chunk of req) body += chunk;
      let args;
      try {
        args = body ? JSON.parse(body) : {};
      } catch (err) {
        res.writeHead(400, { "content-type": "application/json" });
        res.end(JSON.stringify({ error: `invalid JSON: ${err.message}` }));
        return;
      }
      try {
        const result = await upstream.callTool({ name, arguments: args });
        if (result?.isError) {
          const msg = extractText(result) ?? `tool ${name} errored`;
          res.writeHead(500, { "content-type": "application/json" });
          res.end(JSON.stringify({ error: msg }));
          return;
        }
        const unwrapped = unwrapMcpResult(result);
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify(unwrapped));
      } catch (err) {
        res.writeHead(500, { "content-type": "application/json" });
        res.end(JSON.stringify({ error: err?.message ?? String(err) }));
      }
    });
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      log(`callback server on :${port}`);
      resolve({ server, port });
    });
  });
}

export async function startWorkerd({ variant } = {}) {
  const port = await pickFreePort();
  // Each variant (codemode / hybrid) gets its own per-process wrangler state
  // directory. Two wrangler instances pointed at the same .wrangler/state/
  // race on miniflare's SQLite metadata.sqlite, which intermittently causes
  // one of them to never reach "Ready on ..." within Claude Code's MCP
  // startup window. Using --persist-to splits the state so the codemode and
  // hybrid servers can start in parallel without contending.
  const variantTag = variant || "default";
  const persistTo = path.join(
    os.tmpdir(),
    `oc-wrangler-${variantTag}-${process.pid}`
  );
  // Prefer invoking wrangler's real CLI entrypoint directly (node
  // <worker>/node_modules/wrangler/bin/wrangler.js) instead of going through
  // `npx wrangler`. npx resolves "wrangler" via node_modules/.bin, and that
  // shim is normally an npm-created symlink into node_modules/wrangler/bin —
  // but it comes back as a plain copied file (not a symlink) whenever
  // node_modules was populated by something that dereferences symlinks
  // (an archive extraction, a naive directory copy/sync, etc.), and a copied
  // wrangler.js resolves its own `../wrangler-dist/cli.js` one directory too
  // shallow and crashes with MODULE_NOT_FOUND before wrangler ever starts.
  // Spawning the real file directly with `node` sidesteps .bin entirely, so
  // execute_code keeps working regardless of how node_modules/.bin ended up
  // in whatever state it's in. Falls back to `npx wrangler` if the expected
  // path isn't there (e.g. a future wrangler major changes the layout).
  const directWranglerBin = path.join(
    WORKER_DIR,
    "node_modules",
    "wrangler",
    "bin",
    "wrangler.js"
  );
  const useDirectBin = existsSync(directWranglerBin);
  const wranglerArgs = [
    "dev",
    "--port",
    String(port),
    "--ip",
    "127.0.0.1",
    "--persist-to",
    persistTo
  ];
  // npx is a plain executable on macOS/Linux but a `.cmd` shim on Windows,
  // which Node's spawn can't launch directly (ENOENT for "npx", EINVAL for
  // "npx.cmd" since the CVE-2024-27980 fix) — so Windows goes through the
  // shell. POSIX keeps the args array + its own process group so cleanup can
  // SIGTERM the npx→wrangler→workerd tree; Windows passes a single command
  // string (an args array with shell:true both warns DEP0190 and skips
  // quoting) with the persist path quoted for spaces, and is tree-killed by pid.
  const isWindows = process.platform === "win32";
  const spawnEnv = { ...process.env, FORCE_COLOR: "0", NO_COLOR: "1" };
  const proc = isWindows
    ? spawn(
        useDirectBin
          ? `node "${directWranglerBin}" ${wranglerArgs.map((a) => `"${a}"`).join(" ")}`
          : `npx --yes wrangler dev --port ${port} --ip 127.0.0.1 --persist-to "${persistTo}"`,
        {
          cwd: WORKER_DIR,
          stdio: ["ignore", "pipe", "pipe"],
          shell: true,
          env: spawnEnv
        }
      )
    : spawn(
        useDirectBin ? process.execPath : "npx",
        useDirectBin
          ? [directWranglerBin, ...wranglerArgs]
          : ["--yes", "wrangler", ...wranglerArgs],
        {
          cwd: WORKER_DIR,
          stdio: ["ignore", "pipe", "pipe"],
          // Own process group so cleanup can SIGTERM the whole tree; npx +
          // wrangler + workerd is three layers and a plain proc.kill() only
          // signals the npx wrapper.
          detached: true,
          env: spawnEnv
        }
      );

  let resolved = false;
  const captured = [];
  await new Promise((resolve, reject) => {
    const onData = (chunk) => {
      const text = chunk.toString();
      captured.push(text);
      // Wrangler prints "Ready on http://..." when the worker is live.
      if (!resolved && /Ready on /.test(text)) {
        resolved = true;
        resolve();
      }
      process.stderr.write(`[wrangler] ${text}`);
    };
    proc.stdout.on("data", onData);
    proc.stderr.on("data", onData);
    proc.on("exit", (code) => {
      if (!resolved) {
        reject(
          new Error(
            `wrangler exited (${code}) before ready. output:\n${captured.join("")}`
          )
        );
      }
    });
    // A spawn failure (e.g. npx not found) emits 'error', not 'exit'. With no
    // listener that would surface as an unhandled 'error' event and crash the
    // whole server; turn it into a rejection so the caller degrades to
    // "no execute_code" while the passthrough tools keep working.
    proc.on("error", (err) => {
      if (!resolved) reject(err);
    });
    setTimeout(() => {
      if (!resolved) {
        reject(
          new Error(
            `wrangler did not become ready in 60s. output:\n${captured.join("")}`
          )
        );
      }
    }, 60_000);
  });

  log(`workerd ready on :${port}`);
  return { proc, port };
}

// Default sandbox execution budget. A multi-person form fill with explicit
// UI-settle waits between every action can realistically take 60-120s; 300s
// gives that kind of flow plenty of headroom while still surfacing genuine
// infinite loops in a reasonable amount of time.
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
