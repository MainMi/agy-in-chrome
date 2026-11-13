// Split out of extension/background.js — pure refactor, behavior unchanged.
import { cdp, ensureAttached } from "./cdp.js";
import { dbg } from "./debuglog.js";
import { screenshotSaves, screenshotStore, state } from "./state.js";

// --- Screenshot helper ---
// Cap viewport to 1280x800 for screenshots to keep size manageable.
// Retina displays produce 2x+ resolution PNGs that blow up base64 size.
const MAX_SCREENSHOT_WIDTH = 1280;
const MAX_SCREENSHOT_HEIGHT = 800;

export async function takeScreenshot(tabId) {
  await ensureAttached(tabId);

  // Capture at EXACTLY CSS-pixel dimensions, because the agent reads click
  // coordinates off this image and clicks are dispatched in CSS pixels. On a
  // 1.5x display an uncorrected capture of a 1008x632 viewport comes back
  // 1512x948, so an agent told to "click what you see" aims 1.5x off and
  // misses everything.
  //
  // The capture is rasterised at the display's pixel ratio, so on a scaled
  // display the image comes back larger than the CSS viewport and every
  // coordinate read off it is wrong by that factor. Undo it in the capture
  // itself: clip to the viewport and scale by 1/ratio, which yields an image
  // whose pixels ARE CSS pixels. Emulation would also achieve this, but at the
  // cost of freezing the viewport (see ensureAttached).
  let clip = null;
  try {
    const vp = await cdp(tabId, "Runtime.evaluate", {
      expression: "JSON.stringify([innerWidth, innerHeight, devicePixelRatio])",
      returnByValue: true
    });
    const [vw, vh, dpr] = JSON.parse(vp.result.value);
    if (vw > 0 && vh > 0) {
      clip = { x: 0, y: 0, width: vw, height: vh, scale: 1 / (dpr > 0 ? dpr : 1) };
    }
  } catch {}

  const shot = async (quality) => {
    const params = { format: "jpeg", quality, optimizeForSpeed: true, captureBeyondViewport: false };
    if (clip) params.clip = clip;
    return (await cdp(tabId, "Page.captureScreenshot", params)).data;
  };

  let base64 = await shot(45);

  // If still too large (>350KB base64 ≈ ~262KB binary), reduce quality further
  if (base64.length > 350000) {
    base64 = await shot(28);
  }

  // The coordinate space this image is in — the single fact that made screenshot
  // bugs invisible for so long. The response reports dimensions; it says nothing
  // about the pixel ratio the capture was rasterised at, the clip scale used to
  // undo it, or whether a quality retry fired. An agent reading coordinates off
  // this image is trusting every one of those.
  dbg(
    "cdp",
    `screenshot ${clip ? `${clip.width}x${clip.height} CSS px, dpr ${Math.round((1 / clip.scale) * 100) / 100}, clip scale ${Math.round(clip.scale * 1000) / 1000}` : "NO CLIP — image is in device pixels, not CSS pixels"}` +
      ` -> ${Math.round((base64.length * 3) / 4 / 1024)}KB${base64.length > 350000 ? " (after quality retry)" : ""}`,
    { tab: tabId }
  );

  const imageId = `screenshot_${Date.now()}`;
  screenshotStore.set(imageId, base64);
  // Keep only last 10 screenshots (less memory pressure)
  const keys = Array.from(screenshotStore.keys());
  while (keys.length > 10) {
    screenshotStore.delete(keys.shift());
  }

  return { base64, imageId };
}

// Write a captured base64 screenshot to disk via the native host and resolve
// with the absolute path. Used when the computer tool's screenshot action is
// called with save_to_disk: true. The native host replies with `screenshot_saved`.
export function writeScreenshotToDisk(base64) {
  if (!state.nativePort) return Promise.reject(new Error("native host not connected"));
  const id = `shot_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
  return new Promise((resolve, reject) => {
    screenshotSaves.set(id, { resolve, reject });
    state.nativePort.postMessage({
      type: "save_screenshot_to_disk",
      id,
      dataUrl: "data:image/jpeg;base64," + base64,
    });
    // Guard against a dead native host so callers never hang forever.
    setTimeout(() => {
      if (screenshotSaves.has(id)) {
        screenshotSaves.delete(id);
        reject(new Error("timed out waiting for native host to save screenshot"));
      }
    }, 5000);
  });
}
