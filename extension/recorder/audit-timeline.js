// Session timeline + rrweb player, split out of audits.js — pure refactor,
// behavior unchanged.
import { $, cur, fmtClock } from "./audits.js";

// ---------------------------------------------------------------------------
// One timeline across the whole session.
//
// The streams cannot be concatenated — rrweb node ids are per-snapshot — so the
// continuity is built here instead: each segment contributes its own window to
// a single global clock, and playback swaps the underlying player at the
// boundaries. The reviewer presses play once and the tab switches happen on
// their own, which is the entire point of an audit; having to click between
// tabs and reassemble the order by hand is not a replay.
//
// Dead time between segments is compressed out. A wall-clock gap is time the
// agent spent in ANOTHER tab, already shown by that tab's own segment, so
// replaying it as a frozen screen would be showing nothing twice.
const LEAD_IN_MS = 1000;
const LEAD_OUT_MS = 3000;

export let T = { spans: [], total: 0, t: 0, playing: false, timer: null, mounted: -1, pinned: null };

export function buildTimeline() {
  const { segments, streams } = cur.payload;
  T.spans = [];
  let acc = 0;
  segments.forEach((seg, i) => {
    const st = streams[seg.streamId];
    if (!st || !st.events || st.events.length < 2) return;
    const first = st.events[0].timestamp;
    const last = st.events[st.events.length - 1].timestamp;
    const winStart = Math.max(first, seg.tStart - LEAD_IN_MS);
    // Do NOT clamp the window to the stream's last event. rrweb stops emitting
    // the moment a page goes quiet, so the final event can land milliseconds
    // after the last action — clamping there cut the action's aftermath off,
    // and a scroll snapped away to the next tab just as it began. The window
    // runs past the events; the SEEK is clamped instead, so the replay holds
    // its final frame for the remainder.
    const winEnd = Math.max(seg.tEnd + LEAD_OUT_MS, winStart + 1500);
    const dur = Math.max(900, winEnd - winStart);
    T.spans.push({
      segIndex: i, streamId: seg.streamId, tabId: seg.tabId,
      first, last, streamDur: Math.max(0, last - first), winStart, dur, g0: acc,
      site: siteOf(st.url) || `tab ${seg.tabId}`,
      actions: seg.actions
    });
    acc += dur;
  });
  T.total = acc;
  T.t = 0;
  T.mounted = -1;
  $("transport").hidden = T.spans.length === 0;
  $("tTotal").textContent = fmtClock(T.total);
  $("scrub").max = String(Math.max(1, Math.round(T.total)));
  renderTimeline();
  if (T.spans.length) renderAt(0);
  else selectSegment(0);
}

function spanAt(t) {
  for (let i = T.spans.length - 1; i >= 0; i--) if (t >= T.spans[i].g0) return i;
  return 0;
}

export function renderAt(t, { play = false } = {}) {
  if (!T.spans.length) return;
  T.t = Math.max(0, Math.min(t, T.total));
  const i = spanAt(T.t);
  const sp = T.spans[i];
  if (T.mounted !== i) {
    T.mounted = i;
    selectSegment(sp.segIndex, { fromTimeline: true });
  }
  // Clamp into the stream: past its end the player holds the final frame,
  // which is what makes the lead-out above possible.
  seekTo(Math.min(sp.winStart - sp.first + (T.t - sp.g0), sp.streamDur), play);
  $("scrub").value = String(Math.round(T.t));
  $("tNow").textContent = fmtClock(T.t);
  $("nowTab").textContent = sp.site;
  highlight(i);
}

function globalTimeOf(sp, a) {
  return Math.max(sp.g0, Math.min(sp.g0 + sp.dur, sp.g0 + (a.t - sp.winStart)));
}

export function renderTimeline() {
  const host = $("timeline");
  host.innerHTML = "";
  if (!T.spans.length) {
    host.innerHTML = '<span class="empty">Nothing was recorded in this session.</span>';
    return;
  }
  T.spans.forEach((sp, i) => {
    const g = document.createElement("div");
    g.className = "tlgroup";
    g.dataset.span = String(i);
    const head = document.createElement("div");
    head.className = "tlhead";
    head.innerHTML = `<span class="site"></span><span class="tabid">tab ${sp.tabId}</span>`;
    head.querySelector(".site").textContent = sp.site;
    const acts = document.createElement("div");
    acts.className = "tlacts";
    sp.actions.forEach((a) => {
      const gt = globalTimeOf(sp, a);
      const b = document.createElement("button");
      b.className = "act";
      b.dataset.g = String(gt);
      b.innerHTML = `<span class="t">${fmtClock(gt)}</span><span class="tool"></span>`;
      b.querySelector(".tool").textContent = a.action ? `${a.tool}.${a.action}` : a.tool;
      b.title = a.detail || "";
      // Land a beat before the action, so it is seen in context rather than as
      // a jump-cut to its aftermath.
      b.onclick = () => {
        setPlaying(false);
        // Pin the clicked action: the seek lands a beat BEFORE it so the moment
        // is seen in context, and without this the highlight recomputed from
        // that earlier time and lit the previous action instead.
        T.pinned = gt;
        renderAt(Math.max(sp.g0, gt - 1200));
      };
      acts.appendChild(b);
    });
    g.appendChild(head);
    g.appendChild(acts);
    host.appendChild(g);
  });
}

function highlight(spanIndex) {
  const groups = [...$("timeline").querySelectorAll(".tlgroup")];
  groups.forEach((g, j) => g.setAttribute("data-active", String(j === spanIndex)));
  const all = [...$("timeline").querySelectorAll(".act")];
  let active = -1;
  all.forEach((b, j) => { if (Number(b.dataset.g) <= T.t + 250) active = j; });
  // A pinned action wins until the clock actually reaches it, then releases.
  if (T.pinned != null) {
    if (T.t + 250 < T.pinned) {
      const idx = all.findIndex((b) => Number(b.dataset.g) === T.pinned);
      if (idx >= 0) active = idx;
    } else {
      T.pinned = null;
    }
  }
  all.forEach((b, j) => b.setAttribute("aria-current", String(j === active)));
  if (active >= 0 && all[active]) {
    all[active].scrollIntoView({ block: "nearest" });
  }
}


export function setPlaying(on) {
  T.playing = on;
  $("playBtn").innerHTML = on ? "&#10074;&#10074;" : "&#9654;";
  $("playBtn").setAttribute("aria-label", on ? "Pause" : "Play");
  if (T.timer) clearInterval(T.timer);
  T.timer = null;
  if (!on) {
    if (cur.player) { try { cur.player.pause(); } catch {} }
    return;
  }
  if (T.t >= T.total - 50) T.t = 0;
  renderAt(T.t, { play: true });
  // Elapsed comes from the wall clock, not from accumulating a step per tick:
  // Chrome throttles timers in a background tab to about 1Hz, which made a
  // `t += 100` clock run roughly eight times slow and never reach the second
  // tab. Reading the clock makes throttling cost smoothness, never rate.
  const wall0 = Date.now();
  const base = T.t;
  T.timer = setInterval(() => {
    const next = base + (Date.now() - wall0);
    if (next >= T.total) { renderAt(T.total); setPlaying(false); return; }
    const before = spanAt(T.t);
    const after = spanAt(next);
    // Re-seek only at a boundary; in between the player runs on its own clock,
    // so playback stays smooth instead of stuttering every tick.
    if (before !== after) renderAt(next, { play: true });
    else {
      // Refresh the highlight on EVERY tick, not just at a tab boundary. This
      // branch used to update the clock alone, so the active action only moved
      // when the tab changed and stood still through all the actions between.
      T.t = next;
      $("scrub").value = String(Math.round(T.t));
      $("tNow").textContent = fmtClock(T.t);
      highlight(after);
    }
  }, 100);
}

export function selectSegment(i, opts = {}) {
  const { segments, streams } = cur.payload;
  cur.segIndex = i;
  const seg = segments[i];
  if (!seg) return;
  const st = streams[seg.streamId];

  $("segTitle").textContent = (st && st.title) || `Segment ${i + 1}`;
  $("segUrl").textContent = (st && st.url) || "";
  const badge = $("segBadge");
  if (st && st.truncated) {
    badge.hidden = false;
    badge.className = "badge trunc";
    badge.textContent = "truncated — size cap";
  } else if (st && !st.endedAt) {
    badge.hidden = false;
    badge.className = "badge live";
    badge.textContent = "still open";
  } else {
    badge.hidden = true;
  }

  mountPlayer(st, seg);
}

function mountPlayer(stream, seg) {
  const host = $("player");
  host.innerHTML = "";
  cur.player = null;
  if (!stream || !stream.events || stream.events.length < 2) {
    host.innerHTML = '<p class="empty">This segment has too few events to replay.</p>';
    return;
  }
  // The UMD build exposes a module namespace, not the constructor itself.
  const Player = (window.rrwebPlayer && window.rrwebPlayer.default) || window.rrwebPlayer;
  if (typeof Player !== "function") {
    host.innerHTML = '<p class="empty">rrweb-player did not load.</p>';
    return;
  }
  try {
    cur.player = new Player({
      target: host,
      props: {
        events: stream.events,
        width: Math.min(host.clientWidth || 900, 1000),
        height: 420,
        autoPlay: false,
        showController: false
      }
    });
    // Open on the moment the agent first acted here, not the page's birth.
    const t0 = stream.events[0].timestamp;
    seekTo(seg.tStart - t0 - 1000);
  } catch (e) {
    host.innerHTML = `<p class="empty">Player failed: ${e.message}</p>`;
  }
}

export function seekTo(offsetMs, play = false) {
  if (!cur.player) return;
  try {
    cur.player.goto(Math.max(0, offsetMs), play);
  } catch {}
}
