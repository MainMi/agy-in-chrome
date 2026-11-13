// Split out of extension/background.js — pure refactor, behavior unchanged.
import { consoleMessages, networkByRequestId, networkRequests } from "./state.js";

// --- CDP event listeners for console and network ---
chrome.debugger.onEvent.addListener((source, method, params) => {
  const tabId = source.tabId;

  if (method === "Console.messageAdded" && params.message) {
    const msgs = consoleMessages.get(tabId) || [];
    msgs.push({
      level: params.message.level,
      text: params.message.text,
      url: params.message.url || "",
      timestamp: Date.now(),
    });
    // Keep last 1000
    if (msgs.length > 1000) msgs.splice(0, msgs.length - 1000);
    consoleMessages.set(tabId, msgs);
  }

  if (method === "Runtime.consoleAPICalled" && params.args) {
    const msgs = consoleMessages.get(tabId) || [];
    const text = params.args.map((a) => a.value ?? a.description ?? "").join(" ");
    msgs.push({
      level: params.type || "log",
      text,
      url: params.stackTrace?.callFrames?.[0]?.url || "",
      timestamp: Date.now(),
    });
    if (msgs.length > 1000) msgs.splice(0, msgs.length - 1000);
    consoleMessages.set(tabId, msgs);
  }

  // Merge CDP network events into one record per requestId so the reader
  // sees each request once. requestWillBeSent carries the real method + url;
  // responseReceived augments that same record with the status. A requestId
  // is reused across redirect hops, so a later event updates the existing
  // record in place rather than appending a duplicate.
  if (method === "Network.responseReceived" && params.response) {
    recordNetworkEvent(tabId, params.requestId, (existing) => ({
      status: params.response.status,
      statusText: params.response.statusText,
      mimeType: params.response.mimeType,
      type: params.type || (existing && existing.type) || "Other",
      // method + url come from requestWillBeSent; fall back to the old
      // heuristic only when no earlier event was seen for this id.
      method: (existing && existing.method) || (params.response.requestHeaders ? "?" : "GET"),
      url: (existing && existing.url) || params.response.url,
      timestamp: (existing && existing.timestamp) || Date.now(),
    }));
  }

  if (method === "Network.requestWillBeSent" && params.request) {
    recordNetworkEvent(tabId, params.requestId, (existing) => ({
      url: params.request.url,
      method: params.request.method,
      type: params.type || (existing && existing.type) || "Other",
      status: (existing && existing.status) || 0,
      timestamp: (existing && existing.timestamp) || Date.now(),
    }));
  }
});

// Append (or update) one entry for a network event, keyed by requestId.
// makeRecord(existing) returns the fields to merge; when a record already
// exists for the id (a duplicate event or a redirect hop) it is patched
// in place so the request appears exactly once in the reader's list.
function recordNetworkEvent(tabId, requestId, makeRecord) {
  const reqs = networkRequests.get(tabId) || [];
  let byId = networkByRequestId.get(tabId);
  if (!byId) {
    byId = new Map();
    networkByRequestId.set(tabId, byId);
  }

  const existing = byId.get(requestId);
  if (existing) {
    Object.assign(existing, makeRecord(existing));
    return;
  }

  const record = makeRecord(null);
  reqs.push(record);
  byId.set(requestId, record);

  if (reqs.length > 1000) {
    const evicted = reqs.splice(0, reqs.length - 1000);
    // Drop the requestId lookups for evicted records so a reused id does
    // not resurrect a stale entry.
    const evictedSet = new Set(evicted);
    for (const [id, rec] of byId) {
      if (evictedSet.has(rec)) byId.delete(id);
    }
  }
  networkRequests.set(tabId, reqs);
}
