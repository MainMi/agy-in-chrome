// The Audits pane. Reads the same IndexedDB the service worker writes — the
// options page and the worker share an extension origin, so no messaging is
// needed and an audit stays readable even while the worker is evicted.
//
// The read helpers come from ../audit/index.js rather than being reimplemented
// here, so segment derivation has exactly one definition and the unit tests
// cover the version the UI actually runs.

import { listSessions, readSession, deleteSession } from "../audit/index.js";

export const $ = (id) => document.getElementById(id);
export let cur = { payload: null, segIndex: 0, player: null };

function siteOf(url) {
  try { return new URL(url).host; } catch { return ""; }
}

export function fmtClock(ms) {
  const s = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
function fmtWhen(t) {
  return new Date(t).toLocaleString([], {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit"
  });
}

export async function refreshAudits() {
  const host = $("auditList");
  if (!host) return;
  let sessions = [];
  try {
    sessions = await listSessions();
  } catch (e) {
    host.innerHTML = `<div class="empty">Could not read audits: ${e.message}</div>`;
    return;
  }
  if (!sessions.length) {
    host.innerHTML =
      '<div class="empty">No audits yet. Turn recording on with ' +
      '<code>set_config audit_mode=audit</code>, then drive the browser.</div>';
    $("auditPanel").hidden = true;
    return;
  }
  host.innerHTML = "";
  sessions.forEach((s, i) => {
    const b = document.createElement("button");
    b.className = "sitem";
    b.setAttribute("aria-current", String(i === 0));
    b.innerHTML =
      `<span class="top"><span class="id">session ${s.clientId}</span>` +
      `<span class="when"></span></span>` +
      `<span class="ttl"></span>` +
      `<span class="meta">${s.actionCount} actions · ${s.tabs} tab${s.tabs === 1 ? "" : "s"}</span>`;
    b.querySelector(".when").textContent = fmtWhen(s.startedAt);
    // The journey IS the identity. "client 1" means nothing alone, and every
    // capture of one page shares a title, so the list read "untouched" four
    // times over. The sequence of sites is what a reviewer recognises.
    b.querySelector(".ttl").textContent = s.journey && s.journey.length
      ? s.journey.join(" → ")
      : "(nothing recorded)";
    b.title = s.sessionId;
    b.onclick = () => selectSession(s.sessionId, i);
    host.appendChild(b);
  });
  await selectSession(sessions[0].sessionId, 0);
}

async function selectSession(sessionId, index) {
  [...$("auditList").children].forEach((c, j) =>
    c.setAttribute && c.setAttribute("aria-current", String(index === j))
  );
  cur.payload = await readSession(sessionId);
  $("auditPanel").hidden = !cur.payload;
  if (!cur.payload) return;
  buildTimeline();
}

import { buildTimeline, renderAt, setPlaying, T } from "./audit-timeline.js";

export function wireAuditTabs() {
  const tabA = $("tab-audits");
  const tabR = $("tab-recordings");
  if (!tabA || !tabR) return;
  const show = (audits) => {
    tabA.setAttribute("aria-selected", String(audits));
    tabR.setAttribute("aria-selected", String(!audits));
    $("pane-audits").hidden = !audits;
    $("pane-recordings").hidden = audits;
    if (audits) refreshAudits();
  };
  tabA.onclick = () => show(true);
  tabR.onclick = () => show(false);

  const del = $("auditDelete");
  if (del) {
    del.onclick = async () => {
      if (!cur.payload) return;
      const id = cur.payload.session.sessionId;
      del.disabled = true;
      try {
        await deleteSession(id);
        await refreshAudits();
      } finally {
        del.disabled = false;
      }
    };
  }
  const rf = $("auditRefresh");
  if (rf) rf.onclick = () => refreshAudits();

  const play = $("playBtn");
  if (play) play.onclick = () => setPlaying(!T.playing);
  const scrub = $("scrub");
  if (scrub) scrub.oninput = (e) => { setPlaying(false); T.pinned = null; renderAt(Number(e.target.value)); };
}

