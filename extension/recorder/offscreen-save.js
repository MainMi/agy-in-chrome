// Session-record persistence + clipboard helper, split out of offscreen.js —
// pure refactor, behavior unchanged.
import { ensureDb, getAll, getRow, putRecord } from "./offscreen-db.js";

export async function writeSessionRecord(p, status) {
  await ensureDb();
  const { trace, segBlobs, imageRows, recording_id } = p;
  await putRecord("sessions", {
    recording_id,
    started_at: trace.started_at,
    ended_at: trace.ended_at,
    url0: trace.url0,
    events: (trace.behavior || []).length,
    utterances: (trace.cognitive || []).length,
    transcriptStatus: status,
    // Per-segment epoch anchors, so a later retry can re-run transcription and
    // map the rebuilt track onto the same shared clock.
    segEpochs: (segBlobs || []).map((x) => ({ index: x.index, startEpoch: x.startEpoch })),
    trace,
    // kept for playback in the viewer; the authoritative copy is on disk
    audio: new Blob(segBlobs.map((x) => x.blob), { type: "audio/webm" }),
    // 240p frames (dataURL) on the shared clock — the viewer can't read the
    // on-disk images/ dir, so it shows these; the agent uses the disk files.
    images: (imageRows || []).map((r) => ({
      t: r.t - trace.started_at,
      ref: r.ref,
      dataUrl: r.dataUrl,
      w: r.w,
      h: r.h,
      vw: r.vw,
      vh: r.vh
    }))
  });
}

export function buildSummary(trace) {
  const dur = Math.round(((trace.ended_at || 0) - trace.started_at) / 1000);
  const tabs = new Set(trace.behavior.map((e) => e.tab)).size;
  const host = (() => {
    try { return new URL(trace.url0).host; } catch { return "a site"; }
  })();
  const utt = (trace.cognitive || []).length;
  const narration =
    trace.transcript_status === "ok"
      ? `${utt} utterance(s)`
      : `NO usable narration (${trace.transcript_status})`;
  return `Recording ready: ${dur}s across ${tabs || 1} tab(s) on ${host}, ${narration}.`;
}

// Copy text to the clipboard on the SW's behalf (the SW has no clipboard).
// Uses the textarea + execCommand pattern, which works in an offscreen
// document created with the CLIPBOARD reason + the clipboardWrite permission.
export function copyText(text) {
  try {
    const ta = document.createElement("textarea");
    ta.value = text || "";
    ta.style.position = "fixed";
    ta.style.top = "-9999px";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return { ok };
  } catch (e) {
    return { ok: false, error: String(e && e.message) };
  }
}
