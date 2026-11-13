// Split out of extension/background.js — pure refactor, behavior unchanged.
import { CONFIG_SCHEMA, configHydrated, configState, effectiveConfig, writeConfig } from "./config.js";
import { human, humanSession, humanSessionSeed } from "./human.js";
import { isInGroup } from "./tabgroup.js";

export const handlersConfig = {
  async get_config(args) {
    await configHydrated;
    const tabId = args?.tabId;
    const payload = {
      default: configState.default,
      perTab: configState.byTab,
      recognizedKeys: CONFIG_SCHEMA,
      // The persona currently in use, so a comparison can record it and show
      // the hand really was held constant rather than assuming it.
      activeHand: humanSession
        ? {
            seed: humanSessionSeed,
            speed: +humanSession.persona.speed.toFixed(3),
            steadiness: +humanSession.persona.steadiness.toFixed(3),
            overshoot: +humanSession.persona.overshoot.toFixed(3),
            typeTempo: +humanSession.persona.typeTempo.toFixed(3)
          }
        : null
    };
    if (tabId !== undefined && tabId !== null) {
      payload.effectiveForTab = { tabId, config: effectiveConfig(tabId) };
    }
    return { content: [{ type: "text", text: JSON.stringify(payload, null, 2) }] };
  },

  async set_config(args) {
    const { key, value, tabId } = args || {};
    if (!key || typeof key !== "string") {
      return { content: [{ type: "text", text: "set_config requires 'key' (a string)." }] };
    }
    const effective = await writeConfig(key, value === undefined ? null : value, tabId);
    const scope =
      tabId === undefined || tabId === null ? "default (all tabs)" : `tab ${tabId}`;
    const known = Object.prototype.hasOwnProperty.call(CONFIG_SCHEMA, key)
      ? ""
      : ` Note: "${key}" is not a recognized setting, so nothing reads it — it was stored anyway.`;

    // Build the humanization hand NOW rather than lazily on the first action.
    // Otherwise pinning a seed stores a number and changes nothing observable
    // until something is clicked, so there is no way to check what you pinned
    // before relying on it — and get_config would report activeHand: null.
    // Priming here makes the hand inspectable the moment it is configured, and
    // lets this call report exactly what it built.
    let handNote = "";
    if (key === "humanize_seed" || key === "humanize" || key === "humanize_speed") {
      const s = human(effective.humanize_speed, effective.humanize_seed);
      handNote =
        `\nActive hand (seed ${humanSessionSeed === null ? "random" : humanSessionSeed}): ` +
        JSON.stringify({
          speed: +s.persona.speed.toFixed(3),
          steadiness: +s.persona.steadiness.toFixed(3),
          overshoot: +s.persona.overshoot.toFixed(3),
          typeTempo: +s.persona.typeTempo.toFixed(3)
        });
    }
    return {
      content: [
        {
          type: "text",
          text:
            `Set ${key}=${JSON.stringify(value === undefined ? null : value)} for ${scope}.${known}\n` +
            `Effective config${tabId != null ? ` for tab ${tabId}` : ""}: ${JSON.stringify(effective)}` +
            handNote
        }
      ]
    };
  },

  // Deliberate, opt-in attention. Nothing else in this extension selects a tab
  // or raises a window: automation drives background tabs, so the operator is
  // never yanked around as a side effect. This tool is the ONE way to surface
  // a tab, and it is the agent's judgement call when that is worth doing.
  async set_tab_focus(args) {
    const { tabId, focus_window = false } = args;
    if (!(await isInGroup(tabId))) {
      return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };
    }
    try {
      await chrome.tabs.update(tabId, { active: true });
    } catch (e) {
      return { content: [{ type: "text", text: `Could not select tab ${tabId}: ${e.message}` }] };
    }
    let note = "";
    if (focus_window) {
      try {
        const tab = await chrome.tabs.get(tabId);
        // focused:true raises the browser above every other application —
        // this is the part that interrupts the operator.
        await chrome.windows.update(tab.windowId, { focused: true });
        note = " and brought its window to the front";
      } catch (e) {
        note = ` (could not raise its window: ${e.message})`;
      }
    }
    return {
      content: [
        {
          type: "text",
          text: `Tab ${tabId} is now the active tab in its window${note}.`
        }
      ]
    };
  },
};
