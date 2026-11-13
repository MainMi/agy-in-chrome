// Tool schema entries, split out of tool-definitions.js — pure
// refactor, behavior unchanged.
import { z } from "zod";

export const TOOLS_A = [
  {
    name: "tabs_context_mcp",
    description:
      "Get context information about the current MCP tab group. Returns all tab IDs inside the group if it exists. CRITICAL: You must get the context at least once before using other browser automation tools so you know what tabs exist. Each new conversation should create its own new tab (using tabs_create_mcp) rather than reusing existing tabs, unless the user explicitly asks to use an existing tab.",
    paramShape: {
      createIfEmpty: z
        .boolean()
        .optional()
        .describe(
          "Creates a new MCP tab group if none exists, creates a new Window with a new tab group containing an empty tab (which can be used for this conversation). If a MCP tab group already exists, this parameter has no effect."
        )
    }
  },
  {
    name: "tabs_create_mcp",
    description:
      "Creates a new empty tab in the MCP tab group. CRITICAL: You must get the context using tabs_context_mcp at least once before using other browser automation tools so you know what tabs exist.",
    paramShape: {}
  },
  {
    name: "debug_timings",
    description:
      "Diagnostics: return the extension's per-tool-call timing ring buffer (javascript_tool entries carry preMs/evalMs splitting debugger-attach overhead from the Runtime.evaluate itself), plus a live snapshot of every MCP-group tab's scheduling-relevant state (active, audible, discarded, frozen, window state/focus). Survives service-worker restarts via storage.session. Use to localize latency anomalies: a large evalMs with a small preMs means the tab's renderer serviced the evaluation late.",
    paramShape: {
      limit: z.number().optional().describe("Max timing entries to return (default 200, cap 600)."),
      clear: z.boolean().optional().describe("Clear the buffer after reading.")
    }
  },
  {
    name: "tabs_close_mcp",
    description:
      "Close one or more tabs in the MCP tab group. The tab is actually removed from the browser — this is the only correct way to close a tab. Do NOT use navigate to 'about:blank' to 'close' a tab; that just navigates the tab to a blank page and leaves it open. Only tabs in the current MCP group can be closed; requests for tabs outside the group are skipped. If you close the last remaining tab, the MCP group window closes and you'll need tabs_context_mcp({ createIfEmpty: true }) to start a new group.",
    paramShape: {
      tabId: z
        .number()
        .optional()
        .describe(
          "Single tab ID to close. Must be a tab in the current MCP group. Use tabs_context_mcp if you don't have a valid tab ID."
        ),
      tabIds: z
        .array(z.number())
        .optional()
        .describe(
          "Optional batch form: an array of tab IDs to close in one call. Use either `tabId` or `tabIds`, not both."
        )
    }
  },
  {
    name: "navigate",
    description:
      "Navigate to a URL, or go forward/back in browser history. If you don't have a valid tab ID, use tabs_context_mcp first to get available tabs.",
    paramShape: {
      url: z
        .string()
        .describe(
          'The URL to navigate to. Can be provided with or without protocol (defaults to https://). Use "forward" to go forward in history or "back" to go back in history.'
        ),
      tabId: z
        .number()
        .describe(
          "Tab ID to navigate. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        )
    }
  },
  {
    name: "computer",
    description:
      "Use a mouse and keyboard to interact with a web browser, and take screenshots. If you don't have a valid tab ID, use tabs_context_mcp first to get available tabs.\n* Whenever you intend to click on an element like an icon, you should consult a screenshot to determine the coordinates of the element before moving the cursor.\n* If you tried clicking on a program or link but it failed to load, even after waiting, try adjusting your click location so that the tip of the cursor visually falls on the element that you want to click.\n* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.",
    paramShape: {
      action: z
        .enum([
          "left_click",
          "right_click",
          "double_click",
          "triple_click",
          "type",
          "screenshot",
          "wait",
          "scroll",
          "key",
          "left_click_drag",
          "zoom",
          "scroll_to",
          "hover"
        ])
        .describe(
          "The action to perform:\n* `left_click`: Click the left mouse button at the specified coordinates.\n* `right_click`: Click the right mouse button at the specified coordinates to open context menus.\n* `double_click`: Double-click the left mouse button at the specified coordinates.\n* `triple_click`: Triple-click the left mouse button at the specified coordinates.\n* `type`: Type a string of text.\n* `screenshot`: Take a screenshot of the screen.\n* `wait`: Wait for a specified number of seconds.\n* `scroll`: Scroll up, down, left, or right at the specified coordinates.\n* `key`: Press a specific keyboard key.\n* `left_click_drag`: Drag from start_coordinate to coordinate.\n* `zoom`: Take a screenshot of a specific region for closer inspection.\n* `scroll_to`: Scroll an element into view using its element reference ID from read_page or find tools.\n* `hover`: Move the mouse cursor to the specified coordinates or element without clicking. Useful for revealing tooltips, dropdown menus, or triggering hover states."
        ),
      tabId: z
        .number()
        .describe(
          "Tab ID to execute the action on. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        ),
      coordinate: z
        .array(z.number())
        .min(2)
        .max(2)
        .optional()
        .describe(
          "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates. Required for `left_click`, `right_click`, `double_click`, `triple_click`, and `scroll`. For `left_click_drag`, this is the end position."
        ),
      duration: z
        .number()
        .min(0)
        .max(30)
        .optional()
        .describe(
          "The number of seconds to wait. Required for `wait`. Maximum 30 seconds."
        ),
      modifiers: z
        .string()
        .optional()
        .describe(
          'Modifier keys for click actions. Supports: "ctrl", "shift", "alt", "cmd" (or "meta"), "win" (or "windows"). Can be combined with "+" (e.g., "ctrl+shift", "cmd+alt"). Optional.'
        ),
      ref: z
        .string()
        .optional()
        .describe(
          'Element reference ID from read_page or find tools (e.g., "ref_1", "ref_2"). Required for `scroll_to` action. Can be used as alternative to `coordinate` for click actions.'
        ),
      region: z
        .array(z.number())
        .min(4)
        .max(4)
        .optional()
        .describe(
          "(x0, y0, x1, y1): The rectangular region to capture for `zoom`. Coordinates define a rectangle from top-left (x0, y0) to bottom-right (x1, y1) in pixels from the viewport origin. Required for `zoom` action. Useful for inspecting small UI elements like icons, buttons, or text."
        ),
      repeat: z
        .number()
        .min(1)
        .max(100)
        .optional()
        .describe(
          "Number of times to repeat the key sequence. Only applicable for `key` action. Must be a positive integer between 1 and 100. Default is 1. Useful for navigation tasks like pressing arrow keys multiple times."
        ),
      scroll_direction: z
        .enum(["up", "down", "left", "right"])
        .optional()
        .describe("The direction to scroll. Required for `scroll`."),
      scroll_amount: z
        .number()
        .min(1)
        .max(10)
        .optional()
        .describe(
          "The number of scroll wheel ticks. Optional for `scroll`, defaults to 3."
        ),
      start_coordinate: z
        .array(z.number())
        .min(2)
        .max(2)
        .optional()
        .describe("(x, y): The starting coordinates for `left_click_drag`."),
      text: z
        .string()
        .optional()
        .describe(
          'The text to type (for `type` action) or the key(s) to press (for `key` action). For `key` action: Provide space-separated keys (e.g., "Backspace Backspace Delete"). Supports keyboard shortcuts using the platform\'s modifier key (use "cmd" on Mac, "ctrl" on Windows/Linux, e.g., "cmd+a" or "ctrl+a" for select all).'
        ),
      save_to_disk: z
        .boolean()
        .optional()
        .describe(
          "Optional, for the `screenshot` and `zoom` actions. Set true to write the captured image to disk (under ~/.config/agy-in-chrome/screenshots/) and return its absolute path in the result so it can be opened or shared. Default false."
        )
    }
  },
  {
    name: "find",
    description:
      'Find elements on the page using natural language. Can search for elements by their purpose (e.g., "search bar", "login button") or by text content (e.g., "organic mango product"). Returns up to 20 matching elements with references that can be used with other tools. If more than 20 matches exist, you\'ll be notified to use a more specific query. If you don\'t have a valid tab ID, use tabs_context_mcp first to get available tabs.',
    paramShape: {
      query: z
        .string()
        .describe(
          'Natural language description of what to find (e.g., "search bar", "add to cart button", "product title containing organic")'
        ),
      tabId: z
        .number()
        .describe(
          "Tab ID to search in. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        )
    }
  },
];
