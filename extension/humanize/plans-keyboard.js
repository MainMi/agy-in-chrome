// Keyboard planners split out of index.js — pure refactor, behavior unchanged.
import { typematic, keyHoldMs, interKeyMs, keyDescriptor } from "./keyboard.js";
import { tKey } from "./index.js";

export function planType(s, text) {
  const plan = [];
  let prev = null;
  for (const ch of String(text)) {
    if (prev !== null) plan.push({ k: "sleep", ms: tKey(s, interKeyMs(s.rng, prev, s.persona)) });
    const d = keyDescriptor(ch);
    if (!d) {
      plan.push({ k: "text", text: ch });
      prev = ch;
      continue;
    }
    const mods = d.shift ? 8 : 0;
    plan.push({ k: "kdown", key: ch, code: d.code, keyCode: d.keyCode, mods });
    plan.push({ k: "text", text: ch });
    plan.push({ k: "sleep", ms: Math.min(tKey(s, keyHoldMs(s.rng, s.tm, s.persona)), Math.round(s.tm.initialDelayMs * 0.45)) });
    plan.push({ k: "kup", key: ch, code: d.code, keyCode: d.keyCode, mods });
    prev = ch;
  }
  return plan;
}

/**
 * A single key/chord press with a human hold. `holdMs` opts in to a genuine
 * long hold, in which case the OS typematic sequence is rendered faithfully:
 * initial keydown, the initial delay, then autoRepeat keydowns at the repeat
 * rate. Without it, the hold stays under the threshold and does not repeat.
 */
export function planKey(s, { key, code, keyCode, mods = 0, holdMs = 0 }) {
  const plan = [{ k: "kdown", key, code, keyCode, mods }];
  if (holdMs > s.tm.initialDelayMs) {
    plan.push({ k: "sleep", ms: Math.round(s.tm.initialDelayMs) });
    let elapsed = s.tm.initialDelayMs;
    while (elapsed < holdMs) {
      plan.push({ k: "kdown", key, code, keyCode, mods, autoRepeat: true });
      const step = s.tm.repeatMs * s.rng.uniform(0.85, 1.15);
      plan.push({ k: "sleep", ms: Math.round(step) });
      elapsed += step;
    }
  } else {
    plan.push({ k: "sleep", ms: Math.min(tKey(s, keyHoldMs(s.rng, s.tm, s.persona)), Math.round(s.tm.initialDelayMs * 0.45)) });
  }
  plan.push({ k: "kup", key, code, keyCode, mods });
  return plan;
}
