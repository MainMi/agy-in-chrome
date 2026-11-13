// Split out of extension/background.js — pure refactor, behavior unchanged.

export async function detectBrowser() {
  try {
    if (navigator.brave && (await navigator.brave.isBrave?.())) return "Brave";
  } catch (e) {}
  const ua = navigator.userAgent || "";
  if (/Edg\//.test(ua)) return "Edge";
  const brands = (navigator.userAgentData?.brands || []).map((b) => b.brand).join(" ");
  if (/Brave/i.test(brands)) return "Brave";
  if (/OPR\//.test(ua)) return "Opera";
  return "Chrome";
}

// Browser-aware mouse ack strategy. Whether we're on Brave is stable for the
// life of the service worker, so cache the detection at module level and
// resolve it lazily (detectBrowser is async). null = not yet determined.
let IS_BRAVE = null;

export async function isBrave() {
  if (IS_BRAVE === null) {
    IS_BRAVE = (await detectBrowser()) === "Brave";
  }
  return IS_BRAVE;
}
