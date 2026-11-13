// Split out of extension/background.js — pure refactor, behavior unchanged.

// --- Content script communication ---
export async function sendContentMessage(tabId, message) {
  try {
    const response = await chrome.tabs.sendMessage(tabId, message);
    return response;
  } catch {
    // Content script might not be injected yet, try injecting
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"],
    });
    // Retry
    return chrome.tabs.sendMessage(tabId, message);
  }
}

// --- Resolve ref to coordinates ---
// Resolve a ref to the point to dispatch at, scrolling the element into view
// first so the point is actually reachable. Returns the full record (not just
// the pair) so callers can report interception.
export async function resolveRefToCoordinates(tabId, ref, opts = {}) {
  const resp = await sendContentMessage(tabId, {
    type: "getRefCoordinates",
    ref,
    scrollIntoView: opts.scrollIntoView !== false
  });
  return resp?.result || null;
}
