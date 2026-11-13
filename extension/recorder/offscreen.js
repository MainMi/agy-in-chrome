// Offscreen buffer + mic capture + stop pipeline.
//
// Reliability (§3):
//   - behavior events: appended to IndexedDB as they arrive (100%, local).
//   - audio: MediaRecorder timeslice → each chunk appended to IndexedDB
//     (~90%: only the final un-flushed slice is at risk on a crash), then
//     written to disk at stop BEFORE transcription is attempted.
//   - transcript: produced at stop from the saved audio (needs internet;
//     never blocks the bundle, and its failure is reported, never swallowed).
//
// The service worker forwards behavior events here and sends start/stop
// commands. This document owns the durable state so it survives SW eviction.
//
// NEEDS LIVE TESTING (Chrome): mic permission, MediaRecorder, IndexedDB.

import { transcribe, validateOpenAiKey } from "./transcribe.js";
import {
  newTrace,
  segmentsToCognitive,
  cursorToTrack,
  imagesToTrack,
  SCHEMA_VERSION
} from "./schema.js";

const AUDIO_TIMESLICE_MS = 3000; // flush an audio chunk to disk every 3s
const WARMUP_MS = 2500; // hold "ready" until the mic input settles (muffled start)

// Speech, not music: 32kbps mono Opus is transparent to Whisper (which
// resamples to 16kHz anyway) and 4x smaller than Chrome's ~128kbps default.
const AUDIO_BITRATE = 32000;

// Rotate the recorder into a fresh segment every 10 minutes (~2.4MB each).
// This is what makes a recording of ANY length transcribable: each segment is
// a complete, independently-decodable WebM, so it can be uploaded on its own.
// The MediaStream is NEVER touched — only the encoder is recycled — so the mic
// is not released, there is no permission re-prompt, and the operator sees
// nothing. The boundary costs one or two Opus frames (~20-60ms).
const SEGMENT_MS = 10 * 60 * 1000;
let mediaRecorder = null;
let micStream = null;
let segmentTimer = null;
let stopping = false;
export let session = null; // { recording_id, started_at, segments, apiKey, url0 }
// { recording_id, trace, segBlobs } between stop and transcribe — shared with
// offscreen-transcription.js, which clears it once transcription finishes.
export const rec = { pendingStop: null };

// ---- audio segments --------------------------------------------------------
// Start a new encoder over the SAME live MediaStream and stamp its wall-clock
// start. Every segment is anchored to its own epoch, so transcript timestamps
// are mapped independently and boundary loss can never accumulate into drift.
function startSegment() {
  const index = session.segments.length;
  session.segments.push({ index, startEpoch: Date.now() });
  const mr = new MediaRecorder(micStream, {
    mimeType: "audio/webm",
    audioBitsPerSecond: AUDIO_BITRATE
  });
  mr.ondataavailable = async (e) => {
    if (e.data && e.data.size) {
      const buf = await e.data.arrayBuffer();
      // Tag the row with the recording it belongs to. The audio store is only
      // cleared when the NEXT recording starts, so without this tag a retranscribe
      // of an older recording would map its segEpochs onto a newer recording's
      // bytes and silently overwrite the older trace.json with the wrong transcript.
      await put("audio", { recording_id: session.recording_id, seg: index, bytes: buf, at: Date.now() });
    }
  };
  mr.start(AUDIO_TIMESLICE_MS);
  mediaRecorder = mr;
}

function rotateSegment() {
  const mr = mediaRecorder;
  if (!mr || mr.state === "inactive" || stopping || !session) return;
  // Chain the successor off onstop so the gap is one task, not one timer tick.
  mr.onstop = () => {
    if (!stopping && session) startSegment();
  };
  mr.stop();
}

// ---- lifecycle -------------------------------------------------------------
async function startRecording(cmd) {
  // NEVER clobber a recording in progress. If the service worker lost track of
  // us (MV3 eviction wiped its globals) and asks to start again, refuse and
  // report the live session so the SW can adopt it instead. Without this
  // guard, the clearStore calls below silently destroyed in-flight demos.
  if (session) {
    return {
      ok: false,
      already: true,
      session: { recording_id: session.recording_id, started_at: session.started_at }
    };
  }
  await ensureDb();
  await clearStore("events");
  await clearStore("audio");
  await clearStore("cursor");
  await clearStore("images");
  stopping = false;
  rec.pendingStop = null;
  session = {
    recording_id: cmd.recording_id,
    started_at: cmd.started_at, // epoch ms — shared clock zero
    segments: [],
    apiKey: cmd.apiKey,
    url0: cmd.url0 || null
  };

  // Mic → MediaRecorder → audio chunks to IndexedDB.
  // An offscreen document CANNOT show a permission prompt, so the mic grant
  // must already exist (granted via the Options page). If it doesn't, fail
  // with a clear message the service worker surfaces to the operator.
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    session = null;
    const msg =
      e && e.name === "NotAllowedError"
        ? "Microphone permission not granted. Open the extension Options and click Enable microphone."
        : `Microphone error: ${e && e.message}`;
    return { ok: false, error: msg };
  }
  startSegment();
  segmentTimer = setInterval(rotateSegment, SEGMENT_MS);
  // Warm-up: the first couple of seconds of mic audio are often muffled while
  // the input settles. Hold the "ready" reply until then, and set the trace
  // zero to the post-warm-up moment, so the operator isn't cued to talk early
  // and the clock starts on clean audio. (The SW shows REC only after this
  // reply, and behavior capture starts then too, so no events land in warm-up.)
  await new Promise((r) => setTimeout(r, WARMUP_MS));
  session.started_at = Date.now();
  return { ok: true };
}

async function addEvent(evt) {
  if (!session) return;
  // Convert epoch to ms-since-start (the shared clock) at ingest.
  const e = { ...evt };
  delete e.__ocic;
  e.t = evt.t - session.started_at;
  await put("events", e);
}

// Raw cursor points arrive in batches; stored as-is (epoch t), converted to
// the shared clock at stop.
async function addCursor(points) {
  if (!session || !points || !points.length) return;
  await put("cursor", { points });
}

// Downscale a captured frame to 240p JPEG (small enough to keep in IndexedDB
// for the viewer). Runs here because the offscreen document has canvas + Image;
// the service worker does not. Returns { dataUrl, w, h }.
function resize240(dataUrl) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const h = 240;
      const w = Math.max(1, Math.round(img.width * (h / img.height)));
      const c = document.createElement("canvas");
      c.width = w;
      c.height = h;
      c.getContext("2d").drawImage(img, 0, 0, w, h);
      resolve({ dataUrl: c.toDataURL("image/jpeg", 0.6), w, h });
    };
    img.onerror = () => resolve({ dataUrl, w: 0, h: 0 });
    img.src = dataUrl;
  });
}

// A captured frame: resize, store (blob-as-dataURL + ref + t) for the viewer,
// and return the resized dataURL so the SW can write the file to disk.
async function addImage(msg) {
  if (!session) return { ok: false };
  const { dataUrl, w, h } = await resize240(msg.dataUrl);
  await put("images", { t: msg.t, ref: msg.ref, dataUrl, w, h, vw: msg.vw, vh: msg.vh });
  return { ok: true, dataUrl, w, h };
}

// Stop capture and assemble the tracks. Transcription deliberately does NOT
// happen here: the SW writes the audio to disk between this call and
// `transcribe`, so the narration source is durable before anything that can
// fail over the network is attempted.
async function stopRecording() {
  if (!session) return { ok: false, error: "no active session" };
  const s = session;
  stopping = true;
  if (segmentTimer) {
    clearInterval(segmentTimer);
    segmentTimer = null;
  }

  // Flush + stop the current segment.
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    await new Promise((resolve) => {
      mediaRecorder.onstop = resolve;
      mediaRecorder.stop();
    });
  }
  if (micStream) micStream.getTracks().forEach((t) => t.stop());

  // Reassemble one Blob per segment (Tier: ~90% — everything flushed is here).
  const audioRows = await getAll("audio");
  const bySeg = new Map();
  for (const r of audioRows) {
    const k = r.seg ?? 0;
    if (!bySeg.has(k)) bySeg.set(k, []);
    bySeg.get(k).push(r.bytes);
  }
  const segBlobs = s.segments
    .map((seg) => ({
      ...seg,
      blob: new Blob(bySeg.get(seg.index) || [], { type: "audio/webm" })
    }))
    .filter((seg) => seg.blob.size > 0);

  // Track A from the durable event log (Tier: 100%).
  const eventRows = await getAll("events");
  const trace = newTrace(s.started_at, { recording_id: s.recording_id, url0: s.url0 });
  trace.behavior = eventRows.sort((a, b) => a.t - b.t);
  // Track C: the raw cursor trajectory, flattened from batches, on the clock.
  const cursorRows = await getAll("cursor");
  trace.cursor = cursorToTrack(cursorRows.flatMap((r) => r.points || []), s.started_at);
  // Track D: frame references into images/ (the files are already on disk).
  const imageRows = await getAll("images");
  trace.images = imagesToTrack(imageRows, s.started_at);
  trace.ended_at = Date.now();
  trace.transcript_status = "pending";

  rec.pendingStop = {
    recording_id: s.recording_id,
    apiKey: s.apiKey,
    trace,
    segBlobs,
    imageRows
  };
  session = null;

  // Write the session record NOW, before transcription. If transcription
  // never runs (SW evicted, browser closed), the viewer still shows the
  // session — saying plainly that the transcript never completed, rather
  // than the session vanishing from the list.
  await writeSessionRecord(rec.pendingStop, "pending: transcription did not finish");

  return {
    ok: true,
    bundle: {
      recording_id: s.recording_id,
      schema: SCHEMA_VERSION,
      trace,
      // metadata only — Blobs do not survive runtime messaging, so the SW
      // pulls the bytes back with `audio_slice` below.
      audioSegments: segBlobs.map((x) => ({
        index: x.index,
        size: x.blob.size,
        name: audioName(x.index)
      }))
    }
  };
}

import { ensureDb, patchSession } from "./offscreen-db.js";
import { audioSlice, transcribeRecording, retranscribe } from "./offscreen-transcription.js";
import { copyText, writeSessionRecord } from "./offscreen-save.js";
import { audioName } from "./offscreen-transcription.js";


// ---- message bridge with the service worker -------------------------------
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || msg.__ocic_offscreen !== true) return;
  (async () => {
    try {
      if (msg.cmd === "probe_key") sendResponse(await validateOpenAiKey(msg.apiKey));
      else if (msg.cmd === "start") sendResponse(await startRecording(msg));
      else if (msg.cmd === "event") sendResponse(await addEvent(msg.event));
      else if (msg.cmd === "cursor") sendResponse(await addCursor(msg.points));
      else if (msg.cmd === "image") sendResponse(await addImage(msg));
      else if (msg.cmd === "stop") sendResponse(await stopRecording());
      else if (msg.cmd === "audio_slice") sendResponse(await audioSlice(msg));
      else if (msg.cmd === "transcribe") sendResponse(await transcribeRecording());
      else if (msg.cmd === "retranscribe") sendResponse(await retranscribe(msg.recording_id, msg.apiKey));
      else if (msg.cmd === "copy") sendResponse(copyText(msg.text));
      else if (msg.cmd === "set_path") {
        await ensureDb();
        await patchSession(msg.recording_id, { path: msg.path });
        sendResponse({ ok: true });
      } else sendResponse({ ok: false, error: "unknown cmd" });
    } catch (e) {
      sendResponse({ ok: false, error: String(e && e.message) });
    }
  })();
  return true; // async response
});

