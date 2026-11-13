// Split out of extension/background.js — pure refactor, behavior unchanged.
import * as audit from "../audit/index.js";
import { recorder, recorderReady } from "./rec-state.js";
import { maybeCapture } from "./rec-util.js";

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "audit_events") {
    audit.ingest(msg).catch(() => {});
    return; // fire-and-forget; the tab does not wait on us
  }
  if (!msg) return;
  if (msg.__ocic === "behavior_event") {
    recorderReady.then(() => {
      if (!recorder.active) return;
      if (msg.vw) { recorder.lastVw = msg.vw; recorder.lastVh = msg.vh; }
      const evt = { ...msg, tab: sender.tab?.id ?? -1, frame: sender.frameId ?? 0 };
      chrome.runtime
        .sendMessage({ __ocic_offscreen: true, cmd: "event", event: evt })
        .catch(() => {});
      maybeCapture(msg.t); // frame anchored to this action (throttled ≤1/sec)
    });
    return;
  }
  if (msg.__ocic === "cursor_batch") {
    recorderReady.then(() => {
      if (!recorder.active) return;
      if (msg.vw) { recorder.lastVw = msg.vw; recorder.lastVh = msg.vh; }
      chrome.runtime
        .sendMessage({ __ocic_offscreen: true, cmd: "cursor", points: msg.points })
        .catch(() => {});
      maybeCapture(); // frame during cursor activity (throttled ≤1/sec)
    });
    return;
  }
  if (msg.__ocic === "recorder_hello") {
    recorderReady.then(() => sendResponse({ on: recorder.active }));
    return true; // async response
  }
});

// Tab + navigation events, captured in the SW so the trace has one-to-one
// parity with OCIC's own commands (navigate, tab focus/create) — not just the
// computer-tool primitives. Each carries the tab's URL so the trace records
// what tab we're in and what the current URL is.
async function recordSwEvent(action, tabId, extra = {}) {
  await recorderReady; // SW may have just woken mid-recording
  if (!recorder.active) return;
  let url = extra.url;
  if (url === undefined && tabId != null && tabId >= 0) {
    try {
      const t = await chrome.tabs.get(tabId);
      url = t && t.url;
    } catch {
      url = undefined;
    }
  }
  chrome.runtime
    .sendMessage({
      __ocic_offscreen: true,
      cmd: "event",
      event: {
        t: Date.now(),
        tab: tabId ?? -1,
        frame: 0,
        action,
        // The core `command` key: the exact OCIC tool input (plus the event's
        // tab as tabId). tab_activated has NO OCIC verb — tools select tabs
        // via their tabId param — so it carries no command, only context.
        command:
          action === "navigate"
            ? { tool: "navigate", input: { url } }
            : action === "tab_opened"
              ? { tool: "tabs_create_mcp", input: {} }
              : action === "tab_closed"
                ? { tool: "tabs_close_mcp", input: {} }
                : undefined,
        url: url || undefined // context enrichment (what URL the tab shows)
      }
    })
    .catch(() => {});
  maybeCapture(); // frame on navigation / tab change (throttled ≤1/sec)
}

// Focus/select a tab → tab_activated (with the URL now showing).
chrome.tabs.onActivated.addListener((info) => recordSwEvent("tab_activated", info.tabId));
// Open a tab → tab_opened.
chrome.tabs.onCreated.addListener((tab) =>
  recordSwEvent("tab_opened", tab.id, { url: tab.url || tab.pendingUrl })
);
// Close a tab → tab_closed.
chrome.tabs.onRemoved.addListener((tabId) => {
  recordSwEvent("tab_closed", tabId, { url: null });
  audit.onTabRemoved(tabId).catch(() => {});
});
// URL change in a tab (address bar, link, redirect, SPA history) → navigate.
// This is what captures "the current state of the URL" as it changes.
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.url) recordSwEvent("navigate", tabId, { url: changeInfo.url });
});
