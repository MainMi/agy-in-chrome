// Split out of extension/background.js — pure refactor, behavior unchanged.
import * as humanize from "../humanize/index.js";

export let humanSession = null;
export let humanSessionSeed = null; // the seed the live session was built from

/**
 * The humanization "hand" for this browser: one persona (tempo, steadiness,
 * overshoot) reused across actions and tabs, because a person does not become
 * someone else between clicks or when they switch tab.
 *
 * With humanize_seed unset the hand is random per service-worker lifetime,
 * which is what production wants — two sessions should not share a trajectory
 * signature. Pinning the seed rebuilds the session deterministically, so a
 * controlled comparison can hold the hand fixed and vary only the tier.
 */
export function human(speed, seed) {
  const tier = speed || "fast";
  const wantSeed = typeof seed === "number" ? seed : null;
  if (!humanSession || wantSeed !== humanSessionSeed) {
    humanSession = humanize.createSession(wantSeed === null ? undefined : wantSeed, tier);
    humanSessionSeed = wantSeed;
  } else {
    humanize.setSpeed(humanSession, tier);
  }
  return humanSession;
}
