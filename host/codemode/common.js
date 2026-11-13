// Shared lifecycle and codemode plumbing for both code-mode-only
// and hybrid MCP frontends. Sits between Claude Code and the existing
// host/mcp-server.js — spawning a workerd sidecar (via `wrangler dev`)
// to run sandboxed code, and proxying tool calls from the sandbox back
// to the upstream MCP server.

import http from "node:http";// Split into focused modules (cm-*.js); this file stays as the import
// surface both frontends use.

export { pickFreePort, connectUpstream, unwrapMcpResult, startCallbackServer } from "./cm-upstream.js";
export { startWorkerd } from "./cm-workerd.js";
export {
  DEFAULT_EXECUTE_TIMEOUT_MS,
  makeRunCode,
  prewarmSandbox,
  generateApiBlock,
  SERVER_INSTRUCTIONS,
  buildExecuteCodeDescription,
  packExecuteResult,
  installCleanup,
} from "./cm-runcode.js";
