// Split out of extension/background.js — pure refactor, behavior unchanged.
import { activeTabUrl, notifyAgent, saveAudioToDisk, saveBundleToDisk } from "./rec-save.js";
import { persistRecorderState, recorder, recorderReady } from "./rec-state.js";
import { broadcastRecordingState, buildRecordingReference, copyToClipboard, ensureOffscreen, getApiKey, newRecordingId, setBadge, setProcessingBadge, showResultBadge, validateKey } from "./rec-util.js";
import { state } from "./state.js";
import { sleep } from "./util.js";

async function startRecording() {
  // New transition: stale writers from any previous stop are dead from here.
  recorder.epoch++;
  if (state.resultClearTimer) {
    clearTimeout(state.resultClearTimer);
    state.resultClearTimer = null;
  }
  // Boot feedback at the INSTANT of the click — before the key validation
  // network call — so the icon never looks dead after a press.
  setProcessingBadge("Starting… validating key and warming up the microphone");
  const apiKey = await getApiKey();
  const v = await validateKey(apiKey);
  if (!v.ok) {
    // Surface via badge + a notification-free options nudge.
    chrome.action.setTitle({ title: `Cannot record: ${v.error}` });
    setBadge(false);
    return { ok: false, error: v.error };
  }
  await ensureOffscreen();
  recorder.recordingId = newRecordingId();
  recorder.startedAt = Date.now();
  recorder.imgSeq = 0;
  recorder.lastCapture = 0;
  const url0 = await activeTabUrl();
  // Warm-up continues: REC appears only when the offscreen doc reports the
  // mic ready (~2.5s later § muffled start).
  chrome.action.setTitle({ title: "Starting microphone… wait for REC before talking" });
  const startRes = await chrome.runtime.sendMessage({
    __ocic_offscreen: true,
    cmd: "start",
    recording_id: recorder.recordingId,
    started_at: recorder.startedAt,
    apiKey,
    url0
  });
  // Split-brain heal: the offscreen doc already has a live session (we lost
  // track of it, e.g. session-state loss this hydration couldn't cover).
  // ADOPT it — never clobber a recording in progress.
  if (startRes && startRes.already && startRes.session) {
    recorder.active = true;
    recorder.recordingId = startRes.session.recording_id;
    recorder.startedAt = startRes.session.started_at;
    setBadge(true);
    chrome.action.setTitle({ title: "Recording… click to stop" });
    persistRecorderState();
    return { ok: true, adopted: true };
  }
  // If the mic didn't start (permission not granted), fail LOUDLY — voice is
  // core to a recording. Guide the operator to enable it in Options rather
  // than silently capturing behavior with no narration.
  if (!startRes || !startRes.ok) {
    recorder.active = false;
    persistRecorderState();
    setBadge(false);
    const err = (startRes && startRes.error) || "microphone unavailable";
    chrome.action.setTitle({ title: `Can't record: ${err}` });
    chrome.runtime.openOptionsPage();
    return { ok: false, error: err };
  }
  recorder.active = true;
  setBadge(true);
  chrome.action.setTitle({ title: "Recording… click to stop" });
  persistRecorderState();
  await broadcastRecordingState(true);
  return { ok: true };
}

async function stopRecording() {
  const ep = ++recorder.epoch; // stale writers below check this before painting
  const live = () => recorder.epoch === ep;
  const tProc = Date.now();
  recorder.active = false;
  persistRecorderState();
  setProcessingBadge("Processing recording\u2026 (transcribing, saving, copying)");
  await broadcastRecordingState(false);
  const res = await chrome.runtime.sendMessage({
    __ocic_offscreen: true,
    cmd: "stop"
  });
  if (!res || !res.ok) {
    if (live()) chrome.action.setTitle({ title: "Recording failed to save." });
    return { ok: false, error: res && res.error };
  }
  const { bundle } = res;
  // 1) Persist to disk FIRST (reliability), before anything that can fail over
  // the network. The trace lands with transcript_status "pending" so the bundle
  // exists even if the steps below never complete.
  const path = await saveBundleToDisk(bundle).catch((e) => {
    console.error("save failed", e);
    return null;
  });
  if (!path) {
    if (live()) showResultBadge("failed");
    return { ok: false, error: "save failed" };
  }
  // 2) The AUDIO goes to disk next — still before transcription. This is the
  // one artifact that makes a failed transcript recoverable, and it used to
  // live only inside the browser profile where nothing could reach it.
  setProcessingBadge("Processing recording… (saving audio)");
  await saveAudioToDisk(bundle).catch((e) => console.error("audio save failed", e));

  // 3) Transcribe, segment by segment. A failure here is reported, never
  // swallowed: it reaches the trace, the badge, the clipboard and Claude.
  setProcessingBadge("Processing recording… (transcribing)");
  const tr = await chrome.runtime
    .sendMessage({ __ocic_offscreen: true, cmd: "transcribe" })
    .catch((e) => ({ ok: false, error: String(e && e.message) }));
  const transcriptStatus =
    tr && tr.ok ? tr.transcript_status : `failed: ${(tr && tr.error) || "transcription did not run"}`;
  if (tr && tr.ok) {
    bundle.trace.cognitive = tr.cognitive || [];
    bundle.trace.transcript_segments = tr.transcript_segments || [];
    if (tr.summary) bundle.summary = tr.summary;
  }
  bundle.trace.transcript_status = transcriptStatus;
  bundle.transcriptStatus = transcriptStatus;
  // Re-save the trace now that narration (or the reason there is none) is known.
  await saveBundleToDisk(bundle).catch((e) => console.error("re-save failed", e));

  // 4) Copy the reference to the clipboard — the primary, channel-independent
  // feedback. On a transcript failure the text says so, so pasting it into a
  // coding agent surfaces the problem instead of hiding it.
  await copyToClipboard(buildRecordingReference(path, transcriptStatus));
  // Hold the "…" long enough to be SEEN even when the pipeline was instant
  // (no audio -> no transcription): the stages must read consistently.
  const hold = 800 - (Date.now() - tProc);
  if (hold > 0) await sleep(hold);
  if (live()) {
    if (transcriptStatus === "ok") showResultBadge("copied");
    else showResultBadge("no_transcript", transcriptStatus);
  }
  recorder.busy = false; // reference on the clipboard: the icon is live again
  // Record the on-disk path on the session so the Options viewer can copy it too.
  chrome.runtime
    .sendMessage({ __ocic_offscreen: true, cmd: "set_path", recording_id: bundle.recording_id, path })
    .catch(() => {});
  // 3) Notify AGY (best-effort); append delivery to the tooltip when it resolves.
  // Delivery confirmation can arrive up to ~12s later. It must NEVER repaint
  // the badge (a new recording may be underway by then) — tooltip only, and
  // only while this stop is still the latest transition.
  const connectionState = await notifyAgent(bundle, path);
  if (live() && !recorder.active && !recorder.busy) {
    const deliv =
      connectionState === "delivered"
        ? " Also delivered to AGY."
        : connectionState === "sent_unconfirmed"
          ? " Sent to AGY — delivery not confirmed."
          : " No AGY session connected.";
    const head =
      transcriptStatus === "ok"
        ? "Recording saved · reference copied to clipboard — paste it into AGY."
        : `Recording saved WITHOUT narration — ${transcriptStatus}. Reference copied (it says so); audio is on disk in audio/.`;
    chrome.action.setTitle({ title: head + deliv });
  }
  return { ok: true, path, connectionState, transcriptStatus };
}

// Pull each audio segment back out of the offscreen document in slices and
// write it through the native host. Runs BEFORE transcription, so the raw
// narration is durable on disk no matter what the network does afterwards.
// Slices because runtime messages are JSON — a whole segment in one message
// would be needlessly large.
chrome.action.onClicked.addListener(() => {
  recorderReady
    .then(() => {
      // Busy = booting the mic or processing a stop: the click is IGNORED.
      // The toggle is live only when idle, recording, or showing a result.
      if (recorder.busy) return;
      recorder.busy = true;
      const op = recorder.active ? stopRecording() : startRecording();
      return op.finally(() => {
        recorder.busy = false; // safety net; the copied-path clears it earlier
      });
    })
    .catch((e) => console.error("recorder toggle failed", e));
});

// Behavior events from content scripts → offscreen buffer. Tab segmentation.
// Every gate awaits hydration: an event arriving right after SW wake-up must
// still be forwarded to the (still-recording) offscreen buffer.
