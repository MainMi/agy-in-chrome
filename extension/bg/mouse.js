// Split out of extension/background.js — pure refactor, behavior unchanged.
import * as humanize from "../humanize/index.js";
import { CDP_TIMEOUT_MS, ensureAttached, withTimeout } from "./cdp.js";
import { dispatchPlan, effectiveConfig, humanizeOn } from "./config.js";
import { dbg } from "./debuglog.js";
import { isBrave } from "./detect.js";
import { human } from "./human.js";
import { cursorByTab } from "./state.js";
import { sleep } from "./util.js";

// --- Mouse helpers ---
// Brave withholds the debugger ack for synthesized mouse events (a constant
// ~5s flush for move/press/release; mouseWheel is never acked at all) while
// applying the event itself immediately. Chrome acks instantly. The ack
// carries no data we need, so give real protocol errors a short grace window
// and then proceed; a late ack (or late failure) is logged, not awaited.
// Brave's debugger input pipeline (verified empirically, 2026-07-15):
// the FIRST Input.dispatchMouseEvent of a burst acks after a constant ~5s
// cold-start; commands issued while an earlier one is still un-acked are
// NOT queued for press/release types, they are silently DROPPED (mouseMoved
// queues and applies late; mousePressed/Released vanish). mouseWheel is
// never acked at all but its scroll effect applies immediately.
// Consequences: move/press/release MUST be dispatched serially with each
// ack awaited (correctness over speed); ONLY mouseWheel may use a bounded
// race, because its effect is verified to apply without the ack and nothing
// depends on it inside the same action. Chrome acks everything instantly,
// so the awaits cost nothing there.
const INPUT_ACK_WAIT_MS = 250; // Brave: bounded wait for fire-and-forget (mouseWheel never acks)
const CHROME_INPUT_ACK_WAIT_MS = 50; // Chrome: acks instantly, a short window suffices

export async function sendMouseEvent(tabId, params, { awaitAck = true, noAck = false } = {}) {
  await ensureAttached(tabId);
  const t0 = Date.now();
  dbg("input", `${params.type}(${params.x},${params.y})${params.deltaY ? ` dy=${params.deltaY}` : ""}${noAck ? " noack" : awaitAck ? "" : " raced"}`,
      { tab: tabId, x: params.x, y: params.y });
  const send = withTimeout(
    chrome.debugger.sendCommand({ tabId }, "Input.dispatchMouseEvent", params),
    CDP_TIMEOUT_MS,
    "CDP Input.dispatchMouseEvent",
  );
  if (noAck) {
    // Queue it and move on WITHOUT waiting for the ack at all.
    //
    // This exists for humanized motion, where the ack round-trip — not the
    // modelled timing — is the real cost: a natural click plans ~0.8s of
    // delays but measured ~3.9s in the browser, because each of ~45 moves
    // waited ~85ms for its ack. Cursor moves need no ack (they apply
    // regardless, and the plan carries its own pacing in sleep steps), so
    // waiting only buys latency. Press/release still use the awaited path,
    // since those ARE dropped if issued while an earlier command is un-acked.
    // A failure arriving after we stopped waiting is precisely the case where
    // the stream would otherwise show a clean dispatch for an event that never
    // landed. Record it against the coordinates it was meant for.
    send.catch((e) => {
      dbg("input", `${params.type}(${params.x},${params.y}) FAILED AFTER SEND (noack) — nothing received it`,
          { tab: tabId, x: params.x, y: params.y, err: String(e && e.message).slice(0, 120) });
      console.warn("Input.dispatchMouseEvent (noAck):", e.message);
    });
    return;
  }
  if (awaitAck) {
    await send; // serial-await path (required on Brave: press/release dropped if not awaited)
    return;
  }
  // Fire-and-forget path (mouseWheel, and Chrome mouseMoved): wait for the ack
  // only up to a bounded window so Brave's ~5s-stalled acks don't block us.
  // Brave needs the full window; Chrome acks instantly, so a short one suffices.
  const ackWaitMs = (await isBrave()) ? INPUT_ACK_WAIT_MS : CHROME_INPUT_ACK_WAIT_MS;
  await Promise.race([
    send.catch((e) => {
      dbg("input", `${params.type}(${params.x},${params.y}) LATE FAILURE — dispatch did not take`,
          { tab: tabId, x: params.x, y: params.y, err: String(e && e.message).slice(0, 120) });
      console.warn("Input.dispatchMouseEvent late ack/failure:", e.message);
    }),
    sleep(ackWaitMs),
  ]);
}

export async function dispatchMouse(tabId, type, x, y, opts = {}) {
  if (opts.noAck) {
    await sendMouseEvent(
      tabId,
      { type, x, y, button: opts.button || "left", clickCount: opts.clickCount || 1, modifiers: opts.modifiers || 0 },
      { noAck: true }
    );
    return;
  }
  // Chrome acks instantly and applies immediately, so the mouseMoved "move"
  // sub-event needs no ack and can be fire-and-forget (awaitAck:false). Brave
  // must keep the serial-await path (its moves silently drop if not awaited).
  const awaitAck = opts.awaitAck ?? (type === "mouseMoved" ? await isBrave() : true);
  await sendMouseEvent(
    tabId,
    {
      type,
      x,
      y,
      button: opts.button || "left",
      clickCount: opts.clickCount || 1,
      modifiers: opts.modifiers || 0,
    },
    { awaitAck },
  );
}

export async function mouseClick(tabId, x, y, opts = {}) {
  const button = opts.button || "left";
  const clickCount = opts.clickCount || 1;
  const modifiers = opts.modifiers || 0;

  // Humanized: approach along a curved path from wherever this tab's cursor
  // actually is, land on the requested point, press/release with real dwell.
  if (await humanizeOn(tabId)) {
    const s = human(effectiveConfig(tabId).humanize_speed, effectiveConfig(tabId).humanize_seed);
    const from = cursorByTab.get(tabId) || { x: Math.max(0, x - 220), y: Math.max(0, y - 160) };
    await dispatchPlan(
      tabId,
      humanize.planClick(s, from, { x, y }, { button, clickCount, targetSize: opts.targetSize }),
      modifiers
    );
    return;
  }

  await dispatchMouse(tabId, "mouseMoved", x, y, { modifiers });
  // Brave's debugger pipeline needs a ~50ms settle window between dispatched
  // events (verified empirically); Chrome acks instantly, so the sleeps are
  // pure latency there and are dropped to keep clicks snappy.
  const brave = await isBrave();
  if (brave) await sleep(50);
  await dispatchMouse(tabId, "mousePressed", x, y, { button, clickCount, modifiers });
  if (brave) await sleep(50);
  await dispatchMouse(tabId, "mouseReleased", x, y, { button, clickCount, modifiers });
  cursorByTab.set(tabId, { x, y });
}
