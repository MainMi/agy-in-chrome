// Timeline/track rendering for the sessions viewer, split out of
// options.js — pure refactor, behavior unchanged.
import { esc, trunc, traceCache } from "./options-shared.js";

export function renderTracks(trace, rid, images) {
  if (!trace) return `<div class="empty">Trace not stored for this session.</div>`;
  const beh = (trace.behavior || []).slice().sort((a, b) => a.t - b.t);
  const cog = (trace.cognitive || []).slice().sort((a, b) => a.t - b.t);
  const cur = (trace.cursor || []).slice().sort((a, b) => a.t - b.t);
  if (!beh.length && !cog.length && !cur.length)
    return `<div class="empty">Nothing recorded.</div>`;

  // Total span on the shared clock; fall back to the last timestamp seen.
  const lastT = Math.max(
    trace.ended_at ? trace.ended_at - trace.started_at : 0,
    beh.length ? beh[beh.length - 1].t : 0,
    cog.length ? cog[cog.length - 1].end || cog[cog.length - 1].t : 0,
    cur.length ? cur[cur.length - 1].t : 0,
    1000
  );
  // Track C: segment the cursor points into activity blocks (a gap > 500ms
  // starts a new block), so "cursor active, no behavior" stretches are visible
  // against the narration. Each block is clickable → the actual path on canvas.
  const cseg = [];
  {
    let s = null;
    for (const p of cur) {
      if (!s || p.t - s.end > 500) {
        s = { start: p.t, end: p.t, pts: [p] };
        cseg.push(s);
      } else {
        s.end = p.t;
        s.pts.push(p);
      }
    }
  }
  traceCache.set(rid, { beh, cog, cseg, images: images || [] }); // for the popups

  // ---- one shared, content-aware time axis ---------------------------------
  // Position is NOT proportional to time alone: a second holding fifty events
  // needs fifty events' worth of height, and no clamp may take that away.
  // So y advances with elapsed time, and stretches further whenever the lane
  // an item belongs to is still occupied. Crucially the stretch moves the
  // SHARED y, so all three lanes stay on one axis — nothing is nudged per
  // lane, which is what used to desynchronise them from each other and from
  // the time rail while spilling thousands of pixels out of the container.
  const MK_H = 20; // one behavior mark
  const GAP = 3;
  const PX_PER_MS = 0.003; // 3px per idle second: quiet stretches stay visible
  const CW = 112; // curseg content width (lane minus padding/border)

  const uttLines = (u) => Math.min(4, Math.max(1, Math.ceil((u.text || "").length / 46)));

  const items = [];
  beh.forEach((e, i) => items.push({ t: e.t, lane: 0, h: MK_H, kind: "b", i, e }));
  cseg.forEach((s, i) => {
    const im = nearestImage(images, s.start);
    const framed = !!(im && im.dataUrl && im.vw > 0 && im.vh > 0);
    items.push({
      t: s.start,
      lane: 1,
      h: framed ? Math.max(30, Math.round(CW * (im.vh / im.vw))) : 24,
      kind: "c",
      i,
      s,
      im: framed ? im : null
    });
  });
  cog.forEach((u, i) => {
    const lines = uttLines(u);
    items.push({ t: u.t, lane: 2, h: 10 + lines * 17, kind: "n", i, u, lines });
  });
  items.sort((a, b) => a.t - b.t || a.lane - b.lane);

  const bp = [[0, 0]]; // breakpoints [t, y] of the shared mapping
  const free = [0, 0, 0]; // per-lane occupied-until y
  let yy = 0, prevT = 0;
  for (const it of items) {
    yy += (it.t - prevT) * PX_PER_MS;
    prevT = it.t;
    if (yy < free[it.lane]) yy = free[it.lane];
    it.top = Math.round(yy);
    free[it.lane] = it.top + it.h + GAP;
    const last = bp[bp.length - 1];
    if (it.t === last[0]) last[1] = it.top;
    else bp.push([it.t, it.top]);
  }
  // Height is whatever the content actually needed — no clamp, so nothing
  // can overflow into the raw-JSON block below.
  const H = Math.max(Math.round(Math.max(yy + (lastT - prevT) * PX_PER_MS, ...free)) + 8, 220);
  if (lastT > bp[bp.length - 1][0]) bp.push([lastT, H - 8]);

  // The same mapping, interpolated, for things not anchored to an item.
  const y = (t) => {
    if (t <= bp[0][0]) return bp[0][1];
    if (t >= bp[bp.length - 1][0]) return bp[bp.length - 1][1];
    let lo = 0, hi = bp.length - 1;
    while (lo < hi - 1) {
      const mid = (lo + hi) >> 1;
      if (bp[mid][0] <= t) lo = mid;
      else hi = mid;
    }
    const [t0, y0] = bp[lo], [t1, y1] = bp[hi];
    return Math.round(y0 + ((t - t0) / (t1 - t0 || 1)) * (y1 - y0));
  };

  // Each gesture: the path drawn on the faded frame it happened over, fit to
  // the frame (SVG viewBox = the frame's viewport, so raw x/y land in place).
  // No frame → a solid block. Click opens the full popup.
  const cursorBlocks = items
    .filter((x) => x.kind === "c")
    .map(({ s, i, im, top, h }) => {
      if (im) {
        const pts = s.pts.map((p) => `${p.x},${p.y}`).join(" ");
        const a = s.pts[0], b = s.pts[s.pts.length - 1];
        const r = Math.round(Math.max(im.vw, im.vh) * 0.013);
        return (
          `<div class="curseg" style="top:${top}px;height:${h}px" data-rid="${esc(rid)}" data-cseg="${i}" title="${s.pts.length} points">` +
          `<img class="curseg-frame" src="${im.dataUrl}" alt="">` +
          `<svg class="curseg-path" viewBox="0 0 ${im.vw} ${im.vh}" preserveAspectRatio="none">` +
          `<polyline points="${pts}" fill="none" stroke="rgba(0,0,0,.55)" stroke-width="4" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>` +
          `<polyline points="${pts}" fill="none" stroke="#ffd400" stroke-width="1.8" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>` +
          `<circle cx="${a.x}" cy="${a.y}" r="${r}" fill="#0e8a5f"/>` +
          `<circle cx="${b.x}" cy="${b.y}" r="${r}" fill="#d23b2e"/>` +
          `</svg></div>`
        );
      }
      const dens = Math.min(1, s.pts.length / 24);
      return `<div class="cur" style="top:${top}px;height:${h}px;opacity:${(0.35 + 0.55 * dens).toFixed(2)}" data-rid="${esc(rid)}" data-cseg="${i}" title="${s.pts.length} points"></div>`;
    })
    .join("");

  // Each item carries data-rid/idx so a click resolves it to its full record
  // in the popup. Labels truncate with an explicit … ; the full text is in the
  // popup, so nothing is silently clipped.
  const marks = items
    .filter((x) => x.kind === "b")
    .map(({ e, i, top }) => {
      const name = e.anchor?.name || e.anchor?.selector || "";
      const t = (e.t / 1000).toFixed(1);
      const flags =
        (e.suppressed ? ' <span class="sup">[ovr]</span>' : "") +
        (e.inferred ? ' <span class="inf">[?]</span>' : "");
      const label = `${t}s ${esc(e.action)}${flags} ${esc(trunc(name, 32))}`;
      return `<div class="mk${e.inferred ? " mk-inf" : ""}" style="top:${top}px" data-rid="${esc(rid)}" data-kind="b" data-idx="${i}">${label}</div>`;
    })
    .join("");
  const utts = items
    .filter((x) => x.kind === "n")
    .map(({ u, i, top, h, lines }) =>
      `<div class="utt" style="top:${top}px;height:${h}px;-webkit-line-clamp:${lines}" data-rid="${esc(rid)}" data-kind="c" data-idx="${i}">${esc(u.text)}</div>`
    )
    .join("");

  // Time: labels in the left rail, dashed gridlines across every lane. The
  // axis is non-uniform by design, so the spacing between labels is itself
  // information — bursts of activity read as stretched stretches of rail.
  const stepSec = lastT > 240000 ? 60 : lastT > 120000 ? 30 : lastT > 30000 ? 10 : lastT > 10000 ? 5 : 2;
  let railLabels = "", gridLines = "";
  for (let s = 0; s * 1000 <= lastT; s += stepSec) {
    const yt = y(s * 1000);
    railLabels += `<div class="tk" style="top:${yt}px">${s}s</div>`;
    gridLines += `<div class="gl" style="top:${yt}px"></div>`;
  }

  const raw = `<details class="raw"><summary>raw trace JSON</summary><pre>${esc(JSON.stringify(trace, null, 2))}</pre></details>`;

  return `
    <div class="tl-head">
      <div class="th-rail"></div>
      <div class="th-b">Behavior (${beh.length})</div>
      <div class="th-cur">cursor</div>
      <div class="th-n">Narration (${cog.length})</div>
    </div>
    <div class="tl-lanes" style="height:${H}px">
      <div class="rail">${railLabels}</div>
      <div class="lane behav">${marks}</div>
      <div class="curlane">${cursorBlocks}</div>
      <div class="lane narr">${utts}</div>
      <div class="gridlines">${gridLines}</div>
    </div>
    ${raw}`;
}


