// Background service worker for AGY in Chrome extension.
// Handles: native messaging, CDP via chrome.debugger, tool dispatch, tab group
// management — now split into focused modules under ./bg/. This entry keeps
// the load-order glue: the rejection guard, side-effect imports that register
// listeners, and the init calls.

// Prevent unhandled rejections from killing the service worker
self.addEventListener("unhandledrejection", (event) => {
  event.preventDefault();
});

import "./bg/cdp-events.js";    // chrome.debugger.onEvent console/network taps
import "./bg/rec-events.js";   // runtime.onMessage + tabs.* recorder listeners
import "./bg/rec-recording.js"; // action.onClicked start/stop recording toggle
import { connectNativeHost } from "./bg/native.js";
import { recoverTabGroupState } from "./bg/tabgroup.js";

recoverTabGroupState();
connectNativeHost();
