// Split out of extension/background.js — pure refactor, behavior unchanged.
import * as audit from "../audit/index.js";
import { cdp, ensureAttached } from "./cdp.js";
import { dispatchMouse, sendMouseEvent } from "./mouse.js";
import { cursorByTab } from "./state.js";
import { sleep } from "./util.js";

// --- Humanization config + plan execution -----------------------------------
//
// The behavioural modelling lives in extension/humanize/ (pure, no browser
// APIs). Everything below is the thin seam: read the flag, walk a plan, map
// each primitive step onto the CDP call the non-humanized path already uses.

const CONFIG_KEY = "ocic_config_v1";       // { default: {...} } in local
export const TAB_CONFIG_KEY = "ocic_tab_config_v1"; // { [tabId]: {...} } in session

// Recognized settings, and what they do when true. `get_config` reports this
// catalog, so adding a setting later means adding one entry here and reading
// effectiveConfig(tabId).<key> where it applies — set_config never changes.
export const CONFIG_SCHEMA = {
  humanize:
    "Drive mouse and keyboard the way a person would: curved cursor paths with " +
    "acceleration and overshoot, clicks that land off-centre inside the target " +
    "with a real press dwell, scrolls decomposed into momentum ticks, and typing " +
    "with per-character keydown/keyup and human inter-key timing. Outcomes are " +
    "identical (same element, same text, same scroll position) — only the motion " +
    "and timing change, so actions take noticeably longer. Default false.",
  humanize_speed:
    "How much time humanized motion is allowed to take, fastest to slowest: " +
    "\"fastest\", \"fast\" (default), \"natural\", \"relaxed\". Higher tiers " +
    "spend more time and draw cursor paths with more samples. \"natural\" is " +
    "genuine human cadence; \"fastest\" keeps the shape of human motion but " +
    "compresses it, for when there is a lot to get through. Every tier keeps " +
    "movement before the click, real key events and identical outcomes — faster " +
    "tiers use fewer path samples and shorter pauses, never none. Only applies " +
    "while humanize is true.",
  audit_mode:
    "Passively record what this agent does in the browser, so a person can watch " +
    "it back. \"off\" (default) records nothing and costs nothing. \"audit\" " +
    "starts an rrweb DOM recording in each tab the first time an action touches " +
    "it, and stitches those into one timeline per AGY session, viewable " +
    "under Audits on the extension's options page. Recording runs in the " +
    "extension's isolated world, so the page cannot observe it, and captures DOM " +
    "rather than pixels — video and canvas content are not captured. This is a " +
    "mode rather than a flag because a future \"teach\" mode wants the opposite " +
    "masking defaults."
};

const AUDIT_MODES = ["off", "audit"];
export let configState = {
  default: { humanize: false, humanize_speed: "fast", humanize_seed: null, audit_mode: "off" },
  byTab: {}
};
export let configHydrated = null;

async function hydrateConfig() {
  try {
    const local = await chrome.storage.local.get(CONFIG_KEY);
    const session = await chrome.storage.session.get(TAB_CONFIG_KEY);
    configState = {
      default: {
        humanize: false, humanize_speed: "fast", humanize_seed: null, audit_mode: "off",
        ...(local[CONFIG_KEY] || {})
      },
      byTab: session[TAB_CONFIG_KEY] || {}
    };
  } catch {}
  return configState;
}
// MV3 evicts this worker, so re-hydrate at every start and keep the cache live.
configHydrated = hydrateConfig().then((c) => {
  audit.setEnabled(c.default.audit_mode === "audit");
  return c;
});
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes[CONFIG_KEY]) {
    configState.default = { humanize: false, audit_mode: "off", ...(changes[CONFIG_KEY].newValue || {}) };
    audit.setEnabled(configState.default.audit_mode === "audit");
  }
  if (area === "session" && changes[TAB_CONFIG_KEY]) {
    configState.byTab = changes[TAB_CONFIG_KEY].newValue || {};
  }
});

/** Per-tab overrides win over the default. */
export function effectiveConfig(tabId) {
  return { ...configState.default, ...(configState.byTab[String(tabId)] || {}) };
}

export async function humanizeOn(tabId) {
  await configHydrated;
  return !!effectiveConfig(tabId).humanize;
}

export async function writeConfig(key, value, tabId) {
  await configHydrated;
  if (tabId === undefined || tabId === null) {
    const next = { ...configState.default };
    if (value === null) delete next[key];
    else next[key] = value;
    configState.default = next;
    await chrome.storage.local.set({ [CONFIG_KEY]: next });
    return next;
  }
  const id = String(tabId);
  const byTab = { ...configState.byTab };
  const forTab = { ...(byTab[id] || {}) };
  if (value === null) delete forTab[key];
  else forTab[key] = value;
  if (Object.keys(forTab).length) byTab[id] = forTab;
  else delete byTab[id];
  configState.byTab = byTab;
  // Per-tab overrides live in session storage: tab ids are session-scoped, so
  // persisting them past a browser restart would attach settings to unrelated
  // future tabs.
  await chrome.storage.session.set({ [TAB_CONFIG_KEY]: byTab });
  return effectiveConfig(tabId);
}

/**
 * Execute a humanize plan. The ONLY place plans meet the browser: each step is
 * dispatched through the same CDP calls the non-humanized path uses, so a
 * humanized action cannot do anything a normal one could not.
 */
export async function dispatchPlan(tabId, plan, modifiers = 0) {
  await ensureAttached(tabId);
  for (const step of plan) {
    switch (step.k) {
      case "sleep":
        await sleep(step.ms);
        break;
      case "move":
        // awaitAck:false is load-bearing here. A humanized path dispatches
        // dozens of mouseMoved events, and on some Chromium builds each one
        // can sit ~5s waiting for a debugger ack — 26 moves then blow past the
        // 60s tool timeout (observed). The plan already carries its own timing
        // in the sleep steps, and moves apply without their ack, so nothing is
        // lost by not waiting. Press/release still await (they are dropped if
        // issued while an earlier command is un-acked).
        await dispatchMouse(tabId, "mouseMoved", step.x, step.y, { modifiers, noAck: true });
        cursorByTab.set(tabId, { x: step.x, y: step.y });
        break;
      case "down":
        await dispatchMouse(tabId, "mousePressed", step.x, step.y, {
          button: step.button, clickCount: step.clickCount, modifiers
        });
        break;
      case "up":
        await dispatchMouse(tabId, "mouseReleased", step.x, step.y, {
          button: step.button, clickCount: step.clickCount, modifiers
        });
        cursorByTab.set(tabId, { x: step.x, y: step.y });
        break;
      case "wheel":
        await sendMouseEvent(
          tabId,
          { type: "mouseWheel", x: step.x, y: step.y, deltaX: step.dx, deltaY: step.dy, modifiers },
          { noAck: true }
        );
        break;
      case "kdown":
        // rawKeyDown is the NON-text-producing variant: it gives the page a
        // keydown event without the renderer inserting a character. All text
        // comes from the "text" step below, exactly once.
        await cdp(tabId, "Input.dispatchKeyEvent", {
          type: "rawKeyDown",
          key: step.key,
          code: step.code,
          windowsVirtualKeyCode: step.keyCode || 0,
          modifiers: step.mods || 0,
          autoRepeat: !!step.autoRepeat
        });
        break;
      case "kup":
        await cdp(tabId, "Input.dispatchKeyEvent", {
          type: "keyUp",
          key: step.key,
          code: step.code,
          windowsVirtualKeyCode: step.keyCode || 0,
          modifiers: step.mods || 0
        });
        break;
      case "text":
        await cdp(tabId, "Input.insertText", { text: step.text });
        break;
    }
  }
}
