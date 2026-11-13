// Split out of extension/background.js — pure refactor, behavior unchanged.
import { state } from "./state.js";

// --- Tab group management ---
export async function ensureTabGroup(createIfEmpty) {
  // Check if our tab group still exists
  if (state.tabGroupId !== null) {
    try {
      const group = await chrome.tabGroups.get(state.tabGroupId);
      if (group) {
        // Verify tabs are still in the group
        const tabs = await chrome.tabs.query({ groupId: state.tabGroupId });
        state.tabGroupTabs = new Set(tabs.map((t) => t.id));
        if (state.tabGroupTabs.size > 0) return;
      }
    } catch {
      state.tabGroupId = null;
      state.tabGroupTabs.clear();
    }
  }

  if (!createIfEmpty) return;

  // Create a new window with a tab, group it. focused:false — the window is
  // created and rendered, but does not jump in front of whatever the operator
  // is doing. set_tab_focus raises it on purpose when that is actually wanted.
  const win = await chrome.windows.create({ focused: false, url: "about:blank" });
  const tab = win.tabs[0];
  const groupId = await chrome.tabs.group({ tabIds: [tab.id] });
  await chrome.tabGroups.update(groupId, { title: "AGY", color: "blue" });
  state.tabGroupId = groupId;
  state.tabGroupTabs = new Set([tab.id]);
}

export function formatTabContext(tabs) {
  const available = tabs.map((t) => ({
    tabId: t.id,
    title: t.title || "Untitled",
    url: t.url || "",
  }));

  let text = `Tab Context:\n- Available tabs:\n`;
  for (const t of available) {
    text += `  \u2022 tabId ${t.tabId}: "${t.title}" (${t.url})\n`;
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({ availableTabs: available, tabGroupId: state.tabGroupId }) + "\n\n" + text,
      },
    ],
  };
}

export async function isInGroup(tabId) {
  // Always check live state — in-memory state.tabGroupTabs can be stale after service worker restart
  try {
    const tab = await chrome.tabs.get(tabId);
    if (tab.groupId !== -1) {
      // Recover state.tabGroupId if we lost it (service worker restart)
      if (state.tabGroupId === null) {
        try {
          const group = await chrome.tabGroups.get(tab.groupId);
          if (group.title === "MCP") {
            state.tabGroupId = group.id;
            const groupTabs = await chrome.tabs.query({ groupId: state.tabGroupId });
            state.tabGroupTabs = new Set(groupTabs.map((t) => t.id));
          }
        } catch {}
      }
      return tab.groupId === state.tabGroupId;
    }
    return state.tabGroupTabs.has(tabId);
  } catch {
    return false;
  }
}

export async function recoverTabGroupState() {
  try {
    const groups = await chrome.tabGroups.query({ title: "AGY" });
    if (groups.length > 0) {
      state.tabGroupId = groups[0].id;
      const tabs = await chrome.tabs.query({ groupId: state.tabGroupId });
      state.tabGroupTabs = new Set(tabs.map((t) => t.id));
    }
  } catch {
    // Not critical — will be set on first tabs_context_mcp call
  }
}
