// Split out of extension/background.js — pure refactor, behavior unchanged.
import { attachedTabs, state } from "./state.js";
import { ensureTabGroup, formatTabContext, isInGroup } from "./tabgroup.js";

export const handlersTabs = {
  async tabs_context_mcp(args) {
    await ensureTabGroup(args.createIfEmpty);
    if (state.tabGroupId === null) {
      return {
        content: [{ type: "text", text: "No MCP tab group exists. Use createIfEmpty: true to create one." }],
      };
    }
    const tabs = await chrome.tabs.query({ groupId: state.tabGroupId });
    return formatTabContext(tabs);
  },

  async tabs_create_mcp(args) {
    await ensureTabGroup(true);
    // Create the tab INSIDE the MCP group's own window and do NOT select it:
    // automation must never yank the operator away from what they are looking
    // at. Without windowId the tab lands in whatever window is currently
    // focused — i.e. the operator's — which is exactly the interruption we
    // are avoiding. Use the set_tab_focus tool to surface a tab deliberately.
    let windowId;
    try {
      const groupTabs = await chrome.tabs.query({ groupId: state.tabGroupId });
      windowId = groupTabs[0]?.windowId;
    } catch {}
    const tab = await chrome.tabs.create(
      windowId ? { active: false, windowId } : { active: false }
    );
    await chrome.tabs.group({ tabIds: [tab.id], groupId: state.tabGroupId });
    state.tabGroupTabs.add(tab.id);
    const tabs = await chrome.tabs.query({ groupId: state.tabGroupId });
    const result = formatTabContext(tabs);
    result.content[0].text = `Created new tab. Tab ID: ${tab.id}\n\n` + result.content[0].text;
    return result;
  },

  async tabs_close_mcp(args) {
    // Accept either a single tabId (most common) or a tabIds array for
    // batch close. Validate every id is actually in the current MCP group
    // so we never close the user's other tabs.
    const requested = Array.isArray(args?.tabIds)
      ? args.tabIds
      : args?.tabId !== undefined
        ? [args.tabId]
        : [];
    if (requested.length === 0) {
      return {
        content: [
          {
            type: "text",
            text: "No tabId provided. Pass `tabId: <number>` or `tabIds: [<number>, ...]`."
          }
        ]
      };
    }
    const inGroup = [];
    const skipped = [];
    for (const id of requested) {
      const idNum = typeof id === "string" ? Number(id) : id;
      if (await isInGroup(idNum)) inGroup.push(idNum);
      else skipped.push(idNum);
    }
    if (inGroup.length === 0) {
      return {
        content: [
          {
            type: "text",
            text: `None of the requested tabs are in the MCP group. Requested: [${requested.join(", ")}]. Use tabs_context_mcp to see what is in the group.`
          }
        ]
      };
    }
    // chrome.tabs.remove force-closes — no beforeunload prompt. Detach any
    // CDP debuggers proactively so the onRemoved handler doesn't race.
    for (const id of inGroup) {
      if (attachedTabs.has(id)) {
        try { await chrome.debugger.detach({ tabId: id }); } catch {}
        attachedTabs.delete(id);
      }
    }
    await chrome.tabs.remove(inGroup);
    for (const id of inGroup) state.tabGroupTabs.delete(id);

    // Closing the last tab in the group also closes the window; the group
    // becomes invalid. Reflect that in the response so the model doesn't
    // try to reuse stale tabIds.
    let tabs = [];
    try {
      if (state.tabGroupId !== null) {
        tabs = await chrome.tabs.query({ groupId: state.tabGroupId });
      }
    } catch {}
    if (tabs.length === 0) {
      state.tabGroupId = null;
      state.tabGroupTabs.clear();
      return {
        content: [
          {
            type: "text",
            text:
              `Closed ${inGroup.length} tab(s): [${inGroup.join(", ")}]` +
              (skipped.length ? `. Skipped (not in group): [${skipped.join(", ")}]` : "") +
              `. The MCP tab group is now empty — the window has been closed. Use tabs_context_mcp({ createIfEmpty: true }) to start a new group.`
          }
        ]
      };
    }
    const result = formatTabContext(tabs);
    result.content[0].text =
      `Closed ${inGroup.length} tab(s): [${inGroup.join(", ")}]` +
      (skipped.length ? `. Skipped (not in group): [${skipped.join(", ")}]` : "") +
      `.\n\n` +
      result.content[0].text;
    return result;
  },

  async navigate(args) {
    const { url, tabId } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };

    if (url === "back") {
      await chrome.tabs.goBack(tabId);
    } else if (url === "forward") {
      await chrome.tabs.goForward(tabId);
    } else {
      let targetUrl = url;
      // Strip any malformed protocol prefix before normalizing
      if (!targetUrl.match(/^https?:\/\//i) && !targetUrl.startsWith("about:") && !targetUrl.startsWith("chrome:") && !targetUrl.startsWith("brave:")) {
        // Remove any partial/broken protocol prefix (e.g., "hps://", "http:/", "ht://")
        targetUrl = targetUrl.replace(/^[a-z]{1,5}:\/+/i, "");
        targetUrl = "https://" + targetUrl;
      }
      try {
        new URL(targetUrl); // Validate URL before passing to Chrome
      } catch {
        return { content: [{ type: "text", text: `Invalid URL: "${url}". Could not parse as a valid URL.` }] };
      }
      await chrome.tabs.update(tabId, { url: targetUrl });
    }

    // Wait for page load — short timeout to avoid service worker idle kill
    // If the page takes longer, the caller can use screenshot/wait to check
    await new Promise((resolve) => {
      const listener = (updatedTabId, info) => {
        if (updatedTabId === tabId && info.status === "complete") {
          chrome.tabs.onUpdated.removeListener(listener);
          resolve();
        }
      };
      chrome.tabs.onUpdated.addListener(listener);
      // 10s max — enough for most pages, avoids service worker timeout
      setTimeout(() => {
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }, 10000);
    });

    const tab = await chrome.tabs.get(tabId);
    const tabs = await chrome.tabs.query({ groupId: state.tabGroupId });
    const loading = tab.status !== "complete" ? " (still loading)" : "";
    const text = `Navigated to ${tab.url}${loading}.\n## Pages\n` +
      tabs.map((t, i) => `${i + 1}: ${t.url}${t.id === tabId ? " [selected]" : ""}`).join("\n");

    return { content: [{ type: "text", text }] };
  },

};
