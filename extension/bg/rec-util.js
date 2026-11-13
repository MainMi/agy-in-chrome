// Split out of extension/background.js — pure refactor, behavior unchanged.
import { persistRecorderState, recorder } from "./rec-state.js";
import { state } from "./state.js";

export async function maybeCapture(t) {
  if (!recorder.active || !state.nativePort) return;
  const now = Date.now();
  if (now - recorder.lastCapture < 1000) return;
  recorder.lastCapture = now;
  let dataUrl;
  try {
    dataUrl = await chrome.tabs.captureVisibleTab({ format: "jpeg", quality: 60 });
  } catch {
    return; // not capturable (chrome:// page, no active tab, etc.)
  }
  const name = String(++recorder.imgSeq).padStart(5, "0") + ".jpg";
  persistRecorderState(); // keep frame numbering monotonic across SW evictions
  try {
    const res = await chrome.runtime.sendMessage({
      __ocic_offscreen: true,
      cmd: "image",
      t: t || now,
      ref: "images/" + name,
      vw: recorder.lastVw, // viewport this frame was captured at
      vh: recorder.lastVh,
      dataUrl
    });
    if (res && res.ok && res.dataUrl && state.nativePort) {
      state.nativePort.postMessage({
        type: "save_screenshot",
        recording_id: recorder.recordingId,
        name,
        dataUrl: res.dataUrl
      });
    }
  } catch {}
}

export function newRecordingId() {
  return "rec_" + Math.random().toString(36).slice(2, 10);
}

export async function ensureOffscreen() {
  const has = await chrome.offscreen.hasDocument?.();
  if (has) return;
  await chrome.offscreen.createDocument({
    url: "recorder/offscreen.html",
    reasons: ["USER_MEDIA", "CLIPBOARD"],
    justification:
      "Capture microphone narration, buffer the recording durably, and copy the recording reference to the clipboard on stop."
  });
}

export async function getApiKey() {
  const { openai_api_key } = await chrome.storage.local.get("openai_api_key");
  return openai_api_key || "";
}

// Validate the key BEFORE any recording — a recording with no transcript path
// is a poor outcome, so we fail fast (§5).
//
// This deliberately runs a REAL transcription of a 0.3s clip (in the offscreen
// document, which owns transcribe.js) rather than calling /v1/models. That
// endpoint returns 200 for a key whose credit balance is exhausted, so it once
// green-lit a 43-minute narrated recording that could never be transcribed.
// Authentication is not capability.
export async function validateKey(apiKey) {
  if (!apiKey) return { ok: false, error: "No OpenAI API key set. Add one in the extension options." };
  try {
    await ensureOffscreen();
    const r = await chrome.runtime.sendMessage({
      __ocic_offscreen: true,
      cmd: "probe_key",
      apiKey
    });
    if (r && r.ok) return { ok: true };
    return { ok: false, error: (r && r.error) || "OpenAI transcription is unavailable." };
  } catch (e) {
    return { ok: false, error: `Could not reach OpenAI: ${e.message}` };
  }
}

export function setBadge(on) {
  chrome.action.setBadgeText({ text: on ? "REC" : "" });
  if (on) chrome.action.setBadgeBackgroundColor({ color: "#d23b2e" });
}

// The "..." processing state: shown while the mic boots and while a stopped
// recording is transcribed, saved, and copied. Clicks are ignored throughout.
export function setProcessingBadge(title) {
  chrome.action.setBadgeText({ text: "\u2026" });
  chrome.action.setBadgeBackgroundColor({ color: "#a5701a" });
  chrome.action.setTitle({ title });
}

// A paste-able reference to a saved recording — the same text the Options
// "Copy reference" button produces. Copied to the clipboard on stop so you can
// paste it straight into Claude Code, regardless of any channel.
// `transcriptStatus` is "ok" or a reason. The reference must never claim a
// narration track it doesn't have: the whole point of pasting this into a
// coding agent is that the text describes what is ACTUALLY in the bundle.
export function buildRecordingReference(path, transcriptStatus) {
  const base =
    `Read the browser recording at ${path} — an imitation-learning rollout of an expert doing a task. ` +
    `trace.json holds four tracks on one shared clock (behavior, cursor, images, narration); ` +
    `SCHEMA_v0.md in that folder is the field reference, and images/ holds the frames.`;
  if (!transcriptStatus || transcriptStatus === "ok") return base;
  return (
    base +
    ` WARNING — TRANSCRIPT FAILED: ${transcriptStatus}. The narration track is empty or incomplete, ` +
    `so do NOT read a short/absent cognitive[] as the operator having stayed silent. ` +
    `The raw audio is in audio/ and trace.json records per-segment status in transcript_segments. ` +
    `Please tell me this happened.`
  );
}

export async function copyToClipboard(text) {
  // The service worker has no clipboard; the offscreen document (created with
  // the CLIPBOARD reason) does it via a textarea + execCommand. Awaited so the
  // busy gate releases exactly when the reference is on the clipboard.
  try {
    const r = await chrome.runtime.sendMessage({ __ocic_offscreen: true, cmd: "copy", text });
    return !!(r && r.ok);
  } catch {
    return false;
  }
}

// Post-recording icon — same idea as REC while recording, so you see the
// outcome without hovering (icon AND tooltip). On success the icon is a
// clipboard (📋): the reference was copied to your clipboard. Delivery to
// Claude, if any, is appended to the tooltip. Auto-clears a few seconds after
// the last update; a new recording cancels the clear (see startRecording).
function scheduleBadgeClear() {
  if (state.resultClearTimer) clearTimeout(state.resultClearTimer);
  const ep = recorder.epoch; // this timer belongs to THIS result only
  state.resultClearTimer = setTimeout(() => {
    state.resultClearTimer = null;
    if (recorder.epoch === ep && !recorder.active && !recorder.busy) {
      chrome.action.setBadgeText({ text: "" });
      chrome.action.setTitle({ title: "AGY in Chrome — click to start/stop recording" });
    }
  }, 4000);
}
export function showResultBadge(kind, detail) {
  if (kind === "failed") {
    chrome.action.setBadgeText({ text: "✗" });
    chrome.action.setBadgeBackgroundColor({ color: "#d23b2e" });
    chrome.action.setTitle({
      title: "Could not save the recording — is the native host installed? Run register-host.ps1."
    });
  } else if (kind === "no_transcript") {
    // The recording IS saved — but its narration is missing or partial, which
    // for a teaching rollout is most of the value. It gets its own badge so it
    // can never be mistaken for the clean success state.
    chrome.action.setBadgeText({ text: "⚠" });
    chrome.action.setBadgeBackgroundColor({ color: "#a5701a" });
    chrome.action.setTitle({
      title: `Recording saved WITHOUT narration — ${detail}. Reference copied; the audio is on disk in audio/.`
    });
  } else {
    // "copied" — the reference is on your clipboard. Delivery-to-AGY info
    // arrives later and updates the TOOLTIP only (see stopRecording).
    chrome.action.setBadgeText({ text: "📋" });
    chrome.action.setBadgeBackgroundColor({ color: "#0e8a5f" });
    chrome.action.setTitle({
      title: "Recording saved · reference copied to clipboard — paste it into AGY."
    });
  }
  scheduleBadgeClear();
}

export async function broadcastRecordingState(on) {
  const tabs = await chrome.tabs.query({});
  for (const t of tabs) {
    if (t.id != null)
      chrome.tabs
        .sendMessage(t.id, { __ocic: "recording_state", on })
        .catch(() => {});
  }
}
