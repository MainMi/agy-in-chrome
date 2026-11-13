// Split out of extension/background.js — pure refactor, behavior unchanged.
import { TAB_CONFIG_KEY, configState } from "./config.js";
import { dbg } from "./debuglog.js";
import { attachedTabs, consoleMessages, cursorByTab, networkByRequestId, networkRequests, state } from "./state.js";

// --- CDP helpers ---
// NOTE ON TAB ACTIVATION: nothing in here selects a tab or raises a window.
// Automation drives background tabs, so it never yanks the operator away from
// what they are doing — that interruption is the whole of issue #28, and it is
// also how the official Claude in Chrome behaves. The one deliberate exception
// is the set_tab_focus tool, which exists precisely so surfacing a tab is a
// choice the agent makes rather than a side effect of every click.
//
// The tradeoff: Chromium throttles a fully hidden tab's compositor, so input
// dispatched to one can be slower than to a visible tab. A tab in a visible
// window (even an unfocused one) still renders, which is the normal case here
// since the MCP group lives in its own window.

// Attach is not idempotent and not instant: two concurrent calls to a
// not-yet-attached tab both pass the `has` check and the second
// chrome.debugger.attach throws "Another debugger is already attached".
// Reachable by any two consumers hitting a cold tab at the same time.
// Concurrent callers share one in-flight attach.
const attachingTabs = new Map();
export async function ensureAttached(tabId) {
  if (attachedTabs.has(tabId)) return;
  if (attachingTabs.has(tabId)) return attachingTabs.get(tabId);
  const attach = (async () => {
    await chrome.debugger.attach({ tabId }, "1.3");
    attachedTabs.set(tabId, { enabledDomains: new Set() });
  // No device-metrics emulation here. Screenshots get CSS-pixel framing from an
  // explicit capture clip instead (see takeScreenshot), which is more direct and
  // touches nothing about the page — no re-layout, no resize handlers fired.
  //
  // An earlier version of this comment claimed the override was what froze the
  // viewport against resize_window. That was wrong. The real cause is below:
  // Chrome does not re-layout a tab that is not the SELECTED tab in its window,
  // and since #28 we never select tabs. Removing the override did not change
  // that, and restoring it would not either.
  //
  // Builds before this one DID install an override (at the outer window size,
  // which is larger than the viewport, so pages laid out for a size that did not
  // exist). A tab attached by one of those builds still carries it, so clear it
  // once here rather than inheriting a stale viewport from whatever ran before.
  try {
    await chrome.debugger.sendCommand({ tabId }, "Emulation.clearDeviceMetricsOverride", {});
  } catch {}
  // Make the tab behave as focused/active for input purposes WITHOUT selecting
  // it. Since we stopped foregrounding tabs (#28), a driven tab is often not
  // the selected one, and Chromium throttles a hidden tab: synthesized
  // mousePressed/mouseReleased can be dropped outright — observed as clicks
  // that reach the page as zero mousedown/mouseup events. This is the same
  // primitive headless automation uses to drive unfocused pages, and it is
  // what lets "never steal the operator's focus" and "input actually lands"
  // both hold. Best-effort: older builds without it just keep the old
  // behaviour rather than failing the attach.
  try {
    await chrome.debugger.sendCommand({ tabId }, "Emulation.setFocusEmulationEnabled", {
      enabled: true,
    });
  } catch (e) {
    // Without this, input to an unselected tab can be dropped outright, so a
    // silent failure here turns into clicks that vanish with no other trace.
    dbg("cdp", "Emulation.setFocusEmulationEnabled FAILED — input to unselected tabs may be dropped",
        { tab: tabId, err: String(e && e.message).slice(0, 120) });
    console.warn("setFocusEmulationEnabled unavailable:", e.message);
  }
  })();
  attachingTabs.set(tabId, attach);
  try {
    await attach;
  } catch (e) {
    // Failed attach must not leave a half-registered tab behind.
    attachedTabs.delete(tabId);
    throw e;
  } finally {
    attachingTabs.delete(tabId);
  }
}

export async function ensureDomain(tabId, domain) {
  const state = attachedTabs.get(tabId);
  if (!state) throw new Error("Not attached to tab");
  if (state.enabledDomains.has(domain)) return;
  await chrome.debugger.sendCommand({ tabId }, `${domain}.enable`, {});
  state.enabledDomains.add(domain);
}

// A single CDP command must never hang a tool call to the 60s MCP timeout.
// On a heavy page mid-reflow, Page.captureScreenshot (and other commands) can
// block indefinitely; bound every command so a stuck one fails fast and
// surfaces as a tool error the agent can react to, instead of a silent stall.
export const CDP_TIMEOUT_MS = 20000;
export function withTimeout(promise, ms, label) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} timed out after ${ms}ms`)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

export async function cdp(tabId, method, params = {}) {
  await ensureAttached(tabId);
  const t0 = Date.now();
  try {
    const out = await withTimeout(
      chrome.debugger.sendCommand({ tabId }, method, params),
      CDP_TIMEOUT_MS,
      `CDP ${method}`
    );
    dbg("cdp", `${method}${cdpDetail(method, params)}`, { tab: tabId, ms: Date.now() - t0 });
    return out;
  } catch (e) {
    dbg("cdp", `${method}${cdpDetail(method, params)}`, {
      tab: tabId, ms: Date.now() - t0, err: String(e && e.message).slice(0, 120)
    });
    throw e;
  }
}

// A short, useful summary of a CDP call: the parameters that matter for
// diagnosis (where an input went, which key, how far a scroll) without dumping
// entire payloads such as screenshot bytes into the log.
function cdpDetail(method, p) {
  if (!p) return "";
  if (method === "Input.dispatchMouseEvent")
    return ` ${p.type}(${p.x},${p.y})${p.deltaY ? ` dy=${p.deltaY}` : ""}${p.button && p.type !== "mouseMoved" ? ` ${p.button}` : ""}`;
  if (method === "Input.dispatchKeyEvent")
    return ` ${p.type} ${JSON.stringify(p.key || "")}${p.autoRepeat ? " repeat" : ""}`;
  if (method === "Input.insertText") return ` ${JSON.stringify(String(p.text).slice(0, 20))}`;
  if (method === "Runtime.evaluate") return ` ${JSON.stringify(String(p.expression || "").slice(0, 60))}`;
  if (method === "Input.synthesizeScrollGesture") return ` (${p.x},${p.y}) y=${p.yDistance}`;
  return "";
}

// Clean up when tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
  state.tabGroupTabs.delete(tabId);
  if (attachedTabs.has(tabId)) {
    try { chrome.debugger.detach({ tabId }); } catch {}
    attachedTabs.delete(tabId);
  }
  consoleMessages.delete(tabId);
  networkRequests.delete(tabId);
  networkByRequestId.delete(tabId);
  cursorByTab.delete(tabId);
  // Drop any per-tab config override too: tab ids are recycled by the browser,
  // so a stale override would silently apply to an unrelated future tab.
  if (configState.byTab[String(tabId)]) {
    const byTab = { ...configState.byTab };
    delete byTab[String(tabId)];
    configState.byTab = byTab;
    chrome.storage.session.set({ [TAB_CONFIG_KEY]: byTab }).catch(() => {});
  }
});

// Handle user dismissing debugger bar
chrome.debugger.onDetach.addListener((source, reason) => {
  attachedTabs.delete(source.tabId);
});
