// Audit recording: an rrweb stream per tab, stitched into a per-Claude-session
// timeline so you can watch what one agent session actually did.
//
// Deliberately self-contained. It owns its own IndexedDB and its own on-disk
// bundle, touches no recorder state, and background.js reaches it through five
// calls (`setEnabled`, `noteAction`, `onTabRemoved`, `ingest`, `read`). The
// recorder is expected to absorb this eventually; keeping the seam narrow is
// what makes that a merge rather than a rewrite.
//
// THE ONE STRUCTURAL CONSTRAINT: rrweb node ids are integers scoped to a single
// snapshot, so two tabs' event streams can never be concatenated — the ids
// would collide and both replays would corrupt. Streams therefore stay separate
// at the data layer, and a session is an ORDERED LIST OF SEGMENTS that point
// into them. "One recording" is a presentation-layer idea, not a storage one.

import { get, getAll, openDb, put, reqDone, tx } from "./db.js";
import { ensureStream } from "./streams.js";

// --- Policy -----------------------------------------------------------------
//
// A stream lives until its document goes away (tab closed or navigated). That
// is the cheap choice, not the lazy one: re-starting a stream costs a fresh
// full-DOM snapshot — by far the most expensive thing here — while an idle tab
// costs approximately nothing, because rrweb is event-driven and a page nobody
// is touching emits nothing.
//
// So the policy is tuned for the MEDIAN case (a page held open across a few
// minutes of agent work) rather than the worst case (an ad-heavy page mutating
// forever in the background). The two guards below exist only to stop the worst
// case running away, and are set permissively enough that normal work never
// reaches them.
export const IDLE_STOP_MS = 30 * 60 * 1000; // no action against this tab for 30 min
export const MAX_STREAM_BYTES = 40 * 1024 * 1024; // ~40MB of events, then stop appending
const SESSION_IDLE_MS = 30 * 60 * 1000; // a client quiet this long starts a new session


export let enabled = false;

// --- Public: config ---------------------------------------------------------

export function setEnabled(on) {
  enabled = !!on;
}

export function isEnabled() {
  return enabled;
}

// --- Sessions ---------------------------------------------------------------
//
// One session per Claude Code client. The host namespaces every request as
// `h{clientId}_{id}` (native-host.js), and background.js echoes that id back
// untouched, so the client is already identifiable with no protocol change.
// clientId is a counter that resets when the host restarts, so it is paired
// with a start timestamp to stay unique across restarts.

function newSessionId(clientId, t) {
  return `c${clientId}_${t}`;
}

async function currentSession(clientId) {
  const all = await getAll("sessions");
  const mine = all
    .filter((s) => String(s.clientId) === String(clientId))
    .sort((a, b) => b.startedAt - a.startedAt);
  const live = mine[0];
  if (live && Date.now() - live.lastActivityAt < SESSION_IDLE_MS) return live;
  const startedAt = Date.now();
  const fresh = {
    sessionId: newSessionId(clientId, startedAt),
    clientId: String(clientId),
    startedAt,
    lastActivityAt: startedAt,
    actions: []
  };
  await put("sessions", fresh);
  return fresh;
}

/**
 * Record one agent action and make sure its tab is recording.
 *
 * This is the join between the two halves: the action stream gives the timeline
 * its meaning (what the agent did, and when), the rrweb stream gives it pixels.
 */
export async function noteAction({ clientId, tool, action, tabId, detail, postToHost }) {
  if (!enabled || clientId == null) return;
  try {
    let streamId = null;
    if (typeof tabId === "number") streamId = await ensureStream(tabId);

    const session = await currentSession(clientId);
    session.actions.push({
      t: Date.now(),
      tool,
      action: action || null,
      tabId: typeof tabId === "number" ? tabId : null,
      streamId,
      detail: detail ? String(detail).slice(0, 200) : null
    });
    session.lastActivityAt = Date.now();
    await put("sessions", session);
    scheduleCheckpoint(session.sessionId, postToHost);
  } catch {
    // Auditing must never be able to break the action it is auditing.
  }
}

// --- Checkpointing to disk --------------------------------------------------
//
// IndexedDB is what the options page reads, but it is not somewhere a person or
// an agent can look. Checkpointing the session to
// ~/.config/open-claude-in-chrome/audits/<sessionId>/audit.json makes an audit
// inspectable from outside the browser while its tabs are still open, and
// survives the profile being cleared.
//
// Debounced rather than written per action: a checkpoint serialises the whole
// event stream, so doing it on every click would make auditing cost more than
// the work being audited.
const CHECKPOINT_DEBOUNCE_MS = 5000;
const pendingCheckpoints = new Map();

function scheduleCheckpoint(sessionId, postToHost) {
  if (pendingCheckpoints.has(sessionId)) return;
  const timer = setTimeout(() => {
    pendingCheckpoints.delete(sessionId);
    checkpoint(sessionId, postToHost).catch(() => {});
  }, CHECKPOINT_DEBOUNCE_MS);
  pendingCheckpoints.set(sessionId, timer);
}

export async function checkpoint(sessionId, postToHost) {
  if (typeof postToHost !== "function") return null;
  const payload = await readSession(sessionId);
  if (!payload) return null;
  postToHost({ type: "save_audit", session_id: sessionId, payload });
  return sessionId;
}

// --- Read side --------------------------------------------------------------

/**
 * Derive presentation segments: consecutive actions on the same tab collapse
 * into one segment. This is where "tab A, then tab B, then back to tab A"
 * becomes three segments over two streams — the division the viewer scrubs
 * through, without ever merging the underlying event streams.
 */
export function segmentsOf(session) {
  const segs = [];
  for (const a of session.actions || []) {
    if (!a.streamId) continue;
    const last = segs[segs.length - 1];
    if (last && last.streamId === a.streamId) {
      last.tEnd = a.t;
      last.actions.push(a);
    } else {
      segs.push({ streamId: a.streamId, tabId: a.tabId, tStart: a.t, tEnd: a.t, actions: [a] });
    }
  }
  return segs;
}

export async function listSessions() {
  const sessions = await getAll("sessions");
  const streams = await getAll("streams");
  const byId = new Map(streams.map((s) => [s.streamId, s]));
  return sessions
    .sort((a, b) => b.startedAt - a.startedAt)
    .map((s) => {
      const segs = segmentsOf(s);
      // The sequence of sites a session moved through. A page title is a poor
      // identity — several captures of one page all read the same — while the
      // journey is what a reviewer actually recognises a session by.
      const journey = [];
      for (const seg of segs) {
        const st = byId.get(seg.streamId);
        let site = `tab ${seg.tabId}`;
        try {
          if (st && st.url) site = new URL(st.url).host || site;
        } catch {}
        if (journey[journey.length - 1] !== site) journey.push(site);
      }
      return {
        sessionId: s.sessionId,
        clientId: s.clientId,
        startedAt: s.startedAt,
        lastActivityAt: s.lastActivityAt,
        actionCount: (s.actions || []).length,
        segmentCount: segs.length,
        tabs: [...new Set(segs.map((x) => x.tabId))].length,
        journey,
        title: segs.map((x) => byId.get(x.streamId)?.title).find(Boolean) || "(untitled)",
        url: segs.map((x) => byId.get(x.streamId)?.url).find(Boolean) || ""
      };
    });
}

/** Full session payload including events, for the viewer or a disk bundle. */
export async function readSession(sessionId) {
  const session = await get("sessions", sessionId);
  if (!session) return null;
  const segs = segmentsOf(session);
  const streamIds = [...new Set(segs.map((s) => s.streamId))];
  const streams = {};
  for (const sid of streamIds) {
    const meta = await get("streams", sid);
    if (!meta) continue;
    const db = await openDb();
    const t = tx(db, ["chunks"], "readonly");
    const range = IDBKeyRange.bound([sid, -Infinity], [sid, Infinity]);
    const chunks = await reqDone(t.objectStore("chunks").getAll(range));
    chunks.sort((a, b) => a.seq - b.seq);
    streams[sid] = { ...meta, events: chunks.flatMap((c) => c.events) };
  }
  return { session, segments: segs, streams };
}

export async function deleteSession(sessionId) {
  const payload = await readSession(sessionId);
  const db = await openDb();
  if (payload) {
    for (const sid of Object.keys(payload.streams)) {
      const t = tx(db, ["chunks", "streams"], "readwrite");
      const range = IDBKeyRange.bound([sid, -Infinity], [sid, Infinity]);
      await reqDone(t.objectStore("chunks").delete(range));
      await reqDone(t.objectStore("streams").delete(sid));
    }
  }
  const t2 = tx(db, ["sessions"], "readwrite");
  await reqDone(t2.objectStore("sessions").delete(sessionId));
}

