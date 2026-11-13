// workerd sidecar lifecycle, split out of common.js — pure refactor,
// behavior unchanged.
import os from "node:os";
import path from "node:path";
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { watchParent } from "../parent-watch.js";
import { pickFreePort } from "./cm-upstream.js";
import { log, WORKER_DIR } from "./cm-util.js";

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
