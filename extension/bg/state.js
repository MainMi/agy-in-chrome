// Split out of extension/background.js — pure refactor, behavior unchanged.

// Shared mutable state for the service worker modules. Scalar values that
// are written from more than one module live on `state` (a mutable object);
// collections shared across modules are exported directly.
export const NATIVE_HOST_NAME = "com.antigravity.agy_in_chrome";

export const state = {
  nativePort: null,
  tabGroupId: null,
  tabGroupTabs: new Set(),
  timingsDirty: 0,
  suspendReconnectUntil: 0,
  debugDropped: 0,
  resultClearTimer: null,
};

export const attachedTabs = new Map(); // tabId -> { enabledDomains: Set }
export const consoleMessages = new Map(); // tabId -> [{level, text, timestamp, url}]
export const networkRequests = new Map(); // tabId -> [{url, method, status, type, timestamp}]
// requestId -> partial record while the request is in flight
export const networkByRequestId = new Map();
export const screenshotStore = new Map(); // imageId -> base64
export const screenshotSaves = new Map(); // reqId -> { resolve, reject } for save_to_disk
export const cursorByTab = new Map(); // tabId -> { x, y }
