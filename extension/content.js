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
  if (window.__unblockedChromeLoaded) return;
  window.__unblockedChromeLoaded = true;

  // --- Element reference map ---
  // Persistent ref IDs stored as WeakRefs so GC still works
  let refCounter = 0;
  const elementMap = {}; // refId -> WeakRef<Element>
  const reverseMap = new WeakMap(); // Element -> refId

  function getOrAssignRef(el) {
    const existing = reverseMap.get(el);
    if (existing && elementMap[existing]?.deref() === el) return existing;
    const ref = `ref_${++refCounter}`;
    elementMap[ref] = new WeakRef(el);
    reverseMap.set(el, ref);
    return ref;
  }

  function resolveRef(refId) {
    const wr = elementMap[refId];
    if (!wr) return null;
    const el = wr.deref();
    if (!el) {
      delete elementMap[refId];
      return null;
    }
    return el;
  }

  // --- ARIA role mapping ---
  const TAG_TO_ROLE = {
    a: "link",
    button: "button",
    input: "textbox",
    textarea: "textbox",
    select: "combobox",
    img: "img",
    h1: "heading",
    h2: "heading",
    h3: "heading",
    h4: "heading",
    h5: "heading",
    h6: "heading",
    nav: "navigation",
    main: "main",
    header: "banner",
    footer: "contentinfo",
    aside: "complementary",
    form: "form",
    table: "table",
    tr: "row",
    th: "columnheader",
    td: "cell",
    ul: "list",
    ol: "list",
    li: "listitem",
    dialog: "dialog",
    details: "group",
    summary: "button",
    progress: "progressbar",
    meter: "meter",
    video: "video",
    audio: "audio",
    section: "region",
    article: "article",
  };

  function getRole(el) {
    if (el.getAttribute("role")) return el.getAttribute("role");
    const tag = el.tagName.toLowerCase();
    if (tag === "input") {
      const type = (el.type || "text").toLowerCase();
      const typeRoles = {
        checkbox: "checkbox",
        radio: "radio",
        range: "slider",
        button: "button",
        submit: "button",
        reset: "button",
        search: "searchbox",
        number: "spinbutton",
      };
      return typeRoles[type] || "textbox";
    }
    return TAG_TO_ROLE[tag] || null;
  }

  // --- Accessible name ---
  function getAccessibleName(el) {
    // Priority: aria-label > aria-labelledby > placeholder > title > alt > label > text
    const ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel) return ariaLabel.trim();

    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      const names = labelledBy
        .split(/\s+/)
        .map((id) => document.getElementById(id)?.textContent?.trim())
        .filter(Boolean);
      if (names.length) return names.join(" ");
    }

    // typeof guards: a <form> (or <fieldset>) exposes its named controls as
    // properties via a [LegacyOverrideBuiltIns] named getter, so an
    // <input name="title"> makes form.title the ELEMENT, not the string —
    // and .trim() on it throws, taking down read_page/find for the whole
    // page. Same shadowing applies to placeholder and alt.
    if (typeof el.placeholder === "string" && el.placeholder) return el.placeholder.trim();
    if (typeof el.title === "string" && el.title) return el.title.trim();
    if (typeof el.alt === "string" && el.alt) return el.alt.trim();

    // Associated <label>
    if (el.id) {
      const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (label) return label.textContent.trim();
    }
    if (el.closest("label")) {
      const labelText = el.closest("label").textContent.trim();
      if (labelText) return labelText;
    }

    // Direct text content (only for leaf-ish elements)
    const tag = el.tagName.toLowerCase();
    if (["a", "button", "h1", "h2", "h3", "h4", "h5", "h6", "li", "summary", "label", "th", "td", "span"].includes(tag)) {
      const text = el.textContent?.trim();
      if (text && text.length < 200) return text;
    }

    return "";
  }

  // --- Interactivity check ---
  function isInteractive(el) {
    const tag = el.tagName.toLowerCase();
    if (["a", "button", "input", "textarea", "select", "summary", "details"].includes(tag)) return true;
    if (el.getAttribute("role") && ["button", "link", "textbox", "checkbox", "radio", "tab", "menuitem", "switch", "combobox", "slider", "spinbutton", "searchbox", "option"].includes(el.getAttribute("role"))) return true;
    if (el.tabIndex >= 0) return true;
    if (el.onclick || el.getAttribute("onclick")) return true;
    if (el.contentEditable === "true") return true;
    return false;
  }

  // --- Visibility check ---
  function isVisible(el) {
    if (el.offsetParent === null && el.tagName.toLowerCase() !== "body" && getComputedStyle(el).position !== "fixed") return false;
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    return true;
  }

  // Shared with the other content-*.js parts loaded after this file.
  window.__agyNS = {
    getOrAssignRef,
    resolveRef,
    reverseMap,
    elementMap,
    getRole,
    getAccessibleName,
    isInteractive,
    isVisible,
  };
})();
