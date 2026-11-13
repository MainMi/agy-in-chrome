// Split out of extension/background.js — pure refactor, behavior unchanged.
import { recorder } from "./rec-state.js";
import { state } from "./state.js";

const AUDIO_SLICE_BYTES = 768 * 1024; // ~1MB once base64-encoded
export async function saveAudioToDisk(bundle) {
  if (!state.nativePort || !bundle.audioSegments) return;
  for (const seg of bundle.audioSegments) {
    for (let start = 0; start < seg.size; start += AUDIO_SLICE_BYTES) {
      const r = await chrome.runtime.sendMessage({
        __ocic_offscreen: true,
        cmd: "audio_slice",
        index: seg.index,
        start,
        len: AUDIO_SLICE_BYTES
      });
      if (!r || !r.ok) throw new Error((r && r.error) || "audio slice failed");
      state.nativePort.postMessage({
        type: "save_audio",
        recording_id: bundle.recording_id,
        name: seg.name,
        b64: r.b64,
        append: start > 0
      });
    }
  }
}

// Disk write goes through the NATIVE HOST (a Node process with fs), not
// chrome.downloads — the browser download path pops an OS "save as" dialog on
// some setups even with saveAs:false, and this writes to a stable location
// (~/.config/open-claude-in-chrome/recordings/<id>/) the agent can open.
// trace.json is small text; the audio goes through save_audio (above) into
// audio/. Returns the absolute directory, or null if the host isn't reachable.
export async function saveBundleToDisk(bundle) {
  if (!state.nativePort) return null;
  const schemaMd = await getSchemaMd();
  const done = new Promise((resolve) => {
    recorder.pendingSaves.set(String(bundle.recording_id), resolve);
    setTimeout(() => {
      if (recorder.pendingSaves.delete(String(bundle.recording_id))) resolve(null);
    }, 8000);
  });
  try {
    state.nativePort.postMessage({
      type: "save_recording",
      recording_id: bundle.recording_id,
      schema: bundle.schema || "v0",
      schema_md: schemaMd,
      trace: bundle.trace
    });
  } catch {
    recorder.pendingSaves.delete(String(bundle.recording_id));
    return null;
  }
  return await done;
}

// The versioned schema descriptor, shipped into each bundle so the agent knows
// how to read the trace. Read once from the packaged file, then cached.
let _schemaMd = null;
async function getSchemaMd() {
  if (_schemaMd != null) return _schemaMd;
  try {
    const res = await fetch(chrome.runtime.getURL("recorder/SCHEMA_v0.md"));
    _schemaMd = await res.text();
  } catch {
    _schemaMd = "";
  }
  return _schemaMd;
}

// Fire recording_complete upstream (→ native host → TCP → MCP server → channel
// notification). Then wait briefly for AGY's recording_ack to know delivery
// (§4). The native-host heartbeat tells us if any session is connected at all.
export async function notifyAgent(bundle, path) {
  if (!state.nativePort) return "no_session"; // native host not connected
  try {
    state.nativePort.postMessage({
      type: "recording_complete",
      recording_id: bundle.recording_id,
      path: path || "",
      schema: bundle.schema,
      summary: bundle.summary,
      transcript_status: bundle.transcriptStatus || "ok"
    });
  } catch {
    return "no_session";
  }
  // Await ack up to ~12s.
  const acked = await waitForAck(bundle.recording_id, 12000);
  return acked ? "delivered" : "sent_unconfirmed";
}

function waitForAck(recordingId, timeoutMs) {
  if (recorder.deliveredIds.has(recordingId)) return Promise.resolve(true);
  return new Promise((resolve) => {
    const start = Date.now();
    const iv = setInterval(() => {
      if (recorder.deliveredIds.has(recordingId)) {
        clearInterval(iv);
        resolve(true);
      } else if (Date.now() - start > timeoutMs) {
        clearInterval(iv);
        resolve(false);
      }
    }, 250);
  });
}


export async function activeTabUrl() {
  try {
    const [t] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    return t?.url || null;
  } catch {
    return null;
  }
}

// The icon is a start/stop toggle (§9 — non-negotiable). Hydrate first: after
// an SW eviction the in-memory flag is a lie, and acting on it destroys the
