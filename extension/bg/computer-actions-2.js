// Split out of extension/background.js — pure refactor, behavior unchanged.
import * as humanize from "../humanize/index.js";
import { cdp, ensureAttached, withTimeout } from "./cdp.js";
import { act_diag_input, act_double_click, act_hover, act_left_click, act_right_click, act_screenshot, act_triple_click, act_type } from "./computer-actions.js";
import { dispatchPlan, effectiveConfig, humanizeOn } from "./config.js";
import { sendContentMessage } from "./cs-message.js";
import { isBrave } from "./detect.js";
import { human } from "./human.js";
import { parseKeyCombo } from "./keys.js";
import { dispatchMouse, sendMouseEvent } from "./mouse.js";
import { takeScreenshot, writeScreenshotToDisk } from "./screenshot.js";
import { cursorByTab } from "./state.js";
import { sleep } from "./util.js";

export async function act_key({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!args.text) return { content: [{ type: "text", text: "text is required for key action" }] };
        await ensureAttached(tabId);
        const repeat = Math.min(args.repeat || 1, 100);
        // Parse space-separated key combos
        const keys = args.text.split(" ").filter(Boolean);
        for (let r = 0; r < repeat; r++) {
          for (const keyStr of keys) {
            const { key, modifiers: keyMod } = parseKeyCombo(keyStr);
            const resolvedKey = key.length === 1 ? key : key;
            await cdp(tabId, "Input.dispatchKeyEvent", {
              type: "keyDown",
              key: resolvedKey,
              code: resolvedKey.length === 1 ? `Key${resolvedKey.toUpperCase()}` : resolvedKey,
              modifiers: keyMod,
              windowsVirtualKeyCode: resolvedKey.charCodeAt ? resolvedKey.charCodeAt(0) : 0,
            });
            await cdp(tabId, "Input.dispatchKeyEvent", {
              type: "keyUp",
              key: resolvedKey,
              code: resolvedKey.length === 1 ? `Key${resolvedKey.toUpperCase()}` : resolvedKey,
              modifiers: keyMod,
            });
            // Brave's debugger pipeline needs a settle window between key
            // events; Chrome acks instantly, so the sleep is pure latency there.
            if (await isBrave()) await sleep(30);
          }
        }
        return { content: [{ type: "text", text: `Pressed ${repeat} key${repeat > 1 ? "s" : ""}: ${args.text}` }] };


}

export async function act_scroll({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!coordinate) return { content: [{ type: "text", text: "coordinate is required for scroll" }] };
        const dir = args.scroll_direction || "down";
        const amount = Math.min(args.scroll_amount || 3, 10);
        const deltaX = dir === "left" ? -amount * 100 : dir === "right" ? amount * 100 : 0;
        const deltaY = dir === "up" ? -amount * 100 : dir === "down" ? amount * 100 : 0;
        if (await humanizeOn(tabId)) {
          // Humanize the APPROACH, deliver the scroll with the same single
          // wheel event the non-humanized path uses.
          //
          // Two attempts at decomposing the scroll both broke the invariant
          // that humanization must not change outcomes, in opposite ways:
          //   - many wheel ticks spread over time: the page scrolled under the
          //     stationary cursor, a nested scrollable slid into place and ate
          //     the rest (page moved 89-109px instead of 400px). Capping the
          //     burst under 200ms did not help.
          //   - Input.synthesizeScrollGesture: fixed the targeting (the nested
          //     box stayed at 0) but its yDistance is literal pixels, while a
          //     wheel event's deltaY goes through the browser's own scaling —
          //     the same request scrolled 600px humanized vs 400px plain.
          //     Matching them would mean hardcoding a platform-specific factor.
          //
          // So the wheel event stays exactly as it is, and what gets humanized
          // is the cursor arriving at the scroll position and the beat before
          // and after. A real mouse wheel is a chunky discrete device anyway;
          // the smooth part of a scroll is the page's own animation, not the
          // input. Correctness first: an agent asking to scroll one screen must
          // land in the same place whether or not humanization is on.
          const s = human(effectiveConfig(tabId).humanize_speed, effectiveConfig(tabId).humanize_seed);
          const from = cursorByTab.get(tabId);
          if (from && (from.x !== coordinate[0] || from.y !== coordinate[1])) {
            await dispatchPlan(tabId, humanize.planHover(s, from, { x: coordinate[0], y: coordinate[1] }), modifiers);
          }
          await sendMouseEvent(tabId, {
            type: "mouseWheel", x: coordinate[0], y: coordinate[1], deltaX, deltaY, modifiers
          }, { awaitAck: false });
          await sleep(humanize.thinkDelay(s, 0.5));
        } else {
        await sendMouseEvent(tabId, {
          type: "mouseWheel",
          x: coordinate[0],
          y: coordinate[1],
          deltaX,
          deltaY,
          modifiers,
        }, { awaitAck: false });
        }
        // Let the compositor repaint before the confirmation screenshot; Chrome
        // repaints fast, Brave needs a longer settle window.
        await sleep((await isBrave()) ? 300 : 100);
        // The scroll already happened; the confirmation screenshot is best-effort.
        // On a heavy page still re-rendering after the scroll, the capture can
        // block, so bound it and degrade to a text-only result rather than
        // stalling the whole scroll (and the agent's retries) to the 60s cap.
        const scrollContent = [
          { type: "text", text: `Scrolled ${dir} by ${amount} ticks at (${coordinate[0]}, ${coordinate[1]})${hitNote}` },
        ];
        try {
          const { base64 } = await withTimeout(takeScreenshot(tabId), 6000, "scroll screenshot");
          scrollContent.push({ type: "image", data: base64, mimeType: "image/jpeg" });
        } catch (e) {
          scrollContent[0].text += ` (post-scroll screenshot unavailable: ${e.message}; take a screenshot to see the result)`;
        }
        return { content: scrollContent };


}

export async function act_scroll_to({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!coordinate && !args.ref) return { content: [{ type: "text", text: "coordinate or ref is required for scroll_to" }] };
        if (args.ref) {
          await sendContentMessage(tabId, {
            type: "scrollToRef",
            ref: args.ref,
          });
        }
        // Scroll target element into view via JS
        if (coordinate) {
          await cdp(tabId, "Runtime.evaluate", {
            expression: `window.scrollTo(${coordinate[0]}, ${coordinate[1]})`,
          });
        }
        // Let the page repaint the scroll; Chrome is fast, Brave slower.
        await sleep((await isBrave()) ? 300 : 100);
        return { content: [{ type: "text", text: `Scrolled to target` }] };


}

export async function act_wait({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        const duration = Math.min(args.duration || 1, 30);
        await sleep(duration * 1000);
        return { content: [{ type: "text", text: `Waited for ${duration} second${duration !== 1 ? "s" : ""}` }] };


}

export async function act_left_click_drag({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!args.start_coordinate || !coordinate) {
          return { content: [{ type: "text", text: "start_coordinate and coordinate are required for left_click_drag" }] };
        }
        const [sx, sy] = args.start_coordinate;
        const [ex, ey] = coordinate;
        if (await humanizeOn(tabId)) {
          const s = human(effectiveConfig(tabId).humanize_speed, effectiveConfig(tabId).humanize_seed);
          const from = cursorByTab.get(tabId) || { x: sx, y: sy };
          await dispatchPlan(tabId, humanize.planDrag(s, from, { x: sx, y: sy }, { x: ex, y: ey }), modifiers);
          return { content: [{ type: "text", text: `Dragged from (${sx}, ${sy}) to (${ex}, ${ey})${hitNote}` }] };
        }
        await dispatchMouse(tabId, "mouseMoved", sx, sy, { modifiers });
        if (await isBrave()) await sleep(50);
        await dispatchMouse(tabId, "mousePressed", sx, sy, { button: "left", modifiers });
        if (await isBrave()) await sleep(50);
        // Move in steps
        const steps = 10;
        for (let i = 1; i <= steps; i++) {
          const mx = sx + ((ex - sx) * i) / steps;
          const my = sy + ((ey - sy) * i) / steps;
          await dispatchMouse(tabId, "mouseMoved", mx, my, { modifiers });
          if (await isBrave()) await sleep(20);
        }
        await dispatchMouse(tabId, "mouseReleased", ex, ey, { button: "left", modifiers });
        return { content: [{ type: "text", text: `Dragged from (${sx}, ${sy}) to (${ex}, ${ey})${hitNote}` }] };


}

export async function act_zoom({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        if (!args.region || args.region.length !== 4) {
          return { content: [{ type: "text", text: "region [x0, y0, x1, y1] is required for zoom" }] };
        }
        // Capture full screenshot then crop region
        const { base64: fullBase64 } = await takeScreenshot(tabId);
        // save_to_disk: write the captured image to disk and report the path.
        // Best-effort — never fails the zoom.
        let zoomSaveNote = "";
        if (args.save_to_disk) {
          try {
            const path = await writeScreenshotToDisk(fullBase64);
            zoomSaveNote = `\nSaved to disk: ${path}`;
          } catch (e) {
            zoomSaveNote = `\n(Unable to save to disk: ${e.message})`;
          }
        }
        // Return the full screenshot with region info — client can crop
        return {
          content: [
            { type: "text", text: `Zoom region: [${args.region.join(", ")}]${zoomSaveNote}` },
            { type: "image", data: fullBase64, mimeType: "image/jpeg" },
          ],
        };


}

export async function act_default({action, args, tabId, coordinate, modifiers, refCovering, hitNote}) {
        return { content: [{ type: "text", text: `Unknown computer action: ${action}` }] };
}

const COMPUTER_CASES = {
  screenshot: act_screenshot,
  left_click: act_left_click,
  diag_input: act_diag_input,
  right_click: act_right_click,
  double_click: act_double_click,
  triple_click: act_triple_click,
  hover: act_hover,
  type: act_type,
  key: act_key,
  scroll: act_scroll,
  scroll_to: act_scroll_to,
  wait: act_wait,
  left_click_drag: act_left_click_drag,
  zoom: act_zoom
};

export function computerSwitch(ctx) {
  const fn = COMPUTER_CASES[ctx.action] || act_default;
  return fn(ctx);
}
