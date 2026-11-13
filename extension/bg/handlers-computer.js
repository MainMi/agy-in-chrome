// Split out of extension/background.js — pure refactor, behavior unchanged.
import { computerSwitch } from "./computer-actions-2.js";
import { resolveRefToCoordinates } from "./cs-message.js";
import { dbg } from "./debuglog.js";
import { parseModifierString } from "./keys.js";
import { formatHit, hitNote_, probeHit } from "./probe.js";
import { isInGroup } from "./tabgroup.js";

export const handlersComputer = {
  async computer(args) {
    const { action, tabId } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };

    let coordinate = args.coordinate;
    // Resolve ref to coordinates if provided. This scrolls the element into
    // view first: coordinates are viewport-relative, so an element that is off
    // screen has coordinates no dispatch can reach, and the click would land on
    // the document root instead of the thing that was named.
    let refCovering = null;
    if (args.ref && !coordinate) {
      const res = await resolveRefToCoordinates(tabId, args.ref);
      if (!res) return { content: [{ type: "text", text: `Could not resolve ref "${args.ref}" to coordinates. The page may have changed — re-run read_page or find for a fresh ref.` }] };
      if (!res.reachable) {
        return { content: [{ type: "text", text: `Could not bring ref "${args.ref}" into view — it is still outside the viewport after scrolling, so a click there would land on the page background rather than the element. It may be inside a container that needs scrolling separately, or hidden.` }] };
      }
      coordinate = [res.x, res.y];
      refCovering = res.covering;
      if (res.scrolledFrom) {
        // The coordinates just changed underneath the caller. Recording it is
        // what stops a reader of the log concluding no scroll took place.
        dbg(
          "hit",
          `${args.ref} scrolled into view: (${res.scrolledFrom[0]},${res.scrolledFrom[1]}) -> (${res.x},${res.y})`,
          { tab: tabId }
        );
      }
    }

    const modifiers = parseModifierString(args.modifiers);

    // Probe BEFORE dispatching: the action itself can change what is under the
    // point, so an after-the-fact test would describe the consequence rather
    // than the target. For a drag the meaningful point is where the grab
    // happens, not where it is released.
    const HIT_PROBED = ["left_click", "right_click", "double_click", "triple_click", "hover", "scroll"];
    let hitNote = "";
    if (args.ref && coordinate) {
      // Resolving the ref already scrolled it into view and hit-tested the
      // result, so there is nothing left to check — only interception is worth
      // mentioning, and it is deliberately not auto-corrected: a person
      // clicking there would hit the same thing.
      if (refCovering) {
        hitNote = ` — NOTE: <${args.ref}> is covered at that point by ${refCovering}, which received this instead.`;
        dbg("hit", `${args.ref} @(${coordinate[0]},${coordinate[1]}) COVERED BY ${refCovering}`, { tab: tabId });
      } else {
        dbg("hit", `${args.ref} @(${coordinate[0]},${coordinate[1]}) reachable`, { tab: tabId });
      }
    } else if (HIT_PROBED.includes(action) && coordinate) {
      const probe = await probeHit(tabId, coordinate[0], coordinate[1]);
      hitNote = hitNote_(probe);
      dbg("hit", `@(${coordinate[0]},${coordinate[1]}) ${formatHit(probe)}`, { tab: tabId, x: coordinate[0], y: coordinate[1] });
    } else if (action === "left_click_drag" && args.start_coordinate) {
      const probe = await probeHit(tabId, args.start_coordinate[0], args.start_coordinate[1]);
      hitNote = hitNote_(probe);
      dbg("hit", `drag start @(${args.start_coordinate[0]},${args.start_coordinate[1]}) ${formatHit(probe)}`,
          { tab: tabId, x: args.start_coordinate[0], y: args.start_coordinate[1] });
    }

    return computerSwitch({ action, args, tabId, coordinate, modifiers, refCovering, hitNote });
    return computerSwitch({ action, args, tabId, coordinate, modifiers, refCovering, hitNote });
  },
};
