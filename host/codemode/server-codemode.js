#!/usr/bin/env node
// Code-mode MCP server: exposes `execute_code` plus two sibling visual tools
// (`screenshot`, `zoom`) that the model uses outside the sandbox when it
// needs to see the page. Everything else from the upstream
// open-claude-in-chrome tool set is reachable via `chrome.*` inside
// execute_code. Image content from screenshot/zoom is preserved by passing
// the upstream MCP CallToolResult through unchanged.
//
// Startup ordering: MCP stdio connects in the foreground (under ~100ms);
// wrangler dev spins up in the background. execute_code handler waits on
// the wrangler-ready promise with a timeout. This avoids Claude Code's
// MCP startup window timing out on the wrangler boot.

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import {
  connectUpstream,
  startCallbackServer,
  startWorkerd,
  makeRunCode,
  prewarmSandbox,
  buildExecuteCodeDescription,
  packExecuteResult,
  installCleanup,
  SERVER_INSTRUCTIONS
} from "./common.js";
import { generateTsApi } from "../tool-definitions.js";

const NAMESPACE = "chrome";

const EXTRA_NOTES = `
- This MCP server exposes only three tools to you: \`execute_code\`, \`screenshot\`, and \`zoom\`. Everything else (navigate, find, form_input, read_page, get_page_text, computer clicks/types/scrolls, etc.) is available inside \`execute_code\` as \`${NAMESPACE}.*\`.
- Prefer \`execute_code\` whenever you can plan two or more actions in advance. The round-trip savings compound quickly.`;

async function main() {
  // --- Phase 1: fast init (everything except wrangler) ---
  const { client: upstream, tools: upstreamTools } = await connectUpstream();
  const { server: callbackServer, port: callbackPort } =
    await startCallbackServer(upstream);

  // Generate the TS API in-process — no /generate fetch, no wrangler needed.
  const apiBlock = generateTsApi(upstreamTools, NAMESPACE);
  const description = buildExecuteCodeDescription({
    apiBlock,
    namespace: NAMESPACE,
    extraNotes: EXTRA_NOTES
  });

  // --- Phase 2: spawn wrangler in the background ---
  let runCode = null;
  let runCodeError = null;
  let wranglerProc = null;
  const wranglerReady = (async () => {
    try {
      const { proc, port: workerPort } = await startWorkerd({
        variant: "codemode"
      });
      wranglerProc = proc;
      runCode = makeRunCode({
        workerPort,
        callbackUrl: `http://127.0.0.1:${callbackPort}`,
        tools: upstreamTools,
        namespace: NAMESPACE
      });
      await prewarmSandbox(runCode);
    } catch (err) {
      runCodeError = err;
      process.stderr.write(
        `[codemode] wrangler init failed: ${err?.message ?? err}\n`
      );
    }
  })();

  installCleanup({
    wranglerProc: () => wranglerProc,
    callbackServer,
    upstreamClient: upstream
  });

  const server = new McpServer(
    { name: "agy-in-chrome-codemode", version: "1.0.0" },
    { instructions: SERVER_INSTRUCTIONS }
  );

  server.tool(
    "execute_code",
    description,
    {
      code: z
        .string()
        .describe(
          "JavaScript async arrow function body to execute in the sandbox. See the tool description for the available API."
        )
    },
    async ({ code }) => {
      if (!runCode && !runCodeError) {
        await Promise.race([
          wranglerReady,
          new Promise((resolve) => setTimeout(resolve, 30_000))
        ]);
      }
      if (runCodeError) {
        return {
          content: [
            {
              type: "text",
              text: `Sandbox unavailable: ${runCodeError.message ?? runCodeError}`
            }
          ],
          isError: true
        };
      }
      if (!runCode) {
        return {
          content: [
            {
              type: "text",
              text: "Sandbox not ready after 30s — wrangler is still starting. Retry the call shortly."
            }
          ],
          isError: true
        };
      }
      return packExecuteResult(await runCode(code));
    }
  );

  server.tool(
    "screenshot",
    "Take a screenshot of the specified tab and return it as a visible image. Use this whenever you need to look at the page to decide what to do next — image data is NOT visible from inside execute_code, so screenshots must be taken via this tool. If you don't have a valid tab ID yet, call execute_code with `chrome.tabs_context_mcp({ createIfEmpty: true })` first to get one.",
    {
      tabId: z
        .number()
        .describe(
          "Tab ID to screenshot. Must be a tab in the current group. Use execute_code with chrome.tabs_context_mcp if you don't have a valid tab ID."
        )
    },
    async ({ tabId }) =>
      upstream.callTool({
        name: "computer",
        arguments: { action: "screenshot", tabId }
      })
  );

  server.tool(
    "zoom",
    "Take a screenshot of a specific rectangular region of the tab for closer inspection. Returns a visible image. Useful for reading small UI elements, icons, or text that are hard to see in a full-page screenshot.",
    {
      tabId: z
        .number()
        .describe(
          "Tab ID to zoom into. Must be a tab in the current group."
        ),
      region: z
        .array(z.number())
        .min(4)
        .max(4)
        .describe(
          "(x0, y0, x1, y1): the rectangular region to capture, in viewport pixels from the top-left."
        )
    },
    async ({ tabId, region }) =>
      upstream.callTool({
        name: "computer",
        arguments: { action: "zoom", tabId, region }
      })
  );

  // Connect MCP stdio NOW so Claude Code's initialize handshake completes
  // immediately. wranglerReady continues in the background; execute_code
  // calls block on it until it resolves.
  await server.connect(new StdioServerTransport());
}

main().catch((err) => {
  process.stderr.write(`[codemode] fatal: ${err?.stack ?? err}\n`);
  process.exit(1);
});
