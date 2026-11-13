// Shared runtime for agy-in-chrome tools.
//
// Joins the browser bridge as a client and exposes a single
// `callTool(name, args)` entry point. The bridge is owned by the native host,
// which Chrome starts and stops with the extension, so this process never has
// to own anything, elect anything, or care who else is attached.
//
// It used to be far more than this: every consumer raced to bind a TCP port,
// and the winner multiplexed all the others through itself. That made an
// ordinary AGY session load-bearing for the whole machine. All of it —
// the election, the yield protocol, the peer-classification sniff, the
// self-promotion path, the pidfile — existed to manage a role nobody should
// have had, and went away with it.
//
// This used to live inline in mcp-server.js; it's extracted so that other
// in-process consumers (the codemode + hybrid servers) can call tools
// without going through a child mcp-server.js + stdio MCP roundtrip.

import net from "node:net";

import { getPipePath } from "./endpoint.js";
import { noteActivity } from "./parent-watch.js";
import { sendToExtension, rt, pendingRequests } from "./tool-runtime-link.js";

export { init, onRecordingEvent } from "./tool-runtime-link.js";

export function coerceArgs(args) {
  if (!args || typeof args !== "object") return args;
  if (typeof args.tabId === "string") args.tabId = Number(args.tabId);
  if (typeof args.coordinate === "string") {
    try {
      args.coordinate = JSON.parse(args.coordinate);
    } catch {}
  }
  if (typeof args.start_coordinate === "string") {
    try {
      args.start_coordinate = JSON.parse(args.start_coordinate);
    } catch {}
  }
  if (typeof args.region === "string") {
    try {
      args.region = JSON.parse(args.region);
    } catch {}
  }
  return args;
}

function textResult(text) {
  return { content: [{ type: "text", text }] };
}

/**
 * Call a tool on the extension. Returns an MCP CallToolResult envelope
 * (with text/image/etc. content blocks).
 *
 * Args are coerced (string→number/array) before the call so this is
 * safe to invoke directly with values straight off the MCP wire.
 */
export async function callTool(toolName, args) {
  noteActivity();
  try {
    const coerced = coerceArgs(args ?? {});
    const result = await sendToExtension(toolName, coerced);
    if (typeof result === "string") return textResult(result);
    if (result && result.content) return result;
    return textResult(JSON.stringify(result, null, 2));
  } catch (err) {
    return textResult(`Error: ${err.message}`);
  }
}

/**
 * Tear down the connection and pending requests. Idempotent.
 * The caller (process owner) handles process.exit().
 */
export function shutdown() {
  rt.shuttingDown = true;
  if (rt.reconnectTimer) {
    clearTimeout(rt.reconnectTimer);
    rt.reconnectTimer = null;
  }
  for (const [, { reject, timer }] of pendingRequests) {
    clearTimeout(timer);
    reject(new Error("Server shutting down"));
  }
  pendingRequests.clear();
  if (rt.socket && !rt.socket.destroyed) rt.socket.destroy();
  rt.socket = null;
}

