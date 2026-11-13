// Audio-slice intake, transcription + retranscription, split out of
// offscreen.js — pure refactor, behavior unchanged.
import { transcribe, validateOpenAiKey } from "./transcribe.js";
import { ensureDb, getAll, getRow, putRecord } from "./offscreen-db.js";
import { writeSessionRecord } from "./offscreen-save.js";
import { rec, session } from "./offscreen.js";

export function audioName(index) {
  return `audio/${String(index).padStart(3, "0")}.webm`;
}

// Hand a slice of one segment's bytes to the SW as base64, so it can be
// written to disk through the native host. Sliced because runtime messages
// are JSON and a whole segment would make an unreasonably large one.
export function audioSlice(msg) {
  const seg = rec.pendingStop && rec.pendingStop.segBlobs.find((x) => x.index === msg.index);
  if (!seg) return Promise.resolve({ ok: false, error: "no such segment" });
  return new Promise((resolve) => {
    const fr = new FileReader();
    fr.onload = () => {
      const s = String(fr.result);
      resolve({ ok: true, b64: s.slice(s.indexOf(",") + 1) });
    };
    fr.onerror = () => resolve({ ok: false, error: String(fr.error) });
    fr.readAsDataURL(seg.blob.slice(msg.start, msg.start + msg.len));
  });
}

// Transcribe every segment, then merge onto the shared clock. Each segment is
// mapped through its OWN epoch anchor, so one failed or slow segment shifts
// nothing around it — a failure is a hole, never a drift.
export async function transcribeRecording() {
  if (!rec.pendingStop) return { ok: false, error: "nothing to transcribe" };
  const { trace, segBlobs, apiKey, recording_id, imageRows } = rec.pendingStop;

  const { status } = await runTranscription(segBlobs, apiKey, trace);

  await writeSessionRecord(rec.pendingStop, status);
  rec.pendingStop = null;
  return {
    ok: true,
    cognitive: trace.cognitive,
    transcript_status: status,
    transcript_segments: trace.transcript_segments,
    summary: buildSummary(trace)
  };
}

// Shared transcription core: run whisper over each segment, map onto the shared
// clock, and fold statuses into the trace. Used at stop (in-memory segBlobs)
// and on retry (segments rebuilt from IndexedDB). Only mutates the passed
// trace — persistence is the caller's job.
async function runTranscription(segBlobs, apiKey, trace) {
  const segStatuses = [];
  let cognitive = [];
  for (const seg of segBlobs) {
    const t0 = seg.startEpoch - trace.started_at;
    try {
      const r = await transcribe(seg.blob, apiKey, { filename: `${seg.index}.webm` });
      cognitive = cognitive.concat(
        segmentsToCognitive(r.segments, seg.startEpoch, trace.started_at)
      );
      segStatuses.push({ index: seg.index, t: t0, status: "ok" });
    } catch (err) {
      segStatuses.push({ index: seg.index, t: t0, status: `failed: ${err.message}` });
    }
  }
  cognitive.sort((a, b) => a.t - b.t || a.end - b.end);

  const failed = segStatuses.filter((x) => x.status !== "ok");
  let status;
  if (!segStatuses.length) status = "failed: no audio was captured";
  else if (!failed.length) status = "ok";
  else if (failed.length === segStatuses.length) status = failed[0].status;
  else
    status = `partial: ${failed.length} of ${segStatuses.length} audio segments failed — ${failed[0].status.replace(/^failed: /, "")}`;

  trace.cognitive = cognitive;
  trace.transcript_status = status;
  trace.transcript_segments = segStatuses;
  return { cognitive, status, segStatuses };
}

// Re-run transcription for a saved recording whose transcript failed at stop.
// The durable segment bytes live in IndexedDB until the next recording starts,
// and the per-segment epoch anchors persisted in the session record map them
// onto the same shared clock. The SW writes the patched trace to disk.
export async function retranscribe(recording_id, apiKey) {
  await ensureDb();
  const row = await getRow("sessions", recording_id);
  if (!row || !row.trace) return { ok: false, error: "no such recording" };
  if (!row.segEpochs || !row.segEpochs.length)
    return { ok: false, error: "recording predates this retry path (missing segment anchors)" };

  // Only this recording's own audio. The store also holds any NEWER recording's
  // bytes until that one starts recording clears it, so without the filter a
  // retranscribe of an older recording would transcribe the wrong audio and
  // overwrite the older recording's trace.json with a mismatched transcript.
  // (A pre-fix target row has no recording_id and is filtered out — safe failure,
  // and such recordings are already rejected by the segEpochs guard above.)
  const audioRows = (await getAll("audio")).filter((r) => r.recording_id === recording_id);
  const bySeg = new Map();
  for (const r of audioRows) {
    const k = r.seg ?? 0;
    if (!bySeg.has(k)) bySeg.set(k, []);
    bySeg.get(k).push(r.bytes);
  }
  const segBlobs = row.segEpochs
    .map((e) => ({
      index: e.index,
      startEpoch: e.startEpoch,
      blob: new Blob(bySeg.get(e.index) || [], { type: "audio/webm" })
    }))
    .filter((seg) => seg.blob.size > 0);
  if (!segBlobs.length)
    return { ok: false, error: "no audio segments remain (a newer recording cleared them)" };

  const trace = row.trace;
  const { status } = await runTranscription(segBlobs, apiKey, trace);
  row.trace = trace;
  row.transcriptStatus = status;
  row.utterances = (trace.cognitive || []).length;
  await putRecord("sessions", row);
  return {
    ok: true,
    recording_id,
    trace,
    cognitive: trace.cognitive,
    transcript_status: status,
    transcript_segments: trace.transcript_segments,
    summary: buildSummary(trace)
  };
}

// The session record the Options viewer renders (progressive disclosure). The
// full trace (text, small) is kept so the viewer can drill from metadata into
// the tracks and per-action anchors. Written twice: once at stop, once with
// the transcript result — so the list is never missing a saved recording.
