// Split out of extension/background.js — pure refactor, behavior unchanged.
import * as humanize from "../humanize/index.js";
import { cdp, ensureAttached } from "./cdp.js";
import { dispatchPlan, effectiveConfig, humanizeOn } from "./config.js";
import { isBrave } from "./detect.js";
import { human } from "./human.js";
import { dispatchMouse, mouseClick } from "./mouse.js";
import { takeScreenshot, writeScreenshotToDisk } from "./screenshot.js";
import { cursorByTab } from "./state.js";
import { sleep } from "./util.js";

// Each computer action case from the original dispatch switch,
// kept verbatim as a function taking the handler's context.
export async function act_screenshot({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        const { base64, imageId } = await takeScreenshot(tabId);
        // Get viewport dimensions for the response message
        let dims = "";
        try {
          const vp = await cdp(tabId, "Runtime.evaluate", {
            expression: "window.innerWidth + 'x' + window.innerHeight",
          });
          if (vp?.result?.value) dims = vp.result.value;
        } catch {}
        // save_to_disk: write the captured image to disk and report the path so
        // Claude Code can open it. Best-effort — never fails the screenshot.
        let saveNote = "";
        if (args.save_to_disk) {
          try {
            const path = await writeScreenshotToDisk(base64);
            saveNote = `\nSaved to disk: ${path}`;
          } catch (e) {
            saveNote = `\n(Unable to save to disk: ${e.message})`;
          }
        }
        return {
          content: [
            { type: "text", text: `Successfully captured screenshot (${dims}, jpeg) - ID: ${imageId}${saveNote}` },
            { type: "image", data: base64, mimeType: "image/jpeg" },
          ],
        };


}

export async function act_left_click({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!coordinate) return { content: [{ type: "text", text: "coordinate is required for left_click" }] };
        await mouseClick(tabId, coordinate[0], coordinate[1], { modifiers });
        return { content: [{ type: "text", text: `Clicked at (${coordinate[0]}, ${coordinate[1]})${hitNote}` }] };

      // Hidden diagnostic (not in the tool schema): serially times every CDP
      // input variant at the given coordinate so we can hunt for a dispatch
      // path Brave acks fast (keyboard-style) instead of the ~5s mouse path.

}

export async function act_diag_input({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        const dx = coordinate ? coordinate[0] : 200;
        const dy = coordinate ? coordinate[1] : 200;
        const r = {};
        const t = async (label, fn) => {
          const t0 = Date.now();
          try { await fn(); r[label] = (Date.now() - t0) / 1000; }
          catch (e) { r[label] = (Date.now() - t0) / 1000; r[label + "_err"] = String(e.message || e).slice(0, 80); }
        };
        await t("mouse_moved", () => cdp(tabId, "Input.dispatchMouseEvent", { type: "mouseMoved", x: dx, y: dy }));
        await t("mouse_pressed", () => cdp(tabId, "Input.dispatchMouseEvent", { type: "mousePressed", x: dx, y: dy, button: "left", clickCount: 1 }));
        await t("mouse_released", () => cdp(tabId, "Input.dispatchMouseEvent", { type: "mouseReleased", x: dx, y: dy, button: "left", clickCount: 1 }));
        await t("touch_start", () => cdp(tabId, "Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: dx, y: dy }] }));
        await t("touch_end", () => cdp(tabId, "Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }));
        await t("synthesize_tap", () => cdp(tabId, "Input.synthesizeTapGesture", { x: dx, y: dy }));
        await t("synthesize_scroll", () => cdp(tabId, "Input.synthesizeScrollGesture", { x: dx, y: dy, yDistance: -100 }));
        await t("insert_text_noop", () => cdp(tabId, "Input.insertText", { text: "" }));
        return { content: [{ type: "text", text: JSON.stringify(r) }] };


}

export async function act_right_click({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!coordinate) return { content: [{ type: "text", text: "coordinate is required for right_click" }] };
        await mouseClick(tabId, coordinate[0], coordinate[1], { button: "right", modifiers });
        return { content: [{ type: "text", text: `Right-clicked at (${coordinate[0]}, ${coordinate[1]})${hitNote}` }] };


}

export async function act_double_click({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!coordinate) return { content: [{ type: "text", text: "coordinate is required for double_click" }] };
        await mouseClick(tabId, coordinate[0], coordinate[1], { clickCount: 2, modifiers });
        return { content: [{ type: "text", text: `Double-clicked at (${coordinate[0]}, ${coordinate[1]})${hitNote}` }] };


}

export async function act_triple_click({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!coordinate) return { content: [{ type: "text", text: "coordinate is required for triple_click" }] };
        await mouseClick(tabId, coordinate[0], coordinate[1], { clickCount: 3, modifiers });
        return { content: [{ type: "text", text: `Triple-clicked at (${coordinate[0]}, ${coordinate[1]})${hitNote}` }] };


}

export async function act_hover({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!coordinate) return { content: [{ type: "text", text: "coordinate is required for hover" }] };
        if (await humanizeOn(tabId)) {
          // Curved approach, then park STILL. No tremor while holding: a hover
          // exists to keep a tooltip/menu open, and jitter near an element edge
          // can cross the boundary, fire mouseleave and dismiss it.
          const s = human(effectiveConfig(tabId).humanize_speed, effectiveConfig(tabId).humanize_seed);
          const from = cursorByTab.get(tabId) || { x: Math.max(0, coordinate[0] - 200), y: Math.max(0, coordinate[1] - 150) };
          await dispatchPlan(tabId, humanize.planHover(s, from, { x: coordinate[0], y: coordinate[1] }), modifiers);
          return { content: [{ type: "text", text: `Hovered at (${coordinate[0]}, ${coordinate[1]})${hitNote}` }] };
        }
        await dispatchMouse(tabId, "mouseMoved", coordinate[0], coordinate[1], { modifiers });
        cursorByTab.set(tabId, { x: coordinate[0], y: coordinate[1] });
        // Let the page apply the hover state; Brave additionally needs a settle
        // window, Chrome doesn't.
        if (await isBrave()) await sleep(200);
        return { content: [{ type: "text", text: `Hovered at (${coordinate[0]}, ${coordinate[1]})${hitNote}` }] };


}

export async function act_type({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!args.text) return { content: [{ type: "text", text: "text is required for type action" }] };
        await ensureAttached(tabId);
        if (await humanizeOn(tabId)) {
          // Same key events as the default path below, but with human-shaped
          // inter-key timing instead of a flat interval.
          await dispatchPlan(tabId, humanize.planType(human(effectiveConfig(tabId).humanize_speed, effectiveConfig(tabId).humanize_seed), args.text));
          return { content: [{ type: "text", text: `Typed "${args.text.substring(0, 50)}${args.text.length > 50 ? "..." : ""}"` }] };
        }
        // Default path: emit real keydown/keyup around each character.
        //
        // Measured against the official Claude in Chrome on an instrumented
        // page: its `type` delivers a keydown+keyup per character with correct
        // `code` values. Insertion-only (bare insertText) delivered ZERO key
        // events, so pages that gate on keydown — search-as-you-type, key
        // validators, shortcut handlers — saw nothing. That was a parity gap,
        // not just a realism one, so key events are the default here too.
        //
        // rawKeyDown is the NON-text-producing variant: the character comes
        // from insertText alone, exactly once, so this cannot double-insert or
        // drop text. Characters with no real key identity (emoji, CJK) fall
        // back to insertText on its own rather than a fabricated keystroke.
        for (const char of args.text) {
          const d = humanize.keyDescriptorFor(char);
          if (d) {
            await cdp(tabId, "Input.dispatchKeyEvent", {
              type: "rawKeyDown",
              key: char,
              code: d.code,
              windowsVirtualKeyCode: d.keyCode || 0,
              modifiers: d.shift ? 8 : 0
            });
          }
          await cdp(tabId, "Input.insertText", { text: char });
          if (d) {
            await cdp(tabId, "Input.dispatchKeyEvent", {
              type: "keyUp",
              key: char,
              code: d.code,
              windowsVirtualKeyCode: d.keyCode || 0,
              modifiers: d.shift ? 8 : 0
            });
          }
          await sleep(10);
        }
        return { content: [{ type: "text", text: `Typed "${args.text.substring(0, 50)}${args.text.length > 50 ? "..." : ""}"` }] };


}
