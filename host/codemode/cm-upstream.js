// Upstream/runtime connection plumbing, split out of common.js — pure
// refactor, behavior unchanged.
import http from "node:http";
import net from "node:net";
import { init as runtimeInit, callTool as runtimeCallTool, shutdown as runtimeShutdown } from "../tool-runtime.js";
import { toolsAsJsonSchemaList } from "../tool-definitions.js";
import { log } from "./cm-util.js";

export async function pickFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const port = srv.address().port;
      srv.close(() => resolve(port));
    });
  });
}

export async function connectUpstream() {
  // Talk to the tool runtime in-process — no child mcp-server.js, no extra
  // stdio MCP framing layer. The shim mirrors the old McpServer client API
  // (callTool / close) so the rest of common.js doesn't have to care.
  await runtimeInit();
  const tools = toolsAsJsonSchemaList();
  log(`runtime ready with ${tools.length} tools`);
  const client = {
    callTool: ({ name, arguments: args }) => runtimeCallTool(name, args),
    close: () => runtimeShutdown()
  };
  return { client, tools };
}

function extractText(result) {
  const blocks = result?.content;
  if (!Array.isArray(blocks)) return null;
  return blocks
    .filter((b) => b?.type === "text" && typeof b.text === "string")
    .map((b) => b.text)
    .join("\n") || null;
}

// Try to parse `text` as JSON, including the common case where the upstream
// tool emits a JSON object/array followed by a human-readable trailing
// section. Returns { value, trailing } or null when no JSON was found.
function parseLeadingJson(text) {
  if (typeof text !== "string" || text.length === 0) return null;
  // Skip leading whitespace.
  let i = 0;
  while (i < text.length && /\s/.test(text[i])) i++;
  const first = text[i];
  if (first !== "{" && first !== "[") return null;
  const close = first === "{" ? "}" : "]";
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let j = i; j < text.length; j++) {
    const c = text[j];
    if (escape) { escape = false; continue; }
    if (c === "\\" && inString) { escape = true; continue; }
    if (c === '"') { inString = !inString; continue; }
    if (inString) continue;
    if (c === first) depth++;
    else if (c === close) {
      depth--;
      if (depth === 0) {
        const candidate = text.slice(i, j + 1);
        try {
          const value = JSON.parse(candidate);
          const trailing = text.slice(j + 1).trim();
          return { value, trailing };
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

// Collapse an MCP CallToolResult envelope into the most useful shape for
// sandbox code. Single text block → the parsed JSON if the text is or
// starts with JSON (trailing human-readable text is preserved as `_text`
// only when the JSON value is an object), otherwise the raw string.
// Multiple blocks → an array. Image and resource blocks become opaque
// markers since their content isn't visible from inside execute_code.
export function unwrapMcpResult(result) {
  const blocks = result?.content;
  if (!Array.isArray(blocks)) return result;
  if (blocks.length === 1 && blocks[0]?.type === "text") {
    const t = blocks[0].text;
    const parsed = parseLeadingJson(t);
    if (parsed) {
      if (parsed.trailing && typeof parsed.value === "object" && parsed.value !== null && !Array.isArray(parsed.value)) {
        return { ...parsed.value, _text: parsed.trailing };
      }
      return parsed.value;
    }
    return t;
  }
  return blocks.map((b) => {
    if (b?.type === "text") {
      const parsed = parseLeadingJson(b.text);
      return { type: "text", value: parsed ? parsed.value : b.text };
    }
    if (b?.type === "image") {
      return {
        type: "image",
        mimeType: b.mimeType,
        note: "image data not visible from inside execute_code"
      };
    }
    if (b?.type === "resource") {
      return { type: "resource", uri: b.resource?.uri };
    }
    return b;
  });
}

export function startCallbackServer(upstream) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(async (req, res) => {
      const m = req.url && req.url.match(/^\/tool\/(.+)$/);
      if (!m || req.method !== "POST") {
        res.writeHead(404).end();
        return;
      }
      const name = decodeURIComponent(m[1]);
      let body = "";
      for await (const chunk of req) body += chunk;
      let args;
      try {
        args = body ? JSON.parse(body) : {};
      } catch (err) {
        res.writeHead(400, { "content-type": "application/json" });
        res.end(JSON.stringify({ error: `invalid JSON: ${err.message}` }));
        return;
      }
      try {
        const result = await upstream.callTool({ name, arguments: args });
        if (result?.isError) {
          const msg = extractText(result) ?? `tool ${name} errored`;
          res.writeHead(500, { "content-type": "application/json" });
          res.end(JSON.stringify({ error: msg }));
          return;
        }
        const unwrapped = unwrapMcpResult(result);
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify(unwrapped));
      } catch (err) {
        res.writeHead(500, { "content-type": "application/json" });
        res.end(JSON.stringify({ error: err?.message ?? String(err) }));
      }
    });
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      log(`callback server on :${port}`);
      resolve({ server, port });
    });
  });
}

