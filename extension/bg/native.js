// Split out of extension/background.js — pure refactor, behavior unchanged.
import { CDP_TIMEOUT_MS } from "./cdp.js";
import { dbg } from "./debuglog.js";
import { handleToolRequest } from "./dispatch.js";
import { recorder } from "./rec-state.js";
import { NATIVE_HOST_NAME, screenshotSaves, state } from "./state.js";

let heartbeatTimer = null;

// switch_browser releases this browser's hold on the shared runtime by
// dropping the native port; this window keeps us from immediately re-grabbing
// it so a target browser (extension enabled) can become primary.
export const SWITCH_RELEASE_MS = 15000;

// --- Keep-alive alarm ---
// Backstop wake-up for the MV3 service worker. The proactive heartbeat
// inside connectNativeHost (~15s) is the primary mechanism; this alarm
// covers cases where the SW is fully evicted between heartbeats.
chrome.alarms.create("keepalive", { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "keepalive") {
    if (!state.nativePort) connectNativeHost();
  }
});

// --- Native messaging ---
export function connectNativeHost() {
  if (state.nativePort) return;
  // Honor a switch_browser release window: stay disconnected so another
  // browser can take the primary connection, then resume.
  if (Date.now() < state.suspendReconnectUntil) {
    setTimeout(connectNativeHost, 500);
    return;
  }
  try {
    state.nativePort = chrome.runtime.connectNative(NATIVE_HOST_NAME);

    state.nativePort.onMessage.addListener((msg) => {
      // Heartbeat acks (and any other non-request server-originated messages)
      // are intentionally ignored here — only tool_request kicks work.
      if (msg.type === "tool_request" && msg.id) {
        handleToolRequest(msg.id, msg.tool, msg.args || {});
      } else if (msg.type === "recording_saved") {
        // Reply from the native host after writing a recording bundle to disk.
        const resolve = recorder.pendingSaves.get(String(msg.recording_id));
        if (resolve) {
          recorder.pendingSaves.delete(String(msg.recording_id));
          resolve(msg.ok ? msg.path : null);
        }
      } else if (msg.type === "screenshot_saved") {
        // Reply from the native host after writing a screenshot to disk
        // (save_to_disk on the computer tool's screenshot action).
        const pending = screenshotSaves.get(String(msg.id));
        if (pending) {
          screenshotSaves.delete(String(msg.id));
          if (msg.ok && msg.path) pending.resolve(msg.path);
          else pending.reject(new Error(msg.error || "failed to save screenshot"));
        }
      } else if (msg.id && pendingNative.has(msg.id)) {
        // Generic reply to a nativeRequest() (e.g. write_temp_file). The host
        // echoes the request id back so we can settle the matching promise.
        const p = pendingNative.get(msg.id);
        pendingNative.delete(msg.id);
        if (msg.ok) p.resolve(msg.result);
        else p.reject(new Error(String(msg.error || "Native request failed")));
      }
    });

    state.nativePort.onDisconnect.addListener(() => {
      const err = chrome.runtime.lastError;
      dbg("port", `native host disconnected`, { err: err && String(err.message).slice(0, 120) });
      state.nativePort = null;
      stopHeartbeat();
      // Retry quickly. Reconnect latency dominates per-call wall-clock when
      // the SW just slept; 250ms is the right floor — fast enough to be
      // invisible to a single tool call, slow enough not to busy-spin on a
      // genuinely dead host (which will be retried again on next alarm).
      setTimeout(connectNativeHost, 250);
    });

    startHeartbeat();
  } catch (e) {
    state.nativePort = null;
    stopHeartbeat();
    setTimeout(connectNativeHost, 250);
  }
}

// Proactive heartbeat: send a small message every ~15s while the native
// port is alive. Two effects:
//   1) The SW stays alive between alarm fires (postMessage resets the
//      ~30s idle timer Chrome uses to evict MV3 service workers).
//   2) The native-host TCP socket stays warm — no chance of Chrome
//      garbage-collecting the connection because it's been idle.
// 15s is well under both Chrome's SW idle timeout and the alarm period.
function startHeartbeat() {
  stopHeartbeat();
  heartbeatTimer = setInterval(() => {
    if (!state.nativePort) return;
    try {
      state.nativePort.postMessage({ type: "heartbeat", t: Date.now() });
    } catch {
      // Port disconnected; the onDisconnect handler will reconnect.
    }
  }, 15000);
}

export function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

export function sendResponse(id, result) {
  if (!state.nativePort) return;
  try {
    state.nativePort.postMessage({ id, type: "tool_response", result });
  } catch {
    // Port disconnected
  }
}

export function sendError(id, error) {
  if (!state.nativePort) return;
  try {
    state.nativePort.postMessage({ id, type: "tool_error", error: String(error) });
  } catch {
    // Port disconnected
  }
}

// --- Native host request/response (ask host to do something, wait for result) ---
// The recorder's save_* messages are fire-and-forget; upload_image needs a
// reply (the temp file path). pendingNative correlates a reply by id. Bound
// the wait so a lost reply can't hang a tool call past the CDP timeout.
const pendingNative = new Map(); // request id -> { resolve, reject }
let nativeReqSeq = 0;

export function nativeRequest(msg) {
  return new Promise((resolve, reject) => {
    if (!state.nativePort) { reject(new Error("Native host not connected")); return; }
    const id = `nr_${Date.now()}_${nativeReqSeq++}`;
    pendingNative.set(id, { resolve, reject });
    state.nativePort.postMessage({ ...msg, id });
    setTimeout(() => {
      const p = pendingNative.get(id);
      if (p) { pendingNative.delete(id); p.reject(new Error("Native request timed out")); }
    }, CDP_TIMEOUT_MS);
  });
}
