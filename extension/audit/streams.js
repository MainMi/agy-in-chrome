// rrweb stream lifecycle + event ingest, split out of index.js — pure
// refactor, behavior unchanged.
import { get, getAll, put } from "./db.js";
import { enabled, IDLE_STOP_MS, MAX_STREAM_BYTES } from "./index.js";

function newStreamId(tabId, t) {
  return `s${tabId}_${t}`;
}

/**
 * Make sure the tab is recording, and return its streamId.
 *
 * Resilience matters more than elegance here. The service worker can be evicted
 * mid-session and a page can navigate out from under us, and in both cases the
 * in-memory view is wrong while the tab may or may not still be recording. So
 * the tab itself is the source of truth: ask it. A live recorder answers with
 * the streamId it already owns; anything else means start fresh.
 *
 * A navigation therefore produces a NEW stream rather than a gap in the old
 * one, which is correct — a new document needs its own snapshot, and pretending
 * otherwise would yield a replay that cannot be reconstructed.
 */
export async function ensureStream(tabId, opts = {}) {
  if (!enabled) return null;
  try {
    const pong = await chrome.tabs.sendMessage(tabId, { type: "audit_ping" }).catch(() => null);
    if (pong && pong.streamId) return pong.streamId;
  } catch {
    /* no listener yet — fall through and inject */
  }

  const startedAt = Date.now();
  const streamId = newStreamId(tabId, startedAt);
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["vendor/rrweb.umd.min.js", "audit/inject.js"]
    });
    await chrome.scripting.executeScript({
      target: { tabId },
      func: (sid, o) => window.__ocicAuditStart && window.__ocicAuditStart(sid, o),
      args: [streamId, { maskInputs: !!opts.maskInputs }]
    });
  } catch (e) {
    // Restricted pages (chrome://, the Web Store) refuse injection. That is a
    // fact about the page, not a fault, so it is recorded and not thrown.
    return null;
  }

  let url = "";
  let title = "";
  try {
    const tab = await chrome.tabs.get(tabId);
    url = tab.url || "";
    title = tab.title || "";
  } catch {}

  await put("streams", {
    streamId,
    tabId,
    startedAt,
    endedAt: null,
    url,
    title,
    seqCount: 0,
    bytes: 0,
    events: 0,
    truncated: false,
    lastEventAt: startedAt
  });
  return streamId;
}

/** Append a batch of rrweb events from a tab. */
export async function ingest(msg) {
  if (!msg || !msg.streamId || !Array.isArray(msg.events) || !msg.events.length) return;
  const meta = await get("streams", msg.streamId);
  if (!meta) return; // stream was reaped; drop rather than resurrect a partial
  if (meta.truncated) return;

  const bytes = JSON.stringify(msg.events).length;
  if (meta.bytes + bytes > MAX_STREAM_BYTES) {
    // Stop appending, and SAY SO. A silently truncated replay that just ends is
    // indistinguishable from a session that stopped there.
    meta.truncated = true;
    meta.endedAt = Date.now();
    await put("streams", meta);
    return;
  }

  await put("chunks", { streamId: msg.streamId, seq: msg.seq, events: msg.events });
  meta.seqCount = Math.max(meta.seqCount, msg.seq + 1);
  meta.bytes += bytes;
  meta.events += msg.events.length;
  meta.lastEventAt = Date.now();
  await put("streams", meta);
}

export async function onTabRemoved(tabId) {
  const streams = await getAll("streams");
  const now = Date.now();
  for (const s of streams) {
    if (s.tabId === tabId && !s.endedAt) {
      s.endedAt = now;
      await put("streams", s);
    }
  }
}

/** Permissive reaper: only ever closes streams nothing has touched in ages. */
export async function reapIdle() {
  const now = Date.now();
  const streams = await getAll("streams");
  for (const s of streams) {
    if (s.endedAt) continue;
    if (now - (s.lastEventAt || s.startedAt) > IDLE_STOP_MS) {
      s.endedAt = now;
      s.endedReason = "idle";
      await put("streams", s);
      try {
        await chrome.scripting.executeScript({
          target: { tabId: s.tabId },
          func: () => window.__ocicAuditStop && window.__ocicAuditStop()
        });
      } catch {}
    }
  }
}
