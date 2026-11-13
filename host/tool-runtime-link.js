// Bridge-link plumbing: socket lifecycle, reconnect, request correlation,
// split out of tool-runtime.js — pure refactor, behavior unchanged. `rt`
// holds the mutable connection state so both this module and the public API
// can read AND write it.
import net from "node:net";
import { getPipePath } from "./endpoint.js";
import { noteActivity } from "./parent-watch.js";

export const rt = {
  started: false,
  socket: null,
  readBuffer: Buffer.alloc(0),
  reconnectTimer: null,
  shuttingDown: false,
  requestIdCounter: 0,
};

const PIPE_PATH = getPipePath();

const REQUEST_TIMEOUT_MS = 60_000;
// The host dies and respawns whenever Chrome recycles the service worker, and
// background.js reconnects 250ms later. A call landing in that window should
// wait for the bridge to come back rather than fail.
const LINK_GRACE_MS = 5_000;
const RECONNECT_MS = 500;


export const pendingRequests = new Map(); // id -> { resolve, reject, timer, sent }

// Returned when the bridge drops with a request still in flight. Deliberately
// does NOT claim the action failed: the request may have reached the browser
// and run, with only the response lost. The wording has to leave the agent able
// to act — verify, then decide — rather than blindly retry.
export const HOST_DROPPED_ERROR =
  "Browser connection dropped after the request was sent, so its result is unknown. " +
  "The action may have ALREADY taken effect in the browser. Do not blindly retry: " +
  "check the current page state first (e.g. take a screenshot or read the page), " +
  "then repeat the action only if it did not happen.";

export const NO_BRIDGE_ERROR =
  "Browser extension is not connected. Make sure a supported Chromium browser " +
  "is running with the AGY in Chrome extension installed and enabled.";

// Unsolicited upstream events from the extension (not tool responses): the
// imitation-learning recorder posts { type: "recording_complete", ... } when
// a recording finishes. Subscribers (the channel-enabled MCP server) get
// notified so they can inject a channel event into the AGY session.
const recordingEventSubscribers = new Set();
export function onRecordingEvent(cb) {
  recordingEventSubscribers.add(cb);
  return () => recordingEventSubscribers.delete(cb);
}
export function emitRecordingEvent(msg) {
  for (const cb of recordingEventSubscribers) {
    try {
      cb(msg);
    } catch {}
  }
}

export const linkIsUp = () => rt.socket && !rt.socket.destroyed && rt.socket.readyState === "open";

// Wait for the bridge to come back, for callers that arrived while the host was
// being respawned.
export function waitForLink(maxMs) {
  if (linkIsUp()) return Promise.resolve(true);
  return new Promise((resolve) => {
    const startedAt = Date.now();
    const poll = setInterval(() => {
      if (linkIsUp()) {
        clearInterval(poll);
        resolve(true);
      } else if (Date.now() - startedAt >= maxMs) {
        clearInterval(poll);
        resolve(false);
      }
    }, 100);
  });
}

export function handleMessage(msg) {
  if (msg.type === "client_ack") return;
  if (msg.type === "recording_complete") {
    emitRecordingEvent(msg);
    return;
  }
  if (msg.id && pendingRequests.has(msg.id)) {
    const { resolve, reject, timer } = pendingRequests.get(msg.id);
    clearTimeout(timer);
    pendingRequests.delete(msg.id);
    if (msg.type === "tool_error") {
      reject(new Error(msg.error || "Tool execution failed"));
    } else {
      resolve(msg.result);
    }
  }
}

export function connect() {
  if (rt.shuttingDown) return;
  rt.reconnectTimer = null;

  const sock = net.createConnection(PIPE_PATH);
  rt.socket = sock;
  rt.readBuffer = Buffer.alloc(0);
  let established = false;

  sock.on("connect", () => {
    established = true;
    sock.write(JSON.stringify({ type: "client_hello" }) + "\n");
    process.stderr.write(`Joined the browser bridge at ${PIPE_PATH}\n`);
  });

  sock.on("data", (chunk) => {
    rt.readBuffer = Buffer.concat([rt.readBuffer, chunk]);
    let idx;
    while ((idx = rt.readBuffer.indexOf(10)) !== -1) {
      const line = rt.readBuffer.subarray(0, idx).toString("utf-8").trim();
      rt.readBuffer = rt.readBuffer.subarray(idx + 1);
      if (!line) continue;
      try {
        handleMessage(JSON.parse(line));
      } catch {
        // skip malformed
      }
    }
  });

  // Nothing to report for a connect that simply found no host: that is the
  // ordinary state when the browser is not running, and the close handler
  // schedules the retry.
  sock.on("error", (err) => {
    if (established) process.stderr.write(`Bridge error: ${err.message}\n`);
  });

  sock.on("close", () => {
    if (rt.socket === sock) rt.socket = null;
    failPending();
    if (!rt.shuttingDown && !rt.reconnectTimer) {
      rt.reconnectTimer = setTimeout(connect, RECONNECT_MS);
    }
  });
}

// Settle everything in flight when the link drops.
//
// A request that was actually written may have reached the browser and run,
// with only its response lost — replaying it would silently double-execute the
// action (a click clicks twice) while the agent sees one successful call. There
// is no way to tell "never ran" from "ran, response lost" at this layer, so
// those fail loudly and let the agent decide with page context. A request still
// waiting for the link never went anywhere, so it can say so plainly.
export function failPending() {
  if (pendingRequests.size === 0) return;
  for (const [, entry] of pendingRequests) {
    clearTimeout(entry.timer);
    entry.reject(new Error(entry.sent ? HOST_DROPPED_ERROR : NO_BRIDGE_ERROR));
  }
  pendingRequests.clear();
}

export function sendToExtension(tool, args) {
  return new Promise((resolve, reject) => {
    const id = String(++rt.requestIdCounter);
    const timer = setTimeout(() => {
      pendingRequests.delete(id);
      reject(new Error("Tool request timed out after 60s"));
    }, REQUEST_TIMEOUT_MS);
    const entry = { resolve, reject, timer, sent: false };
    pendingRequests.set(id, entry);

    const line = JSON.stringify({ id, type: "tool_request", tool, args }) + "\n";

    if (linkIsUp()) {
      entry.sent = true;
      rt.socket.write(line);
      return;
    }

    waitForLink(LINK_GRACE_MS).then((ok) => {
      // Only dispatch if still pending: the entry is gone once the promise has
      // settled some other way, and sending then would run an action nobody is
      // waiting on.
      if (!pendingRequests.has(id)) return;
      if (ok && linkIsUp()) {
        entry.sent = true;
        rt.socket.write(line);
        return;
      }
      clearTimeout(timer);
      pendingRequests.delete(id);
      reject(new Error(NO_BRIDGE_ERROR));
    });
  });
}

// --- Public API ---

/**
 * Join the browser bridge. Returns as soon as the first connection attempt has
 * been made — deliberately not once it succeeds, because the MCP server has to
 * come up and advertise its tools whether or not a browser is running. Calls
 * made before the bridge is up get the grace period in sendToExtension.
 */
export async function init() {
  if (rt.started) return;
  rt.started = true;
  connect();
}

/**
 * Coerce stringified params that some MCP clients send as strings into
 * the types the extension expects (numbers, arrays). Mutates and
 * returns args.
 */
