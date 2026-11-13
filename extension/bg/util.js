// Split out of extension/background.js — pure refactor, behavior unchanged.

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
