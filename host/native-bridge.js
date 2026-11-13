// Pipe ownership, MCP-client attach and extension<->client routing, split
// out of native-host.js — pure refactor, behavior unchanged.
import net from "node:net";
import { ensureSocketDir, getPipePath, clearStaleSocket, secureSocket } from "./endpoint.js";
import { readNativeMessage, writeNativeMessage } from "./native-msg.js";
import { bridge } from "./native-state.js";
import {
  handleSaveAudit, handleSaveRecording, handleSaveAudio,
  handleSaveScreenshot, handleSaveScreenshotToDisk, handleWriteTempFile,
} from "./native-save.js";

export const PIPE_PATH = getPipePath();

const RETRY_MS = 1500;
const REJECTED_RETRY_MS = 15000;
// A peer that has connected but not yet said what it is. A real client sends
// `client_hello` immediately, so silence past this window is not one.
const CLASSIFY_MS = 500;

export function onIncomingConnection(socket) {
  // An accepted socket is unclassified until its first line arrives, and until
  // then nothing downstream has attached an 'error' listener. In Node an
  // unhandled 'error' is a thrown exception, so a peer that vanishes in that
  // window — a client MCP process killed mid-handshake, which is routine —
  // would take the host down, and with it every session's browser link. This is
  // the same failure that cost the primary its life in c0a09a2.
  socket.on("error", () => socket.destroy());

  let buffer = Buffer.alloc(0);
  let classified = false;

  const classifyTimer = setTimeout(() => {
    if (!classified) {
      classified = true;
      socket.destroy();
    }
  }, CLASSIFY_MS);
  socket.on("close", () => clearTimeout(classifyTimer));

  socket.on("data", function onEarlyData(chunk) {
    if (classified) return;
    buffer = Buffer.concat([buffer, chunk]);
    const idx = buffer.indexOf(10);
    if (idx === -1) return;

    const firstLine = buffer.subarray(0, idx).toString("utf-8").trim();
    const rest = buffer.subarray(idx + 1);
    let msg = null;
    try {
      msg = JSON.parse(firstLine);
    } catch {}

    classified = true;
    clearTimeout(classifyTimer);
    socket.removeListener("data", onEarlyData);

    if (msg && msg.type === "client_hello") {
      attachClient(socket, rest);
      return;
    }
    socket.destroy();
  });
}

export const pipeServer = net.createServer(onIncomingConnection);

// How long we keep probing quickly before settling into the slow lane. This has
// to comfortably exceed background.js's SWITCH_RELEASE_MS (15s): switch_browser
// hands over by having the outgoing browser drop its host and suspend reconnect
// for that window, and the incoming browser only gets the bridge if it happens
// to probe while the window is open. Backing off to 15s immediately would make
// a hand-off land inside the window mostly by luck.
const FAST_CLAIM_WINDOW_MS = 40_000;

export async function claimPipe() {
  ensureSocketDir();
  await clearStaleSocket(PIPE_PATH);
  const onErr = (err) => {
    if (err.code === "EADDRINUSE") {
      // Another browser's host holds the bridge for this user. Probe often at
      // first so a hand-off is picked up promptly, then drop to the slow lane
      // so two idle browsers are not polling each other forever.
      const fast = Date.now() - bridge.claimingSince < FAST_CLAIM_WINDOW_MS;
      setTimeout(claimPipe, fast ? RETRY_MS : REJECTED_RETRY_MS);
      return;
    }
    process.stderr.write(`Bridge listen failed: ${err.message}\n`);
    setTimeout(claimPipe, RETRY_MS);
  };
  pipeServer.once("error", onErr);
  pipeServer.listen(PIPE_PATH, () => {
    pipeServer.removeListener("error", onErr);
    process.stderr.write(`Native host owns the bridge at ${PIPE_PATH}\n`);
  });
}

export function attachClient(socket, initialBuffer) {
  const clientId = String(++bridge.clientIdCounter);
  bridge.clients.set(clientId, socket);
  process.stderr.write(`MCP client ${clientId} attached (${bridge.clients.size} total)\n`);
  socket.write(JSON.stringify({ type: "client_ack", clientId }) + "\n");

  let buffer = initialBuffer;

  function pump() {
    let idx;
    while ((idx = buffer.indexOf(10)) !== -1) {
      const line = buffer.subarray(0, idx).toString("utf-8").trim();
      buffer = buffer.subarray(idx + 1);
      if (!line) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.type === "tool_request" && msg.id) {
          // Namespace the id so concurrent sessions cannot collide, and so a
          // response can be routed back to the one client that asked.
          const prefixedId = `h${clientId}_${msg.id}`;
          bridge.clientRequestMap.set(prefixedId, { clientId, originalId: msg.id });
          writeNativeMessage({ ...msg, id: prefixedId });
        }
      } catch {
        // skip malformed
      }
    }
  }

  pump();
  socket.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    pump();
  });
  socket.on("close", () => {
    bridge.clients.delete(clientId);
    for (const [prefixedId, info] of bridge.clientRequestMap) {
      if (info.clientId === clientId) bridge.clientRequestMap.delete(prefixedId);
    }
    process.stderr.write(`MCP client ${clientId} detached (${bridge.clients.size} left)\n`);
  });
}

// Route one extension-originated message to whoever is waiting for it.
export function routeFromExtension(msg) {
  // Liveness ping from the service worker. Nothing downstream needs it, but
  // its rhythm is what the deaf-extension watchdog below keys off.
  if (msg.type === "heartbeat") {
    bridge.heartbeatsSeen++;
    return;
  }
  if (msg.type === "recording_complete") {
    // Unsolicited: any attached session may be the one holding the Claude
    // channel, so every client gets a copy.
    const line = JSON.stringify(msg) + "\n";
    for (const socket of bridge.clients.values()) {
      try {
        if (!socket.destroyed) socket.write(line);
      } catch {}
    }
    return;
  }
  if (msg.id && bridge.clientRequestMap.has(msg.id)) {
    const { clientId, originalId } = bridge.clientRequestMap.get(msg.id);
    bridge.clientRequestMap.delete(msg.id);
    const socket = bridge.clients.get(clientId);
    try {
      if (socket && !socket.destroyed) {
        socket.write(JSON.stringify({ ...msg, id: originalId }) + "\n");
      }
    } catch {}
  }
  // Anything else: the client that asked is gone, or we never issued this id.
}

