// Tool schema entries, split out of tool-definitions.js — pure
// refactor, behavior unchanged.
import { z } from "zod";

export const TOOLS_C = [
  {
    name: "resize_window",
    description:
      "Resize the current browser window to specified dimensions. Useful for testing responsive designs or setting up specific screen sizes. If you don't have a valid tab ID, use tabs_context_mcp first to get available tabs.",
    paramShape: {
      width: z.number().describe("Target window width in pixels"),
      height: z.number().describe("Target window height in pixels"),
      tabId: z
        .number()
        .describe(
          "Tab ID to get the window for. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        )
    }
  },
  {
    name: "shortcuts_list",
    description:
      "List all available shortcuts and workflows (shortcuts and workflows are interchangeable). Returns shortcuts with their commands, descriptions, and whether they are workflows. Use shortcuts_execute to run a shortcut or workflow.",
    paramShape: {
      tabId: z
        .number()
        .describe(
          "Tab ID to list shortcuts from. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        )
    }
  },
  {
    name: "shortcuts_execute",
    description:
      "Execute a shortcut or workflow by running it in a new sidepanel window using the current tab (shortcuts and workflows are interchangeable). Use shortcuts_list first to see available shortcuts. This starts the execution and returns immediately - it does not wait for completion.",
    paramShape: {
      tabId: z
        .number()
        .describe(
          "Tab ID to execute the shortcut on. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        ),
      shortcutId: z
        .string()
        .optional()
        .describe("The ID of the shortcut to execute"),
      command: z
        .string()
        .optional()
        .describe(
          "The command name of the shortcut to execute (e.g., 'debug', 'summarize'). Do not include the leading slash."
        )
    }
  },
  {
    name: "switch_browser",
    description:
      "Hand off browser automation to a different Chromium browser (Chrome, Brave, Edge). One browser drives at a time. Calling this releases the current browser's hold on the shared runtime for ~15s so a target browser with this extension enabled can take over automatically (no restart). Tell the user to enable the extension in the target browser first. After calling, wait a few seconds and use tabs_context_mcp to confirm which browser is now active.",
    paramShape: {}
  },
  {
    name: "update_plan",
    description:
      "Present a plan to the user for approval before taking actions. The user will see the domains you intend to visit and your approach. Once approved, you can proceed with actions on the approved domains without additional permission prompts.",
    paramShape: {
      domains: z
        .array(z.string())
        .describe(
          "List of domains you will visit (e.g., ['github.com', 'stackoverflow.com']). These domains will be approved for the session when the user accepts the plan."
        ),
      approach: z
        .array(z.string())
        .describe(
          "High-level description of what you will do. Focus on outcomes and key actions, not implementation details. Be concise - aim for 3-7 items."
        )
    }
  },
  {
    name: "debug",
    description:
      "Read what this extension actually did, in one timestamped stream. This holds what tool responses deliberately LEAVE OUT — never a copy of them: the arguments a call was made with, what a click landed on even when it landed correctly and the response stayed silent, the coordinate space a screenshot was captured in, CDP commands and their durations, and input dispatches that failed after the send returned. Use it to verify an action had the effect you intended, or to find where time went, rather than inferring either from a result that reads the same whether it worked or not. Reports its own limits on every read: how many events were dropped, and how far back the buffer reaches, so a short log is never mistaken for a quiet system.",
    paramShape: {
      limit: z
        .number()
        .optional()
        .describe("How many of the most recent matching events to show (default 100, max 1000)."),
      kind: z
        .enum(["tool", "cdp", "input", "hit", "port"])
        .optional()
        .describe(
          'Only this kind of event. "tool" = calls in and out with their result line; "cdp" = protocol commands and durations; "input" = dispatched mouse/cursor events with coordinates; "hit" = what a click landed on; "port" = native host connect/disconnect.'
        ),
      filter: z
        .string()
        .optional()
        .describe(
          'Free-form match over each event, as a regex (falls back to plain substring if it will not compile). Examples: "mousePressed", "WARNING", "left_click|type".'
        ),
      tabId: z.number().optional().describe("Only events for this tab."),
      since_ms: z
        .number()
        .optional()
        .describe("Only events from the last N milliseconds — e.g. 5000 to see just what the last action did."),
      clear: z
        .boolean()
        .optional()
        .describe("Empty the buffer after reading, so the next read starts clean around one action.")
    }
  },
  {
    name: "get_config",
    description:
      "Read the browser-automation settings this extension honors. Returns the default config (applies to every tab), any per-tab overrides, and a catalog of recognized settings with what each one does — that catalog is the source of truth, so read it before setting anything. Pass tabId to also see the config that actually applies to that tab (per-tab override merged over the default).",
    paramShape: {
      tabId: z
        .number()
        .optional()
        .describe(
          "Optional. Also report the effective config for this tab (its override merged over the default)."
        )
    }
  },
  {
    name: "set_config",
    description:
      "Change a browser-automation setting. Call get_config first to see the recognized settings and what they do. Omit tabId to set the default for every tab, or pass tabId to override the setting for that one tab only (per-tab overrides win, and are dropped when the tab closes). Pass value: null to clear a setting and fall back to the default. Settings persist, so a default you set stays on until you change it.",
    paramShape: {
      key: z
        .string()
        .describe("Setting name, as listed by get_config (e.g. \"humanize\")."),
      value: z
        .union([z.boolean(), z.number(), z.string(), z.null()])
        .describe("New value for the setting. Use null to clear it."),
      tabId: z
        .number()
        .optional()
        .describe(
          "Optional. Scope this change to a single tab instead of changing the default for all tabs."
        )
    }
  },
  {
    name: "set_tab_focus",
    description:
      "Bring a tab to the user's attention: make it the selected tab in its window, and optionally raise that window in front of every other application. Browser automation never needs this — every tool drives background tabs normally, and nothing else here selects a tab or steals focus — so this is yours to use at your discretion, when the user should actually be looking at something. Reach for it when: they asked to be kept in the loop or told about problems and you hit something worth their eyes; you need a decision or confirmation before doing something consequential or irreversible; you have finished something they are waiting to see; or the page only behaves correctly while its tab is visible (media playback, visibility-dependent apps, timers that throttle in the background). Default to not calling it — routine progress does not warrant an interruption.",
    paramShape: {
      tabId: z
        .number()
        .describe(
          "Tab ID to surface. Must be a tab in the current group. Use tabs_context_mcp if you don't have a valid tab ID."
        ),
      focus_window: z
        .boolean()
        .optional()
        .describe(
          "Also raise the browser window above every other application, interrupting whatever the user is doing right now, in whatever app they are in. Use when the interruption is genuinely warranted; leave false (default) to select the tab quietly so they see it whenever they next look at the browser."
        )
    }
  },
];
