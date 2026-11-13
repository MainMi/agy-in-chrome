// The 25 agy-in-chrome tool definitions, extracted as data so both
// the standard stdio MCP server (host/mcp-server.js) and the codemode +
// hybrid servers can register them without duplicating the schemas.
//
// Each entry is { name, description, paramShape } where paramShape is the
// object literal of zod values passed to McpServer.tool(). Wrapping it in
// z.object(paramShape) yields the full input schema.

import { z } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";

import { TOOLS_A } from "./tool-defs-a.js";
import { TOOLS_B } from "./tool-defs-b.js";
import { TOOLS_C } from "./tool-defs-c.js";
import { TOOLS_D } from "./tool-defs-d.js";

export const TOOLS = [...TOOLS_A, ...TOOLS_B, ...TOOLS_C, ...TOOLS_D];

/**
 * Convert a tool's paramShape to a JSON Schema object suitable for
 * MCP tools/list, codemode TS-API generation, etc.
 */
export function toolInputJsonSchema(tool) {
  const schema = zodToJsonSchema(z.object(tool.paramShape), {
    target: "openApi3",
    $refStrategy: "none"
  });
  // zodToJsonSchema wraps with $schema by default; strip it for cleanliness
  if (schema && typeof schema === "object") {
    delete schema.$schema;
  }
  return schema;
}

export function toolsAsJsonSchemaList() {
  return TOOLS.map((t) => ({
    name: t.name,
    description: t.description,
    inputSchema: toolInputJsonSchema(t)
  }));
}
export { generateTsApi } from "./tool-defs-tsapi.js";
