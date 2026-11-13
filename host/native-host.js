#!/usr/bin/env node

// Native Messaging Host for AGY in Chrome extension.
// Launched by Chrome when the extension calls connectNative().
// Bridges between Chrome native messaging (stdin/stdout, 4-byte LE length prefix
// + JSON) and the AGY sessions attached to the bridge it owns.

import net from "node:net";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

import {
  getPipePath,
  ensureSocketDir,
  clearStaleSocket,
  secureSocket
} from "./endpoint.js";

import { readNativeMessage } from "./native-msg.js";
import { bridge } from "./native-state.js";
import { pipeServer, claimPipe, routeFromExtension, PIPE_PATH } from "./native-bridge.js";
import {
  handleSaveAudit, handleSaveRecording, handleSaveAudio,
  handleSaveScreenshot, handleSaveScreenshotToDisk, handleWriteTempFile,
} from "./native-save.js";

// --- Who owns the bridge ---
//
// Exactly one process has to own the rendezvous, because native messaging gives
// the extension exactly one host, and every Claude Code session on the machine
// has to reach that one browser through it. The only real question is WHICH
// process owns it.
//
// It used to be whichever MCP server bound :18765 first — an ordinary Claude
// Code session, picked for no reason but boot order, holding the browser link
// on behalf of every other session on the box. That made the link's lifetime an
// accident: it ended when an unrelated session exited, and a stale server left
// behind by a session that died days ago was just as eligible to win the race
// as a live one (#36, #41).
//
// This process is the principled owner. Chrome starts it when the extension
// connects and kills it when the extension goes away, so its lifetime already
// IS the browser link's lifetime — and the extension already supervises it,
// reconnecting 250ms after onDisconnect (background.js). Owning the rendezvous
// here deletes the election entirely and demotes a leaked MCP server to
// harmless: it holds nothing anyone else needs.



// MCP servers connect to us and are multiplexed onto the single native
// messaging channel to the extension.

// --- Main: bridge stdin (from extension) <-> the attached MCP clients ---

let stdinBuffer = Buffer.alloc(0);

process.stdin.on("data", (chunk) => {
  bridge.lastExtensionTraffic = Date.now();
  stdinBuffer = Buffer.concat([stdinBuffer, chunk]);
  const { messages, remainder } = readNativeMessage(stdinBuffer);
  stdinBuffer = remainder;

  for (const msg of messages) {
    // Handle recording saves locally (write to disk + reply); don't forward.
    if (msg && msg.type === "save_recording") {
      handleSaveRecording(msg);
      continue;
    }
    if (msg && msg.type === "save_audit") {
      handleSaveAudit(msg);
      continue;
    }
    if (msg && msg.type === "save_screenshot") {
      handleSaveScreenshot(msg);
      continue;
    }
    if (msg && msg.type === "save_screenshot_to_disk") {
      handleSaveScreenshotToDisk(msg);
      continue;
    }
    if (msg && msg.type === "save_audio") {
      handleSaveAudio(msg);
      continue;
    }
    if (msg && msg.type === "write_temp_file") {
      handleWriteTempFile(msg);
      continue;
    }
    // Everything else is a reply for a waiting MCP client; route it by id.
    routeFromExtension(msg);
  }
});

process.stdin.on("end", () => {
  recordExit(`extension disconnected (bridge.clients: ${bridge.clients.size})`);
  // Extension disconnected. Drop the bridge immediately rather than lingering:
  // with no extension there is no browser link to own, and holding the pipe
  // would stop the host Chrome spawns next from claiming it.
  for (const socket of bridge.clients.values()) {
    try {
      socket.destroy();
    } catch {}
  }
  try {
    pipeServer.close();
  } catch {}
  process.exit(0);
});

// --- Deaf-extension watchdog ---
//
// The worst failure this bridge has is not dying, it is going deaf: still
// holding the rendezvous, still accepting connections, never answering. Nothing
// recovers from that on its own, because every mechanism we have keys off the
// owner being GONE. Dying is the recoverable state — Chrome notices, respawns
// us, and bridge.clients reconnect — so if we cannot reach the extension any more, the
// useful thing to do is stop existing.
//
// The signal is already there: background.js posts a heartbeat every ~15s. Long
// silence means the service worker is wedged or gone.
//
// Armed only after we have actually seen heartbeats. An extension too old to
// send them would otherwise look permanently deaf, and we would exit-loop —
// which is why this is safe to ship ahead of any extension change.
const SILENCE_LIMIT_MS = Number(process.env.OCIC_SILENCE_LIMIT_MS) || 60_000;

// Chrome owns this process's stderr and throws it away, so when the host exits
// there is no way to find out why — which made a host that was cycling every 12
// minutes impossible to explain from the outside. Leave a breadcrumb on disk
// instead. One line, truncated, never grows without bound.
function recordExit(reason) {
  try {
    const file = path.join(os.homedir(), ".config", "agy-in-chrome", "host-exits.log");
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const line = `${new Date().toISOString()} pid=${process.pid} ${reason}\n`;
    let prev = "";
    try {
      prev = fs.readFileSync(file, "utf-8");
    } catch {}
    // Keep the last ~200 lines; a cycling host would otherwise write forever.
    const kept = (prev + line).split("\n").slice(-200).join("\n");
    fs.writeFileSync(file, kept);
  } catch {}
}

setInterval(() => {
  if (bridge.heartbeatsSeen < 2) return; // never saw a heartbeat: not our signal to use
  const silentFor = Date.now() - bridge.lastExtensionTraffic;
  if (silentFor < SILENCE_LIMIT_MS) return;
  const reason =
    `watchdog: no word from the extension for ${Math.round(silentFor / 1000)}s ` +
    `(heartbeats seen: ${bridge.heartbeatsSeen}, bridge.clients: ${bridge.clients.size})`;
  process.stderr.write(`${reason} — exiting so a fresh host can take the bridge.\n`);
  recordExit(reason);
  process.exit(0);
}, 15_000).unref();

claimPipe();

