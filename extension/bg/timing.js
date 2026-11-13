// Split out of extension/background.js — pure refactor, behavior unchanged.
import { state } from "./state.js";

// --- Per-call timing forensics -------------------------------------------
// Ring buffer of tool-call timings, persisted to chrome.storage.session so a
// worker restart doesn't lose the window we were trying to catch. Exists to
// pin down a field-observed failure mode: calls against certain tabs paying a
// flat ~1s quantum each (payload-independent), in windows lasting minutes.
// Read (and optionally clear) via the debug_timings tool.
export const bootAt = Date.now();
export const callTimings = [];
export function recordTiming(entry) {
  callTimings.push(entry);
  if (callTimings.length > 600) callTimings.splice(0, callTimings.length - 600);
  if (++state.timingsDirty >= 20) {
    state.timingsDirty = 0;
    try {
      chrome.storage.session.set({ mcp_call_timings: callTimings.slice(), mcp_boot_at: bootAt });
    } catch {}
  }
}
