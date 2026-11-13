// Content-script capturer — injected into every frame of every tab
// (all_frames, document_start). Split into two ordered parts loaded via
// manifest.json; part 2 shares state through window.__ocicCapture.

(function () {
  if (window.__ocicCaptureEventsLoaded) return;
  window.__ocicCaptureEventsLoaded = true;

  const NS = window.__ocicCapture;
  const {
    emit,
    OVERRIDE_KEY,
    HOVER_DWELL_MS,
    HOVER_MOVE_EPS,
    DRAG_MIN_PX,
    CURSOR_SAMPLE_MS,
    CURSOR_BATCH_MAX,
    CURSOR_FLUSH_MS,
  } = NS;


  // ---- cursor track (Layer 2) + pointer heuristics -------------------------
  // The cursor track captures the RAW trajectory (all movement, throttled) so
  // the pointing/circling gesture survives losslessly. hover and left_click_drag
  // are inferred landmarks derived from it; they're flagged `inferred`.
  let cursorBatch = [];
  let lastSample = 0;
  function flushCursor() {
    if (!cursorBatch.length) return;
    const points = cursorBatch;
    cursorBatch = [];
    try {
      chrome.runtime.sendMessage(
        { __ocic: "cursor_batch", points, vw: window.innerWidth, vh: window.innerHeight },
        () => void chrome.runtime.lastError
      );
    } catch {}
  }
  setInterval(() => { if (NS.recording) flushCursor(); }, CURSOR_FLUSH_MS);

  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const NONHOVER = new Set(["BODY", "HTML"]);
  const isHoverWorthy = (el) => el && el.nodeType === 1 && !NONHOVER.has(el.tagName);

  let downPt = null; // pointerdown state {x,y,el,t}
  let dragging = false;
  let justDragged = 0; // ts of last drag, to drop the trailing synthetic click
  let dwellPt = null; // current hover-dwell anchor {x,y}
  let dwellTimer = null;
  let hoveredEl = null; // element already emitted for this dwell

  document.addEventListener(
    "pointerdown",
    (e) => {
      if (!NS.recording || e.button !== 0) return;
      downPt = { x: e.clientX, y: e.clientY, el: e.target, t: Date.now() };
      dragging = false;
      clearTimeout(dwellTimer);
      dwellPt = null;
      hoveredEl = null; // no hover while a button is held
    },
    true
  );

  document.addEventListener(
    "pointermove",
    (e) => {
      if (!NS.recording) return;
      const now = Date.now();
      const p = { x: e.clientX, y: e.clientY };
      // (1) raw cursor track — sample all movement, throttled
      if (now - lastSample >= CURSOR_SAMPLE_MS) {
        lastSample = now;
        cursorBatch.push({ t: now, x: Math.round(p.x), y: Math.round(p.y) });
        if (cursorBatch.length >= CURSOR_BATCH_MAX) flushCursor();
      }
      // (2) drag detection while a button is held
      if (downPt) {
        if (!dragging && dist(downPt, p) > DRAG_MIN_PX) dragging = true;
        return; // no hover mid-press
      }
      // (3) hover dwell — restart on movement, emit after a brief pause
      if (!dwellPt || dist(dwellPt, p) > HOVER_MOVE_EPS) {
        dwellPt = p;
        hoveredEl = null;
        clearTimeout(dwellTimer);
        dwellTimer = setTimeout(() => {
          const el = document.elementFromPoint(p.x, p.y);
          if (el && el !== hoveredEl && isHoverWorthy(el)) {
            hoveredEl = el;
            emit("hover", el, { inferred: true, coordinate: [p.x, p.y] });
          }
        }, HOVER_DWELL_MS);
      }
    },
    true
  );

  document.addEventListener(
    "pointerup",
    (e) => {
      if (!NS.recording || !downPt) return;
      if (dragging) {
        justDragged = Date.now();
        const from = downPt;
        // Anchor on the drop target; keep endpoints + the time range so the
        // actual curve can be pulled from the cursor track for [t_down, t_up].
        emit("left_click_drag", e.target, {
          inferred: true,
          start_coordinate: [from.x, from.y], // OCIC's drag params, 1:1
          coordinate: [e.clientX, e.clientY],
          t_down: from.t, // recorder timing enrichment: the curve for
          t_up: Date.now() // [t_down, t_up] lives in the cursor track
        });
      }
      downPt = null;
      dragging = false;
    },
    true
  );

  // OCIC-syntax modifier string ("ctrl+shift+cmd"). Alt is EXCLUDED on clicks:
  // the recorder reserves Alt as the override/mask key, so an alt-click records
  // suppressed intent, never an alt-modified click (documented exception).
  function modStr(e, withAlt) {
    const m = [];
    if (e.ctrlKey) m.push("ctrl");
    if (withAlt && e.altKey) m.push("alt");
    if (e.shiftKey) m.push("shift");
    if (e.metaKey) m.push("cmd");
    return m.length ? m.join("+") : undefined;
  }

  // ---- discrete DOM events (certain — never flagged inferred) ---------------
  document.addEventListener(
    "click",
    (e) => {
      if (!NS.recording) return;
      if (Date.now() - justDragged < 200) return; // the pointerup was a drag
      if (e[OVERRIDE_KEY]) {
        // Override/mask mode: record the intent, suppress the real click.
        e.preventDefault();
        e.stopPropagation();
        emit("left_click", e.target, { suppressed: true, coordinate: [e.clientX, e.clientY] });
        return;
      }
      // Click-count discrimination, mirroring OCIC's distinct commands: a
      // rapid burst ascends left_click (detail 1) → double_click (the dblclick
      // listener) → triple_click (detail 3). Replay takes the last of a burst.
      if (e.detail >= 3) {
        emit("triple_click", e.target, { coordinate: [e.clientX, e.clientY], modifiers: modStr(e) });
        return;
      }
      if (e.detail === 2) return; // the dblclick listener emits double_click
      emit("left_click", e.target, { coordinate: [e.clientX, e.clientY], modifiers: modStr(e) });
    },
    true
  );

  document.addEventListener(
    "contextmenu",
    (e) => {
      if (NS.recording) emit("right_click", e.target, { coordinate: [e.clientX, e.clientY], modifiers: modStr(e) });
    },
    true
  );

  document.addEventListener(
    "dblclick",
    (e) => {
      if (NS.recording) emit("double_click", e.target, { coordinate: [e.clientX, e.clientY], modifiers: modStr(e) });
    },
    true
  );

  document.addEventListener(
    "keydown",
    (e) => {
      if (!NS.recording) return;
      // Meaningful keys (Enter/Tab/Escape/shortcuts) — typed text is captured
      // on `change` as a value, not per keystroke.
      if (["Enter", "Tab", "Escape"].includes(e.key) || e.metaKey || e.ctrlKey) {
        // OCIC key syntax: lowercase modifiers + key, e.g. "cmd+a", "Enter".
        const mods = modStr(e, true);
        const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
        emit("key", e.target, { text: mods ? mods + "+" + k : k });
      }
    },
    true
  );

  document.addEventListener(
    "change",
    (e) => {
      if (!NS.recording) return;
      const el = e.target;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT")) {
        emit("type", el, { text: (el.value || "").slice(0, 200) });
      }
    },
    true
  );

  // Scroll is recorded as the OCIC scroll command: pointer coordinate +
  // direction + wheel ticks, accumulated per burst. 1 tick = 100px of delta —
  // the exact inverse of OCIC's dispatch constant — clamped to OCIC's 1..10.
  // (Scrollbar drags don't fire wheel; they surface as drags + frame changes.)
  let wheelAcc = null;
  let wheelTimer = null;
  document.addEventListener(
    "wheel",
    (e) => {
      if (!NS.recording) return;
      if (!wheelAcc)
        wheelAcc = { x: e.clientX, y: e.clientY, dx: 0, dy: 0, el: e.target, t: Date.now() };
      wheelAcc.dx += e.deltaX;
      wheelAcc.dy += e.deltaY;
      clearTimeout(wheelTimer);
      wheelTimer = setTimeout(() => {
        const a = wheelAcc;
        wheelAcc = null;
        if (!a) return;
        const vert = Math.abs(a.dy) >= Math.abs(a.dx);
        const px = vert ? a.dy : a.dx;
        if (!px) return;
        emit("scroll", a.el, {
          t: a.t,
          coordinate: [a.x, a.y],
          scroll_direction: vert ? (px > 0 ? "down" : "up") : (px > 0 ? "right" : "left"),
          scroll_amount: Math.max(1, Math.min(10, Math.round(Math.abs(px) / 100)))
        });
      }, 300);
    },
    { capture: true, passive: true }
  );
})();
