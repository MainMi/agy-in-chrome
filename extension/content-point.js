// Content script for AGY in Chrome extension.
// Injected into every page. Provides:
// - Accessibility tree generation (read_page)
// - Element ref mapping with WeakRef (persistent across calls)
// - Form input handling
// - Page text extraction
// - Element finding by text/attributes
// Split into ordered parts loaded by manifest.json; they share state through
// window.__agyNS (content scripts cannot use ES module imports).

(function () {
  if (window.__agyContentPointLoaded) return;
  window.__agyContentPointLoaded = true;

  const {
    getOrAssignRef,
    resolveRef,
    reverseMap,
    elementMap,
    getRole,
    getAccessibleName,
    isInteractive,
    isVisible,
    generateAccessibilityTree,
    getPageText,
    findElements,
    setFormValue,
  } = window.__agyNS;

  // --- What is actually at a point ---
  // A dispatched click lands on whatever occupies its coordinates, which is not
  // necessarily what the caller aimed at: the target may have scrolled out of
  // view, or something transparent may be sitting on top of it. The dispatch
  // succeeds either way, so without this a hit and a miss are indistinguishable
  // from the tool result. Runs in the isolated world, so it can also report the
  // ref of the element it found — the same ref space read_page/find hand out.
  function describePoint(x, y) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const outside = x < 0 || y < 0 || x >= vw || y >= vh;
    const el = outside ? null : document.elementFromPoint(x, y);
    if (!el) return { hit: null, outside, viewport: [vw, vh] };

    // Shadow DOM: elementFromPoint stops at the host, so walk into the shadow
    // tree to name the node that will really receive the event.
    let node = el;
    for (let depth = 0; depth < 4 && node.shadowRoot; depth++) {
      const inner = node.shadowRoot.elementFromPoint(x, y);
      if (!inner || inner === node) break;
      node = inner;
    }

    const tag = node.tagName.toLowerCase();
    const attrs = {};
    for (const a of ["id", "name", "type", "role", "data-testid", "data-test", "aria-label"]) {
      const v = node.getAttribute && node.getAttribute(a);
      if (v) attrs[a] = v.length > 40 ? v.slice(0, 40) + "…" : v;
    }
    const cls =
      typeof node.className === "string" && node.className.trim()
        ? node.className.trim().split(/\s+/).slice(0, 2).join(".")
        : "";
    const text = (node.textContent || "").replace(/\s+/g, " ").trim().slice(0, 60);
    // Only report a ref the element already has; assigning a new one here would
    // grow the ref map on every click.
    const existing = reverseMap.get(node);
    const ref = existing && elementMap[existing]?.deref() === node ? existing : null;
    // Whether a click here can be a no-op a caller can't tell apart from a hit.
    // Flag it only when the point is on/inside a <label> whose associated
    // control is missing OR not natively activatable, AND no live interactive
    // element is present to receive the bubbled click. A click on a label with
    // a working control, or on a label under a real interactive ancestor, still
    // reaches a target and must not read as dead.
    //
    // The effective disabled state is deliberate: ctrl.disabled is the control's
    // own attribute, so it misses a control disabled by being inside a
    // <fieldset disabled>, while ctrl.matches(":disabled") reflects the real,
    // inheritable state. Testing :disabled (not :enabled) also matters because
    // :enabled only matches button/input/select/textarea/option — it would
    // wrongly mark non-disabled labelable elements like <meter>/<output>/
    // <progress> as non-activatable and flag a healthy label as dead.
    //
    // The hit must be resolved through the DOM, not just the direct
    // elementFromPoint result: labels usually wrap a <span>/<svg> child, so the
    // point often lands on the child, not the <label> itself.
    //
    // The ancestor selector matches only LIVE interactive elements: enabled form
    // controls, acted-on anchors, and interactive ARIA roles. Bare [role] would
    // match presentational/landmark roles like banner or presentation; bare
    // input/button would count a DISABLED control as "still gets the click".
    const labelEl = node.closest ? node.closest("label") : null;
    const ctrl = labelEl && labelEl.control;
    const noNativeActivation = !ctrl || ctrl.matches(":disabled");
    // [onclick]/[tabindex] must also exclude disabled controls: a disabled
    // control that happens to carry one still never receives the click.
    // ARIA roles are ASCII case-insensitive, so use the `i` flag. contenteditable
    // and media controls are natively interactive targets of their own.
    const interactiveAncestor = node.closest(
      "a[href],a[onclick]," +
      "button:enabled,input:enabled,textarea:enabled,select:enabled," +
      "summary," +
      "[onclick]:not(:disabled),[tabindex]:not(:disabled)," +
      "[contenteditable]:not([contenteditable=\"false\"]),audio[controls],video[controls]," +
      "[role=button i],[role=combobox i],[role=link i],[role=menuitem i],[role=menuitemradio i]," +
      "[role=menuitemcheckbox i],[role=option i],[role=radio i],[role=checkbox i],[role=tab i]," +
      "[role=switch i],[role=textbox i],[role=spinbutton i],[role=slider i],[role=listbox i]," +
      "[role=treeitem i]"
    );
    const deadLabel = !!labelEl && noNativeActivation && !interactiveAncestor;
    return {
      hit: { tag, attrs, cls, text, ref },
      // <html>/<body> means the point is over page background — nothing
      // interactive there, which is almost always a miss worth flagging.
      bare: tag === "html" || tag === "body",
      deadLabel,
      viewport: [vw, vh]
    };
  }

  // --- Get element coordinates for ref ---
  function getRefCoordinates(refId, opts = {}) {
    const el = resolveRef(refId);
    if (!el) return null;

    // Bring the element into view before reading its position.
    //
    // Coordinates are viewport-relative, so an element scrolled out of view has
    // coordinates that cannot be clicked at all: the dispatch lands on the
    // document root instead. That is not a reporting problem, it is a targeting
    // one — the caller named an element, and the element is reachable, it just
    // is not on screen yet. Scrolling first is what a person does, and what
    // Playwright/Puppeteer do before every click, so the click lands on what
    // was actually asked for.
    //
    // block/inline "center" (rather than the default "start") keeps the element
    // clear of sticky headers and footers, which are a common way for a
    // technically-in-viewport element to still be covered.
    let scrolledFrom = null;
    if (opts.scrollIntoView !== false) {
      const r = el.getBoundingClientRect();
      const off =
        r.left < 0 || r.top < 0 || r.right > window.innerWidth || r.bottom > window.innerHeight;
      if (off) {
        // Remember where it was, so the caller can record that a scroll
        // happened. A move this large silently changing the coordinates is
        // exactly the kind of thing a debug log has to show.
        scrolledFrom = [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)];
        try {
          el.scrollIntoView({ block: "center", inline: "center", behavior: "instant" });
        } catch {
          el.scrollIntoView(true);
        }
      }
    }

    const rect = el.getBoundingClientRect();
    const x = Math.round(rect.x + rect.width / 2);
    const y = Math.round(rect.y + rect.height / 2);
    // Report what is actually at the resulting point, so the caller learns when
    // something else (an overlay, a sticky bar) will receive the click. That
    // case is NOT auto-corrected: a person clicking there would hit the overlay
    // too, so silently clicking through it would be the unfaithful choice.
    let covering = null;
    if (x >= 0 && y >= 0 && x < window.innerWidth && y < window.innerHeight) {
      const at = document.elementFromPoint(x, y);
      if (at && at !== el && !el.contains(at) && !at.contains(el)) {
        covering = describeBrief(at);
      }
    }
    return {
      x,
      y,
      reachable: x >= 0 && y >= 0 && x < window.innerWidth && y < window.innerHeight,
      covering,
      scrolledFrom,
    };
  }

  function describeBrief(el) {
    const id = el.id ? `#${el.id}` : "";
    const cls =
      typeof el.className === "string" && el.className.trim()
        ? "." + el.className.trim().split(/\s+/)[0]
        : "";
    const t = (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40);
    return `<${el.tagName.toLowerCase()}${id}${cls}>${t ? ` "${t}"` : ""}`;
  }

  // --- Message handler ---
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === "generateAccessibilityTree") {
      const result = generateAccessibilityTree(msg.options || {});
      sendResponse({ result });
      return true;
    }

    if (msg.type === "getPageText") {
      const result = getPageText();
      sendResponse({ result });
      return true;
    }

    if (msg.type === "findElements") {
      const result = findElements(msg.query);
      sendResponse({ result });
      return true;
    }

    if (msg.type === "setFormValue") {
      const result = setFormValue(msg.ref, msg.value);
      sendResponse({ result });
      return true;
    }

    if (msg.type === "describePoint") {
      sendResponse({ result: describePoint(msg.x, msg.y) });
      return true;
    }

    if (msg.type === "getRefCoordinates") {
      const result = getRefCoordinates(msg.ref, { scrollIntoView: msg.scrollIntoView });
      sendResponse({ result });
      return true;
    }

    // Resolve a ref in THIS (isolated) world — where resolveRef/elementMap live —
    // and stamp a DOM attribute on the element so the background page can find it
    // via CDP. CDP Runtime.evaluate runs in the page's MAIN world and cannot see
    // window.__unblockedChrome, so a main-world resolveRef always returns null;
    // the DOM is shared across worlds, so an attribute set here IS visible to CDP.
    // Used by file_upload / upload_image to reach a (possibly hidden) file input.
    if (msg.type === "markElementForUpload") {
      const el = resolveRef(msg.ref);
      if (!el) {
        sendResponse({ ok: false });
        return true;
      }
      const isFileInput =
        el.tagName &&
        el.tagName.toLowerCase() === "input" &&
        (el.type || "").toLowerCase() === "file";
      try { el.setAttribute("data-ocic-upload-target", "1"); } catch {}
      try { el.scrollIntoView({ block: "center", behavior: "instant" }); } catch {}
      sendResponse({ ok: true, isFileInput, tag: el.tagName.toLowerCase() });
      return true;
    }

    if (msg.type === "unmarkElementForUpload") {
      try {
        document
          .querySelectorAll("[data-ocic-upload-target]")
          .forEach((e) => e.removeAttribute("data-ocic-upload-target"));
      } catch {}
      sendResponse({ ok: true });
      return true;
    }

    return false;
  });

  // Expose globally for executeScript fallback
  window.__unblockedChrome = {
    describePoint,
    generateAccessibilityTree,
    getPageText,
    findElements,
    setFormValue,
    getRefCoordinates,
    resolveRef,
    reverseMap,
    elementMap,
  };
})();
