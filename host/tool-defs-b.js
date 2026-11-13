// Tool schema entries, split out of tool-definitions.js — pure
// refactor, behavior unchanged.
import { z } from "zod";

export const TOOLS_B = [
  {
    name: "form_input",
    description:
      "Set values in form elements using element reference ID from the read_page tool. If you don't have a valid tab ID, use tabs_context_mcp first to get available tabs.",
    paramShape: {
      ref: z
        .string()
        .describe(
          'Element reference ID from the read_page tool (e.g., "ref_1", "ref_2")'
        ),
      value: z
        .union([z.string(), z.boolean(), z.number()])
        .describe(
          "The value to set. For checkboxes use boolean, for selects use option value or text, for other inputs use appropriate string/number"
        ),
      tabId: z
        .number()
        .describe(
          "Tab ID to set form value in. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        )
    }
  },
  {
    name: "get_page_text",
    description:
      "Extract raw text content from the page, prioritizing article content. Ideal for reading articles, blog posts, or other text-heavy pages. Returns plain text without HTML formatting. If you don't have a valid tab ID, use tabs_context_mcp first to get available tabs.",
    paramShape: {
      tabId: z
        .number()
        .describe(
          "Tab ID to extract text from. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        )
    }
  },
  {
    name: "gif_creator",
    description:
      "Manage GIF recording and export for browser automation sessions. Control when to start/stop recording browser actions (clicks, scrolls, navigation), then export as an animated GIF with visual overlays (click indicators, action labels, progress bar, watermark). All operations are scoped to the tab's group. When starting recording, take a screenshot immediately after to capture the initial state as the first frame. When stopping recording, take a screenshot immediately before to capture the final state as the last frame. For export, either provide 'coordinate' to drag/drop upload to a page element, or set 'download: true' to download the GIF.",
    paramShape: {
      action: z
        .enum(["start_recording", "stop_recording", "export", "clear"])
        .describe(
          "Action to perform: 'start_recording' (begin capturing), 'stop_recording' (stop capturing but keep frames), 'export' (generate and export GIF), 'clear' (discard frames)"
        ),
      tabId: z
        .number()
        .describe("Tab ID to identify which tab group this operation applies to"),
      download: z
        .boolean()
        .optional()
        .describe(
          "Always set this to true for the 'export' action only. This causes the gif to be downloaded in the browser."
        ),
      filename: z
        .string()
        .optional()
        .describe(
          "Optional filename for exported GIF (default: 'recording-[timestamp].gif'). For 'export' action only."
        ),
      options: z
        .object({
          showClickIndicators: z
            .boolean()
            .optional()
            .describe("Show orange circles at click locations (default: true)"),
          showDragPaths: z
            .boolean()
            .optional()
            .describe("Show red arrows for drag actions (default: true)"),
          showActionLabels: z
            .boolean()
            .optional()
            .describe("Show black labels describing actions (default: true)"),
          showProgressBar: z
            .boolean()
            .optional()
            .describe("Show orange progress bar at bottom (default: true)"),
          showWatermark: z
            .boolean()
            .optional()
            .describe("Show AGY watermark (default: true)"),
          quality: z
            .number()
            .optional()
            .describe(
              "GIF compression quality, 1-30 (lower = better quality, slower encoding). Default: 10"
            )
        })
        .optional()
        .describe(
          "Optional GIF enhancement options for 'export' action. Properties: showClickIndicators (bool), showDragPaths (bool), showActionLabels (bool), showProgressBar (bool), showWatermark (bool), quality (number 1-30). All default to true except quality (default: 10)."
        )
    }
  },
  {
    name: "javascript_tool",
    description:
      "Execute JavaScript code in the context of the current page. The code runs in the page's context and can interact with the DOM, window object, and page variables. Returns the result of the last expression or any thrown errors. If you don't have a valid tab ID, use tabs_context_mcp first to get available tabs.",
    paramShape: {
      action: z
        .literal("javascript_exec")
        .describe("Must be set to 'javascript_exec'"),
      text: z
        .string()
        .describe(
          "The JavaScript code to execute. The code will be evaluated in the page context. The result of the last expression will be returned automatically. Do NOT use 'return' statements - just write the expression you want to evaluate (e.g., 'window.myData.value' not 'return window.myData.value'). You can access and modify the DOM, call page functions, and interact with page variables."
        ),
      tabId: z
        .number()
        .describe(
          "Tab ID to execute the code in. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        )
    }
  },
  {
    name: "read_console_messages",
    description:
      "Read browser console messages (console.log, console.error, console.warn, etc.) from a specific tab. Useful for debugging JavaScript errors, viewing application logs, or understanding what's happening in the browser console. Returns console messages from the current domain only. If you don't have a valid tab ID, use tabs_context_mcp first to get available tabs. IMPORTANT: Always provide a pattern to filter messages - without a pattern, you may get too many irrelevant messages.",
    paramShape: {
      tabId: z
        .number()
        .describe(
          "Tab ID to read console messages from. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        ),
      pattern: z
        .string()
        .optional()
        .describe(
          "Regex pattern to filter console messages. Only messages matching this pattern will be returned (e.g., 'error|warning' to find errors and warnings, 'MyApp' to filter app-specific logs). You should always provide a pattern to avoid getting too many irrelevant messages."
        ),
      limit: z
        .number()
        .optional()
        .describe(
          "Maximum number of messages to return. Defaults to 100. Increase only if you need more results."
        ),
      onlyErrors: z
        .boolean()
        .optional()
        .describe(
          "If true, only return error and exception messages. Default is false (return all message types)."
        ),
      clear: z
        .boolean()
        .optional()
        .describe(
          "If true, clear the console messages after reading to avoid duplicates on subsequent calls. Default is false."
        )
    }
  },
  {
    name: "read_network_requests",
    description:
      "Read HTTP network requests (XHR, Fetch, documents, images, etc.) from a specific tab. Useful for debugging API calls, monitoring network activity, or understanding what requests a page is making. Returns all network requests made by the current page, including cross-origin requests. Requests are automatically cleared when the page navigates to a different domain. If you don't have a valid tab ID, use tabs_context_mcp first to get available tabs.",
    paramShape: {
      tabId: z
        .number()
        .describe(
          "Tab ID to read network requests from. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        ),
      urlPattern: z
        .string()
        .optional()
        .describe(
          "Optional URL pattern to filter requests. Only requests whose URL contains this string will be returned (e.g., '/api/' to filter API calls, 'example.com' to filter by domain)."
        ),
      limit: z
        .number()
        .optional()
        .describe(
          "Maximum number of requests to return. Defaults to 100. Increase only if you need more results."
        ),
      clear: z
        .boolean()
        .optional()
        .describe(
          "If true, clear the network requests after reading to avoid duplicates on subsequent calls. Default is false."
        )
    }
  },
  {
    name: "read_page",
    description:
      "Get an accessibility tree representation of elements on the page. By default returns all elements including non-visible ones. Output is limited to 50000 characters by default. If the output exceeds this limit, you will receive an error asking you to specify a smaller depth or focus on a specific element using ref_id. Optionally filter for only interactive elements. If you don't have a valid tab ID, use tabs_context_mcp first to get available tabs.",
    paramShape: {
      tabId: z
        .number()
        .describe(
          "Tab ID to read from. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        ),
      filter: z
        .enum(["interactive", "all"])
        .optional()
        .describe(
          'Filter elements: "interactive" for buttons/links/inputs only, "all" for all elements including non-visible ones (default: all elements)'
        ),
      depth: z
        .number()
        .optional()
        .describe(
          "Maximum depth of the tree to traverse (default: 15). Use a smaller depth if output is too large."
        ),
      ref_id: z
        .string()
        .optional()
        .describe(
          "Reference ID of a parent element to read. Will return the specified element and all its children. Use this to focus on a specific part of the page when output is too large."
        ),
      max_chars: z
        .number()
        .optional()
        .describe(
          "Maximum characters for output (default: 50000). Set to a higher value if your client can handle large outputs."
        )
    }
  },
];
