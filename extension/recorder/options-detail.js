// Detail popup (modal) for the sessions viewer, split out of options.js —
// pure refactor, behavior unchanged.
import { esc, trunc, traceCache } from "./options-shared.js";

// ---- detail popup ----
// Clicking a timeline item opens its full record in a modal that floats over
// the page, so the absolutely-positioned timeline never shifts or distorts.
const modal = document.getElementById("modal");
const modalBody = document.getElementById("modalBody");
function closeModal() {
  modal.hidden = true;
  modalBody.innerHTML = "";
}
modal.addEventListener("click", (e) => {
  if (e.target.hasAttribute("data-close")) closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modal.hidden) closeModal();
});
document.getElementById("sessions").addEventListener("click", (e) => {
  // Copy a paste-able reference to a session (path + how to read it).
  const copyBtn = e.target.closest(".copy-ref");
  if (copyBtn) {
    e.preventDefault();
    const p = copyBtn.getAttribute("data-path");
    const rid = copyBtn.getAttribute("data-rid");
    const ts = copyBtn.getAttribute("data-tstatus") || "";
    // Same contract as the on-stop reference in background.js: the text must
    // describe what is actually in the bundle, never what usually is.
    const warn =
      ts && ts !== "ok"
        ? ` WARNING — TRANSCRIPT FAILED: ${ts}. The narration track is empty or incomplete, so do NOT read a short/absent cognitive[] as the operator having stayed silent. The raw audio is in audio/ and trace.json records per-segment status in transcript_segments. Please tell me this happened.`
        : "";
    const ref = p
      ? `Read the browser recording at ${p} — an imitation-learning rollout of an expert doing a task. trace.json holds four tracks on one shared clock (behavior, cursor, images, narration); SCHEMA_v0.md in that folder is the field reference, and images/ holds the frames.${warn}`
      : `Recording ${rid} was not written to disk; open it in the AGY in Chrome extension Options to inspect.`;
    navigator.clipboard.writeText(ref).then(() => {
      copyBtn.textContent = "Copied";
      setTimeout(() => (copyBtn.textContent = "Copy reference"), 1500);
    });
    return;
  }
  // Cursor gesture thumbnail (or fallback block) → full gesture popup.
  const cblk = e.target.closest(".curseg, .cur");
  if (cblk) {
    const cache = traceCache.get(cblk.getAttribute("data-rid"));
    if (cache && cache.cseg) openCursorDetail(cache.cseg[+cblk.getAttribute("data-cseg")], cache.images);
    return;
  }
  const el = e.target.closest(".mk, .utt");
  if (!el) return;
  const cache = traceCache.get(el.getAttribute("data-rid"));
  if (!cache) return;
  const idx = +el.getAttribute("data-idx");
  if (el.getAttribute("data-kind") === "b") openBehaviorDetail(cache.beh[idx], cache.images);
  else openUtteranceDetail(cache.cog[idx], cache.images);
});

// The 240p frame nearest a given time on the shared clock — the screen as it
// looked at that moment. (The on-disk full-size images/ dir is the agent's;
// these small frames are for the viewer.)
function nearestImage(images, t) {
  if (!images || !images.length) return null;
  let best = images[0], bd = Math.abs(images[0].t - t);
  for (const im of images) {
    const d = Math.abs(im.t - t);
    if (d < bd) { bd = d; best = im; }
  }
  return best;
}
function frameHtml(images, t) {
  const im = nearestImage(images, t);
  if (!im || !im.dataUrl) return "";
  return `${row("Frame", `nearest at ${(im.t / 1000).toFixed(1)}s${im.ref ? ` · <code>${esc(im.ref)}</code>` : ""}`)}<img class="frame" src="${im.dataUrl}" alt="frame">`;
}

// A labelled endpoint dot: filled circle + a coloured pill with the label,
// nudged to stay on-canvas.
function endpointDot(ctx, x, y, color, label) {
  ctx.beginPath();
  ctx.arc(x, y, 5, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 1.5;
  ctx.stroke();
  ctx.font = "600 11px ui-monospace, Menlo, monospace";
  ctx.textBaseline = "middle";
  const tw = ctx.measureText(label).width;
  let lx = x + 10;
  if (lx + tw + 6 > ctx.canvas.width) lx = x - tw - 16;
  let ly = y;
  if (ly < 10) ly = 10;
  else if (ly > ctx.canvas.height - 10) ly = ctx.canvas.height - 10;
  ctx.fillStyle = color;
  ctx.fillRect(lx - 4, ly - 8, tw + 8, 16);
  ctx.fillStyle = "#fff";
  ctx.fillText(label, lx, ly + 1);
}

// Cursor gesture drawn ON the frame it happened over. With the frame's viewport
// dims, cursor (x,y) map straight onto the screenshot, so you see the path over
// the actual screen. Start = green, end = red. Falls back to an abstract path
// if the nearest frame has no viewport dims.
function openCursorDetail(seg, images) {
  if (!seg || !seg.pts.length) return;
  const im = nearestImage(images, seg.start);
  const overlay = !!(im && im.dataUrl && im.vw > 0 && im.vh > 0);
  const W = 520;
  const Hc = overlay ? Math.max(120, Math.round(W * (im.vh / im.vw))) : 300;

  modalBody.innerHTML = `
    <h3>Cursor gesture</h3>
    ${row("Time", `${(seg.start / 1000).toFixed(2)}s – ${(seg.end / 1000).toFixed(2)}s`)}
    ${row("Points", String(seg.pts.length))}
    ${overlay ? row("Over frame", `nearest at ${(im.t / 1000).toFixed(1)}s${im.ref ? ` · <code>${esc(im.ref)}</code>` : ""}`) : ""}
    <canvas id="curcv" width="${W}" height="${Hc}"></canvas>
    ${overlay ? "" : frameHtml(images, seg.start)}`;
  modal.hidden = false;
  const ctx = document.getElementById("curcv").getContext("2d");

  const strokePath = (mapx, mapy, color, width) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();
    seg.pts.forEach((p, i) => (i ? ctx.lineTo(mapx(p.x), mapy(p.y)) : ctx.moveTo(mapx(p.x), mapy(p.y))));
    ctx.stroke();
  };
  const drawPath = (mapx, mapy) => {
    strokePath(mapx, mapy, "rgba(0,0,0,.45)", 5); // halo so the path reads on any frame
    strokePath(mapx, mapy, "#ffd400", 2.5);
    const a = seg.pts[0], b = seg.pts[seg.pts.length - 1];
    endpointDot(ctx, mapx(a.x), mapy(a.y), "#0e8a5f", "start");
    endpointDot(ctx, mapx(b.x), mapy(b.y), "#d23b2e", "end");
  };

  if (overlay) {
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, W, Hc);
      ctx.fillStyle = "rgba(0,0,0,.18)"; // dim the frame so the path pops
      ctx.fillRect(0, 0, W, Hc);
      drawPath((x) => (x / im.vw) * W, (y) => (y / im.vh) * Hc);
    };
    img.src = im.dataUrl;
  } else {
    const xs = seg.pts.map((p) => p.x), ys = seg.pts.map((p) => p.y);
    const minx = Math.min(...xs), maxx = Math.max(...xs);
    const miny = Math.min(...ys), maxy = Math.max(...ys);
    const pad = 22, sx = maxx - minx || 1, sy = maxy - miny || 1;
    const scale = Math.min((W - 2 * pad) / sx, (Hc - 2 * pad) / sy);
    drawPath((x) => pad + (x - minx) * scale, (y) => pad + (y - miny) * scale);
  }
}

// The cursor gesture, drawn spatially (the trajectory can't live in a
// time-vertical lane, so the lane shows WHEN and the popup shows the SHAPE —
// the circle, the point, the drag curve). Start = green dot, end = red.
function row(k, v) {
  return v ? `<div class="mrow"><div class="k">${k}</div><div class="v">${v}</div></div>` : "";
}
function openBehaviorDetail(e, images) {
  if (!e) return;
  const a = e.anchor || {};
  const attrs = a.attrs
    ? Object.entries(a.attrs).map(([k, v]) => `<code>${esc(k)}="${esc(v)}"</code>`).join(" ")
    : "";
  const path = a.path && a.path.length ? `<div class="path">${a.path.map(esc).join("\n")}</div>` : "";
  const val = e.value != null ? (typeof e.value === "string" ? e.value : JSON.stringify(e.value)) : "";
  const effect = e.effect ? JSON.stringify(e.effect, null, 2) : "";
  // Spatial grounding, same treatment as the cursor popup: if the event has a
  // pointer position (p) or drag endpoints, draw it ON the nearest frame using
  // the frame's viewport dims. Falls back to the plain frame image otherwise.
  const im = nearestImage(images, e.t);
  // The command core key first; fallbacks for older bundles (flattened
  // fields, then value.from/to and p).
  const ci = (e.command && e.command.input) || e;
  const drag =
    ci.start_coordinate && ci.coordinate
      ? { from: { x: ci.start_coordinate[0], y: ci.start_coordinate[1] },
          to: { x: ci.coordinate[0], y: ci.coordinate[1] } }
      : e.value && e.value.from && e.value.to
        ? e.value
        : null;
  const pt = !drag && ci.coordinate ? { x: ci.coordinate[0], y: ci.coordinate[1] } : e.p || null;
  const overlay = !!(im && im.dataUrl && im.vw > 0 && im.vh > 0 && (pt || drag));
  const W = 520;
  const Hb = overlay ? Math.max(120, Math.round(W * (im.vh / im.vw))) : 0;
  modalBody.innerHTML = `
    <h3>${esc(e.action)}${e.suppressed ? " · override (not fired)" : ""}${e.inferred ? " · inferred (heuristic — check the narration)" : ""}</h3>
    ${row("Time", `${(e.t / 1000).toFixed(2)}s · t=${e.t}ms · tab ${e.tab}/frame ${e.frame ?? 0}`)}
    ${row("Element", esc(a.name || "") + (a.role ? ` · <code>${esc(a.role)}</code>` : ""))}
    ${row("Selector", a.selector ? `<code>${esc(a.selector)}</code>` : "")}
    ${row("Text", esc(a.text || ""))}
    ${row("Attrs", attrs)}
    ${row("Path", path)}
    ${row("Command", e.command ? `<code>${esc(JSON.stringify(e.command))}</code>` : "")}
    ${row("Coordinate", ci.coordinate ? `<code>[${ci.coordinate.join(", ")}]</code>${ci.start_coordinate ? ` from <code>[${ci.start_coordinate.join(", ")}]</code>` : ""}${ci.modifiers ? ` · <code>${esc(ci.modifiers)}</code>` : ""}` : "")}
    ${row("Text", ci.text ? `<code>${esc(ci.text)}</code>` : "")}
    ${row("URL", (ci.url || e.url) ? `<code>${esc(ci.url || e.url)}</code>` : "")}
    ${row("Scroll", ci.scroll_direction ? `<code>${esc(ci.scroll_direction)} × ${ci.scroll_amount || 3} ticks</code>` : "")}
    ${row("Value", val ? `<code>${esc(val)}</code>` : "")}
    ${row("Effect", effect ? `<code>${esc(effect)}</code>` : "")}
    ${overlay
      ? `${row("On frame", `nearest at ${(im.t / 1000).toFixed(1)}s${im.ref ? ` · <code>${esc(im.ref)}</code>` : ""}`)}<canvas id="behcv" width="${W}" height="${Hb}"></canvas>`
      : frameHtml(images, e.t)}
    <details class="raw"><summary>raw JSON</summary><pre>${esc(JSON.stringify(e, null, 2))}</pre></details>`;
  modal.hidden = false;
  if (overlay) {
    const ctx = document.getElementById("behcv").getContext("2d");
    const mx = (x) => (x / im.vw) * W;
    const my = (y) => (y / im.vh) * Hb;
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, W, Hb);
      ctx.fillStyle = "rgba(0,0,0,.18)"; // dim so the marker pops
      ctx.fillRect(0, 0, W, Hb);
      if (drag) {
        ctx.strokeStyle = "rgba(0,0,0,.45)"; ctx.lineWidth = 5; ctx.lineCap = "round";
        ctx.beginPath(); ctx.moveTo(mx(drag.from.x), my(drag.from.y)); ctx.lineTo(mx(drag.to.x), my(drag.to.y)); ctx.stroke();
        ctx.strokeStyle = "#ffd400"; ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.moveTo(mx(drag.from.x), my(drag.from.y)); ctx.lineTo(mx(drag.to.x), my(drag.to.y)); ctx.stroke();
        endpointDot(ctx, mx(drag.from.x), my(drag.from.y), "#0e8a5f", "from");
        endpointDot(ctx, mx(drag.to.x), my(drag.to.y), "#d23b2e", "to");
      } else if (pt) {
        // Crosshair ring at the pointer position + the action as the label.
        ctx.strokeStyle = "rgba(0,0,0,.55)"; ctx.lineWidth = 4;
        ctx.beginPath(); ctx.arc(mx(pt.x), my(pt.y), 11, 0, Math.PI * 2); ctx.stroke();
        ctx.strokeStyle = "#ffd400"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(mx(pt.x), my(pt.y), 11, 0, Math.PI * 2); ctx.stroke();
        endpointDot(ctx, mx(pt.x), my(pt.y), "#2a5fd8", e.action);
      }
    };
    img.src = im.dataUrl;
  }
}
function openUtteranceDetail(u, images) {
  if (!u) return;
  modalBody.innerHTML = `
    <h3>Narration</h3>
    ${row("Time", `${(u.t / 1000).toFixed(2)}s – ${(u.end / 1000).toFixed(2)}s`)}
    ${row("Said", esc(u.text))}
    ${frameHtml(images, u.t)}
    <details class="raw"><summary>raw JSON</summary><pre>${esc(JSON.stringify(u, null, 2))}</pre></details>`;
  modal.hidden = false;
}

renderSessions();

// Audits pane: its own module, wired here so the recorder UI stays untouched.
wireAuditTabs();

