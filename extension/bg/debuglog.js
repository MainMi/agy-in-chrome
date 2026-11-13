// Split out of extension/background.js — pure refactor, behavior unchanged.
import { state } from "./state.js";

// --- Debug recorder ----------------------------------------------------------
//
// One flat, timestamped event stream covering everything this extension does:
// tool calls, CDP commands and their durations, dispatched input with its
// coordinates, what each click actually landed on, and native-host connection
// changes. Read it with the `debug` tool.
//
// It exists so a failure can be SEEN rather than reconstructed. Several bugs
// here (clicks landing on nothing, screenshots in the wrong coordinate space,
// a resize the window manager refused) were invisible because success and
// failure produced identical output, and each took hours of forensics.
//
// Two rules, because a feedback channel that lies is worse than none:
//
//   1. Recording must never affect what it records. Every entry point is
//      wrapped so a fault in here can never fail, slow, or alter a real
//      action. Recording is a plain array push.
//   2. Absence of a record must never look like absence of an event. The
//      buffer is bounded and lives in a service worker that MV3 evicts, so
//      both limits are reported explicitly on every read: how many events were
//      dropped, and how far back the buffer actually reaches. A reader is told
//      what is NOT in here, not left to assume the silence is meaningful.
export const DEBUG_MAX = 1000;
export const debugLog = [];
export const debugBootedAt = Date.now();

// What the caller actually ASKED for. A tool response never echoes its own
// arguments, so without this the stream cannot answer the first question you
// ask of any log entry: what was this call, exactly?
export function argSummary(args) {
  if (!args || typeof args !== "object") return "(no args)";
  const parts = [];
  for (const [k, v] of Object.entries(args)) {
    if (k === "tabId") continue; // already carried on the entry itself
    let out;
    if (typeof v === "string") {
      out = v.length > 60 ? JSON.stringify(v.slice(0, 60)) + `…+${v.length - 60}ch` : JSON.stringify(v);
    } else if (Array.isArray(v)) {
      out = `[${v.slice(0, 4).join(",")}${v.length > 4 ? ",…" : ""}]`;
    } else if (v && typeof v === "object") {
      out = "{…}";
    } else {
      out = String(v);
    }
    parts.push(`${k}=${out}`);
  }
  return parts.length ? parts.join(" ") : "(no args)";
}

// What the response LEAVES OUT about itself: how much came back, and the size
// of any image. Deliberately NOT the response text — the caller already has
// that, and echoing it here would make the stream a duplicate rather than a
// record of what was omitted.
export function resultShape(result) {
  const items = (result && result.content) || [];
  let chars = 0, images = 0, b64 = 0;
  for (const it of items) {
    if (!it) continue;
    if (it.type === "text" && typeof it.text === "string") chars += it.text.length;
    else if (it.type === "image" && typeof it.data === "string") { images++; b64 += it.data.length; }
  }
  const bits = [];
  if (chars) bits.push(`${chars}ch`);
  if (images) bits.push(`${images} image ${Math.round((b64 * 3) / 4 / 1024)}KB`);
  return bits.length ? bits.join(" + ") : "empty";
}

export function dbg(kind, detail, extra) {
  try {
    const e = { t: Date.now(), kind, detail: String(detail).slice(0, 300) };
    if (extra && typeof extra === "object") {
      for (const k of ["tab", "ms", "x", "y", "err"]) {
        if (extra[k] !== undefined && extra[k] !== null) e[k] = extra[k];
      }
    }
    debugLog.push(e);
    if (debugLog.length > DEBUG_MAX) {
      state.debugDropped += debugLog.length - DEBUG_MAX;
      debugLog.splice(0, debugLog.length - DEBUG_MAX);
    }
  } catch {
    // A recorder that throws would take down the action it is observing.
  }
}
