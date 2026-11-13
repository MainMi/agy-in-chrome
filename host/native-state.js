// Shared mutable state for the native-host bridge: which MCP clients are
// attached, extension traffic timing, and the id-rewrite map. An object so
// every module can read AND write it (imported `let` bindings are read-only).
export const bridge = {
  lastExtensionTraffic: Date.now(), // last stdin byte from the extension
  heartbeatsSeen: 0,
  clients: new Map(),               // clientId -> socket
  clientRequestMap: new Map(),      // prefixed id -> { clientId, originalId }
  clientIdCounter: 0,
  claimingSince: Date.now(),
};
