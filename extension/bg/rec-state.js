// Split out of extension/background.js — pure refactor, behavior unchanged.
import { setBadge } from "./rec-util.js";

// ---------------------------------------------------------------------------
// The service worker is a THIN ROUTER only: it toggles recording on the icon,
// owns the offscreen document (the durable buffer that survives SW eviction),
// forwards behavior events from content scripts to it, segments the cross-tab
// timeline, and on stop ships the bundle to disk + notifies Claude Code.
// The heavy state lives in the offscreen doc, never in SW globals.
// ===========================================================================
export const recorder = {
  active: false,
  recordingId: null,
  startedAt: null,
  deliveredIds: new Set(), // recording_ids Claude has acked
  pendingSaves: new Map(), // recording_id -> resolve (native-host disk write)
  imgSeq: 0, // frame counter for the images/ dir
  lastCapture: 0, // ts of last frame, to throttle to ≤1/sec
  lastVw: 0, // last viewport size seen (from content-script events), stamped
  lastVh: 0, // onto each frame so the viewer can map cursor x/y onto it
  // True while booting the mic or processing a stop (transcribe/save/copy).
  // Icon clicks are IGNORED while busy. In-memory on purpose: a dead SW has
  // no in-flight pipeline, so busy must never survive a restart.
  busy: false,
  // Badge epoch: bumped on every start/stop transition. Every DELAYED badge
  // writer (the post-copy delivery update, the 4s result-clear timer) captures
  // the epoch and is discarded if a newer transition happened — a previous
  // recording's stragglers must never repaint the current recording's badge.
  epoch: 0
};

// MV3 evicts this service worker after ~30s idle, which zeroes the globals
// above. Before this guard, a mid-recording eviction made the next icon click
// START a new recording (active had reset to false) whose offscreen "start"
// cleared the buffers — destroying the in-flight demo and shipping a 4-second
// shell instead. The cure: the toggle/forwarding state lives in
// chrome.storage.session (survives SW eviction, dies with the browser), and
// every gate hydrates from it before trusting `recorder`.
const REC_STATE_KEY = "recorder_state_v1";

export function persistRecorderState() {
  chrome.storage.session
    .set({
      [REC_STATE_KEY]: {
        active: recorder.active,
        recordingId: recorder.recordingId,
        startedAt: recorder.startedAt,
        imgSeq: recorder.imgSeq,
        lastVw: recorder.lastVw,
        lastVh: recorder.lastVh
      }
    })
    .catch(() => {});
}

async function hydrateRecorderState() {
  try {
    const { [REC_STATE_KEY]: s } = await chrome.storage.session.get(REC_STATE_KEY);
    if (s && s.active && !recorder.active) {
      recorder.active = true;
      recorder.recordingId = s.recordingId;
      recorder.startedAt = s.startedAt;
      recorder.imgSeq = s.imgSeq || 0;
      recorder.lastVw = s.lastVw || 0;
      recorder.lastVh = s.lastVh || 0;
      setBadge(true); // restore REC after an eviction mid-recording
      chrome.action.setTitle({ title: "Recording… click to stop" });
    }
  } catch {}
}
// Kicked off at every SW (re)start; gates await it before reading `recorder`.
export const recorderReady = hydrateRecorderState();

// Capture a 240p frame anchored to an event, at most once per second. The SW
// grabs the visible tab; the offscreen doc resizes + stores it for the viewer;
// the native host writes the file. The reference goes in the images track. All
// best-effort — a dropped frame just means no file at that ref.
