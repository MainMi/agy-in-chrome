// Content-script capturer — injected into every frame of every tab
// (all_frames, document_start). Split into two ordered parts loaded via
// manifest.json; part 2 shares state through window.__ocicCapture.

(function () {
  if (window.__ocicRecorderLoaded) return;
  window.__ocicRecorderLoaded = true;

  const OVERRIDE_KEY = "altKey"; // Alt/Option = override/mask mode (§8)


  // --- Heuristic thresholds (documented in SCHEMA_v0.md § Heuristics) --------
  // Bias: FALSE POSITIVES over false negatives. The cursor track keeps the raw
  // trajectory losslessly, so a missed hover loses nothing; and inferred events
  // are flagged so the reading agent treats them as guesses to cross-check, not
  // confident facts. So these thresholds are deliberately LOW.
  const HOVER_DWELL_MS = 350; // a brief pause (not a dead stop) counts as hover
  const HOVER_MOVE_EPS = 8; // px; movement beyond this restarts the dwell
  const DRAG_MIN_PX = 8; // button-held movement beyond this is a drag, not a click
  const CURSOR_SAMPLE_MS = 50; // throttle raw cursor sampling
  const CURSOR_BATCH_MAX = 40; // flush the cursor batch at this many points
  const CURSOR_FLUSH_MS = 700; // ...or at least this often

  // The service worker tells us when a recording is active.
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg && msg.__ocic === "recording_state") NS.recording = !!msg.on;
  });
  // Ask on load in case we were injected mid-recording (new tab during a session).
  try {
    chrome.runtime.sendMessage({ __ocic: "recorder_hello" }, (r) => {
      if (chrome.runtime.lastError) return;
      if (r && typeof r.on === "boolean") NS.recording = r.on;
    });
  } catch {}

  // ---- durable anchor resolution -------------------------------------------
  const TAG_ROLE = {
    a: "link", button: "button", input: "textbox", textarea: "textbox",
    select: "combobox", img: "img"
  };
  const SEMANTIC_ATTRS = [
    "id", "class", "role", "type", "name", "href", "placeholder",
    "data-testid", "data-test", "aria-label", "aria-labelledby"
  ];

  function accessibleName(el) {
    return (
      el.getAttribute("aria-label") ||
      (el.getAttribute("aria-labelledby") &&
        document.getElementById(el.getAttribute("aria-labelledby"))?.textContent?.trim()) ||
      el.getAttribute("title") ||
      el.getAttribute("alt") ||
      (el.tagName === "INPUT" && el.labels?.[0]?.textContent?.trim()) ||
      el.textContent?.trim().slice(0, 80) ||
      ""
    );
  }

  function pickAttrs(el) {
    const out = {};
    for (const a of SEMANTIC_ATTRS) {
      const v = el.getAttribute && el.getAttribute(a);
      if (v) out[a] = v.length > 80 ? v.slice(0, 80) : v;
    }
    return out;
  }

  // A stable-ish CSS selector: prefer id, then data-testid, then a scoped
  // path. Not guaranteed unique across redesigns, but the anchor also carries
  // role/name/text so the agent has multiple ways to relocate the element.
  function cssSelector(el) {
    if (el.id) return `#${CSS.escape(el.id)}`;
    const testid = el.getAttribute("data-testid") || el.getAttribute("data-test");
    if (testid) return `${el.tagName.toLowerCase()}[data-testid="${testid}"]`;
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 5) {
      let part = node.tagName.toLowerCase();
      if (node.getAttribute("role")) part += `[role="${node.getAttribute("role")}"]`;
      const sibs = node.parentNode
        ? [...node.parentNode.children].filter((c) => c.tagName === node.tagName)
        : [];
      if (sibs.length > 1) part += `:nth-of-type(${sibs.indexOf(node) + 1})`;
      parts.unshift(part);
      if (node.id) { parts[0] = `#${CSS.escape(node.id)}`; break; }
      node = node.parentElement;
    }
    return parts.join(" > ");
  }

  // The ancestor path: cleaned opening tags up the tree (location context).
  // §13-E showed this is ~150-300 tokens vs 75k for full HTML.
  function ancestorPath(el, depth = 6) {
    const path = [];
    let node = el.parentElement;
    while (node && node.nodeType === 1 && path.length < depth) {
      let tag = `<${node.tagName.toLowerCase()}`;
      const id = node.id ? ` id="${node.id}"` : "";
      const role = node.getAttribute("role") ? ` role="${node.getAttribute("role")}"` : "";
      const cls = node.getAttribute("class")
        ? ` class="${node.getAttribute("class").slice(0, 40)}"`
        : "";
      path.unshift(tag + id + role + cls + ">");
      node = node.parentElement;
    }
    return path;
  }

  function resolveAnchor(el) {
    if (!el || el.nodeType !== 1) return null;
    return {
      selector: cssSelector(el),
      role: el.getAttribute("role") || TAG_ROLE[el.tagName.toLowerCase()] || undefined,
      name: accessibleName(el) || undefined,
      text: el.textContent?.trim().slice(0, 120) || undefined,
      tag: el.tagName.toLowerCase(),
      attrs: pickAttrs(el),
      path: ancestorPath(el)
    };
  }

  // ---- pre/post effect window ----------------------------------------------
  // The action->result signal: what mutated in the ~700ms after an action.
  // Scoped and bounded, not a full replay stream.
  function captureEffect(afterFn) {
    const added = [];
    const removed = [];
    const obs = new MutationObserver((records) => {
      for (const r of records) {
        for (const n of r.addedNodes) {
          if (n.nodeType === 1 && added.length < 8) added.push(describeNode(n));
        }
        for (const n of r.removedNodes) {
          if (n.nodeType === 1 && removed.length < 8) removed.push(describeNode(n));
        }
      }
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
    const urlBefore = location.href;
    setTimeout(() => {
      obs.disconnect();
      const effect = {};
      if (added.length) effect.added = added;
      if (removed.length) effect.removed = removed;
      if (location.href !== urlBefore) effect.urlChanged = location.href;
      afterFn(effect);
    }, 700);
  }

  function describeNode(n) {
    const role = n.getAttribute?.("role");
    const label = n.getAttribute?.("aria-label") || n.textContent?.trim().slice(0, 40);
    return `${n.tagName.toLowerCase()}${role ? `[role=${role}]` : ""}${label ? ` ${label}` : ""}`;
  }

  // ---- emit ----------------------------------------------------------------
  function emit(action, el, extra) {
    if (!NS.recording) return;
    const suppressed = extra && extra.suppressed;
    const base = {
      __ocic: "behavior_event",
      t: (extra && extra.t) || Date.now(), // epoch; SW subtracts started_at
      vw: window.innerWidth, // viewport at capture — lets frames map cursor x/y
      vh: window.innerHeight,
      action,
      anchor: el ? resolveAnchor(el) : undefined,
      suppressed: suppressed || undefined,
      // inferred = derived by a heuristic (hover, left_click_drag), not a DOM
      // event. The reading agent should treat these as guesses and cross-check
      // against the cursor track, effect window, and narration.
      inferred: (extra && extra.inferred) || undefined,
      value: extra && extra.value
    };
    // THE CORE KEY: `command` is the exact OCIC tool input that reproduces
    // this event — 1:1 field names, units, and coordinate space (viewport px,
    // which is what OCIC dispatches over CDP). Every tool also takes tabId:
    // use the event's `tab`. Nothing here is invented: values come from the
    // observed DOM event; commands on `inferred` events are heuristic
    // reconstructions and are flagged as such at the event level.
    const COMPUTER_ACTIONS = new Set([
      "left_click", "right_click", "double_click", "triple_click", "hover",
      "left_click_drag", "type", "key", "scroll"
    ]);
    const input = {};
    for (const k of ["coordinate", "start_coordinate", "modifiers", "text",
                     "scroll_direction", "scroll_amount"]) {
      if (extra && extra[k] !== undefined) input[k] = extra[k];
    }
    if (COMPUTER_ACTIONS.has(action)) {
      base.command = { tool: "computer", input: { action, ...input } };
    }
    // Recorder timing enrichment for drags (not OCIC params): the cursor
    // track holds the actual curve for [t_down, t_up].
    if (extra && extra.t_down !== undefined) base.t_down = extra.t_down;
    if (extra && extra.t_up !== undefined) base.t_up = extra.t_up;
    if (
      !suppressed &&
      (action === "left_click" || action === "type" || action === "key" || action === "left_click_drag")
    ) {
      captureEffect((effect) => {
        if (Object.keys(effect).length) base.effect = effect;
        send(base);
      });
    } else {
      send(base);
    }
  }

  function send(evt) {
    try {
      chrome.runtime.sendMessage(evt, () => void chrome.runtime.lastError);
    } catch {}
  }

  // Shared with capture-events.js (the DOM listener half of this capturer).
  const NS = (window.__ocicCapture = {
    recording: false,
    emit,
    OVERRIDE_KEY,
    HOVER_DWELL_MS,
    HOVER_MOVE_EPS,
    DRAG_MIN_PX,
    CURSOR_SAMPLE_MS,
    CURSOR_BATCH_MAX,
    CURSOR_FLUSH_MS,
  });
})();
