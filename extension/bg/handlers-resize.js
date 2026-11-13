// Split out of extension/background.js — pure refactor, behavior unchanged.
import { cdp, ensureAttached } from "./cdp.js";
import { dbg } from "./debuglog.js";
import { isInGroup } from "./tabgroup.js";
import { sleep } from "./util.js";

export const handlersResize = {
  async resize_window(args) {
    const { width, height, tabId } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };

    await ensureAttached(tabId);
    const tab = await chrome.tabs.get(tabId);

    // A maximized or full-screen window ignores width/height, so it has to be
    // returned to "normal" FIRST, and the state change has to have landed before
    // the resize is issued: chrome.windows.update resolves when the request is
    // accepted, not when the window manager has applied it. Exiting macOS
    // full-screen is an animation, which is why this polls rather than retrying
    // once.
    //
    // This guard is precautionary — it has never been observed firing. It was
    // written to explain four resizes that left the viewport untouched, and that
    // explanation was wrong: the cause was that Chrome does not re-layout a tab
    // which is not the selected tab in its window (see the NOTE further down),
    // and the window measured "normal" every time. So the race described above
    // is plausible rather than demonstrated. It stays because the behaviour it
    // guards against is real — a maximized window genuinely does ignore a resize
    // — and because the whole block is a no-op on a window already normal.
    let win = await chrome.windows.get(tab.windowId);
    if (win.state !== "normal") {
      try {
        await chrome.windows.update(tab.windowId, { state: "normal" });
      } catch {}
      for (let i = 0; i < 20; i++) {
        await sleep(100);
        try {
          win = await chrome.windows.get(tab.windowId);
        } catch {
          break;
        }
        if (win.state === "normal") break;
      }
    }
    if (win.state !== "normal") {
      return {
        content: [
          {
            type: "text",
            text: `Could not resize: the window is ${win.state} and would not return to a normal state, so the window manager will ignore any size. Exit full screen and try again.`
          }
        ]
      };
    }
    // Record the window's own bounds either side of the call. The viewport
    // alone cannot distinguish "the window never moved" from "the window moved
    // but the page did not follow", and those have completely different causes.
    const before = { state: win.state, w: win.width, h: win.height, left: win.left, top: win.top };
    // The viewport before the call, so a window that moves while the page stays
    // put is detectable. That combination is not a window-manager behaviour at
    // all — it means something on our side has pinned the viewport — and it is
    // exactly what emulation used to do here.
    let vpBefore = null;
    try {
      const v0 = await cdp(tabId, "Runtime.evaluate", {
        expression: "JSON.stringify([innerWidth, innerHeight])",
        returnByValue: true
      });
      vpBefore = JSON.parse(v0.result.value);
    } catch {}
    let updateErr = null;
    try {
      await chrome.windows.update(tab.windowId, { width, height, state: "normal" });
    } catch (e) {
      updateErr = String(e && e.message).slice(0, 160);
    }
    // Give the window manager a moment to apply the size before measuring it,
    // for the same reason as above.
    await sleep(150);
    let after = null;
    try {
      const w2 = await chrome.windows.get(tab.windowId);
      after = { state: w2.state, w: w2.width, h: w2.height, left: w2.left, top: w2.top };
    } catch {}

    // A window resize and the page's re-layout are not the same event: the
    // window can report its new bounds while the renderer has not yet reflowed.
    // A fixed sleep here read the pre-resize viewport often enough to make
    // correct resizes report themselves as failures. Wait for the viewport to
    // actually move instead, then let it settle, and cap the wait so a resize
    // that genuinely changes nothing still returns promptly.
    const readViewport = async () => {
      try {
        const v = await cdp(tabId, "Runtime.evaluate", {
          expression: "JSON.stringify([innerWidth, innerHeight])",
          returnByValue: true
        });
        return JSON.parse(v.result.value);
      } catch {
        return null;
      }
    };
    const changedFromBefore = (v) =>
      v && vpBefore && (v[0] !== vpBefore[0] || v[1] !== vpBefore[1]);
    const settleDeadline = 900;
    let waited = 0;
    let last = await readViewport();
    while (waited < settleDeadline) {
      if (changedFromBefore(last)) {
        // Moved. One more read so a mid-reflow value is not what we report.
        await sleep(60);
        waited += 60;
        const settled = await readViewport();
        if (settled) last = settled;
        break;
      }
      await sleep(60);
      waited += 60;
      const next = await readViewport();
      if (next) last = next;
    }
    const settledViewport = last;
    dbg(
      "tool",
      `resize_window bounds ${before.w}x${before.h}(${before.state}) -> ${after ? `${after.w}x${after.h}(${after.state})` : "unknown"} requested ${width}x${height}${updateErr ? ` ERR ${updateErr}` : ""}`,
      { tab: tabId }
    );
    // Report what actually happened rather than echoing the request, and judge
    // the window against the WINDOW bounds — not the viewport, which is legitimately
    // ~100px shorter than the window it lives in because the browser's own chrome
    // takes that space. Comparing the two directly made every successful resize
    // look like a failure.
    const actual = settledViewport;

    const windowTook = after && Math.abs(after.w - width) <= 8 && Math.abs(after.h - height) <= 8;
    const windowMoved = after && (after.w !== before.w || after.h !== before.h);
    const pageFollowed =
      !vpBefore || !actual || actual[0] !== vpBefore[0] || actual[1] !== vpBefore[1];

    let note = "";
    if (!windowTook) {
      // The window itself did not reach the requested size: a window-manager call.
      note =
        ` — NOTE: requested ${width}x${height} but the window went ${before.w}x${before.h} -> ` +
        `${after ? `${after.w}x${after.h}` : "unknown"} (state ${after ? after.state : "?"}), so the ` +
        `window manager ${windowMoved ? "clamped" : "ignored"} the request. Full-screen, tiled, and ` +
        `snapped windows refuse resizes; on macOS, Stage Manager and split view do too, while still ` +
        `reporting state "normal".${updateErr ? ` The update call also errored: ${updateErr}` : ""}`;
    } else if (windowMoved && !pageFollowed) {
      // The window took the size but the page did not re-layout. Not the window
      // manager's doing — something is holding the viewport fixed on our side.
      // Gated on windowMoved so that asking for the size the window already has
      // (a legitimate no-op, where the viewport correctly does not change) is
      // not reported as a fault.
      note =
        ` — NOTE: the window resized to ${after.w}x${after.h} as requested, but the page's viewport ` +
        `stayed ${actual[0]}x${actual[1]} after waiting ${settleDeadline}ms for it to reflow. Chrome ` +
        `does not re-layout a tab that is not the SELECTED tab in its window, and this tab is not ` +
        `selected, so the page keeps the size it had when it was last displayed. Call set_tab_focus ` +
        `on this tab first if the new size actually needs to reach the page. Note that the page ` +
        `cannot tell you this itself: focus emulation makes it report visibilityState "visible" and ` +
        `hasFocus() true either way. Until then, anything measured at this "new size" is really ` +
        `still the old one.`;
    }
    return {
      content: [
        {
          type: "text",
          text: `Resized window to ${width}x${height}${after ? ` (window is ${after.w}x${after.h})` : ""}; ` +
            `viewport is now ${actual ? `${actual[0]}x${actual[1]}` : "unknown"}.${note}`
        }
      ]
    };
  },

};
