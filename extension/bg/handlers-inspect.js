// Split out of extension/background.js — pure refactor, behavior unchanged.
import { ensureAttached, ensureDomain } from "./cdp.js";
import { consoleMessages, networkByRequestId, networkRequests, state } from "./state.js";
import { isInGroup } from "./tabgroup.js";
import { bootAt, callTimings } from "./timing.js";

export const handlersInspect = {
  async debug_timings(args) {
    const limit = Math.min(Number(args?.limit) || 200, 600);
    let stored = [];
    let storedBootAt = null;
    try {
      const got = await chrome.storage.session.get(["mcp_call_timings", "mcp_boot_at"]);
      stored = got.mcp_call_timings || [];
      storedBootAt = got.mcp_boot_at ?? null;
    } catch {}
    const seen = new Set(callTimings.map((e) => `${e.t}|${e.tool}`));
    const merged = stored.filter((e) => !seen.has(`${e.t}|${e.tool}`)).concat(callTimings);
    const tabs = [];
    const winIds = new Set();
    for (const id of state.tabGroupTabs) {
      try {
        const t = await chrome.tabs.get(id);
        winIds.add(t.windowId);
        tabs.push({ id, windowId: t.windowId, active: t.active, audible: !!t.audible,
                    discarded: !!t.discarded, frozen: !!t.frozen,
                    origin: (t.url || "").split("/").slice(0, 3).join("/") });
      } catch {}
    }
    const windows = [];
    for (const wid of winIds) {
      try {
        const w = await chrome.windows.get(wid);
        windows.push({ id: wid, state: w.state, focused: w.focused });
      } catch {}
    }
    if (args?.clear) {
      callTimings.length = 0;
      state.timingsDirty = 0;
      try { chrome.storage.session.remove(["mcp_call_timings", "mcp_boot_at"]); } catch {}
    }
    return { content: [{ type: "text", text: JSON.stringify({
      bootAt, storedBootAt, now: Date.now(), count: merged.length,
      tabs, windows, timings: merged.slice(-limit),
    }) }] };
  },

  async read_console_messages(args) {
    const { tabId, pattern, limit = 100, onlyErrors, clear } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };

    // Ensure console domain is enabled
    await ensureAttached(tabId);
    await ensureDomain(tabId, "Console");
    await ensureDomain(tabId, "Runtime");

    let msgs = consoleMessages.get(tabId) || [];

    if (onlyErrors) {
      msgs = msgs.filter((m) => ["error", "exception"].includes(m.level));
    }

    if (pattern) {
      try {
        const re = new RegExp(pattern, "i");
        msgs = msgs.filter((m) => re.test(m.text) || re.test(m.level));
      } catch {
        // Invalid regex, use as substring
        msgs = msgs.filter((m) => m.text.includes(pattern));
      }
    }

    msgs = msgs.slice(-limit);

    if (clear) {
      consoleMessages.set(tabId, []);
    }

    if (msgs.length === 0) {
      return { content: [{ type: "text", text: "No console messages matching the pattern." }] };
    }

    const text = msgs
      .map((m) => `[${m.level}] ${m.text}${m.url ? ` (${m.url})` : ""}`)
      .join("\n");

    return { content: [{ type: "text", text: `Console messages (${msgs.length}):\n${text}` }] };
  },

  async read_network_requests(args) {
    const { tabId, urlPattern, limit = 100, clear } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };

    // Ensure network domain is enabled
    await ensureAttached(tabId);
    await ensureDomain(tabId, "Network");

    let reqs = networkRequests.get(tabId) || [];

    if (urlPattern) {
      reqs = reqs.filter((r) => r.url.includes(urlPattern));
    }

    reqs = reqs.slice(-limit);

    if (clear) {
      networkRequests.set(tabId, []);
      networkByRequestId.set(tabId, new Map());
    }

    if (reqs.length === 0) {
      return { content: [{ type: "text", text: "No network requests matching the pattern." }] };
    }

    const text = reqs
      .map((r) => `${r.method} ${r.url} ${r.status ? `→ ${r.status}` : "(pending)"}${r.mimeType ? ` [${r.mimeType}]` : ""}`)
      .join("\n");

    return { content: [{ type: "text", text: `Network requests (${reqs.length}):\n${text}` }] };
  },

};
