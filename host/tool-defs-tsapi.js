// In-process TS-API generator, split out of tool-definitions.js —
// pure refactor, behavior unchanged.

// --- In-process TS-API generator (no workerd needed) -------------------------
//
// Used by the codemode + hybrid MCP servers to build execute_code's
// description synchronously at startup, so server.connect(stdio) can happen
// before wrangler is ready. Mirrors the output shape of
// @cloudflare/codemode's generateTypesFromJsonSchema closely enough for the
// model: namespaced declare const + per-tool JSDoc + per-param descriptions.

function pascal(name) {
  return name
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .split("_")
    .filter(Boolean)
    .map((s) => s[0].toUpperCase() + s.slice(1))
    .join("");
}

function escapeJsdoc(s) {
  return String(s).replace(/\*\//g, "*\\/");
}

function tsType(schema) {
  if (!schema || typeof schema !== "object") return "unknown";
  if (Array.isArray(schema.enum) && schema.enum.length > 0) {
    return schema.enum.map((v) => JSON.stringify(v)).join(" | ");
  }
  if (schema.const !== undefined) return JSON.stringify(schema.const);
  if (schema.anyOf || schema.oneOf) {
    const variants = (schema.anyOf || schema.oneOf).map(tsType);
    return variants.join(" | ");
  }
  switch (schema.type) {
    case "string":
      return "string";
    case "integer":
    case "number":
      return "number";
    case "boolean":
      return "boolean";
    case "array":
      return `(${tsType(schema.items || {})})[]`;
    case "object": {
      const required = new Set(schema.required || []);
      const props = schema.properties || {};
      const fields = Object.entries(props).map(([k, v]) => {
        const opt = required.has(k) ? "" : "?";
        const doc = v && v.description ? `    /** ${escapeJsdoc(String(v.description).replace(/\s+/g, " "))} */\n    ` : "    ";
        return `${doc}${k}${opt}: ${tsType(v)};`;
      });
      return `{\n${fields.join("\n")}\n}`;
    }
    default:
      return "unknown";
  }
}

/**
 * Build the TypeScript API block exposed to the model inside execute_code.
 * `tools` is a list of { name, description, inputSchema } records (the same
 * shape toolsAsJsonSchemaList() returns); `namespace` controls the binding
 * name (e.g. "chrome" → `declare const chrome: {...}`).
 */
export function generateTsApi(tools, namespace = "codemode") {
  let types = "";
  let api = "";
  for (const t of tools) {
    const typeName = pascal(t.name);
    const inputBody = tsType(t.inputSchema || { type: "object" });
    types += `\ntype ${typeName}Input = ${inputBody}`;
    types += `\ntype ${typeName}Output = unknown`;

    const descLine = t.description
      ? escapeJsdoc(String(t.description).replace(/\s+/g, " "))
      : t.name;
    api += `\n\t/**\n\t * ${descLine}\n\t */`;
    api += `\n\t${t.name}: (input: ${typeName}Input) => Promise<${typeName}Output>;`;
    api += "\n";
  }
  return `${types}\n\ndeclare const ${namespace}: {${api}}`.trim();
}

