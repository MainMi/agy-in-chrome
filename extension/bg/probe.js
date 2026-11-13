// Split out of extension/background.js — pure refactor, behavior unchanged.
import { sendContentMessage } from "./cs-message.js";

// --- What a coordinate-based action actually landed on -----------------------
//
// A dispatch always "succeeds": the events go out whether or not anything is
// there to receive them. So a perfect hit, a click into empty space, and a
// click swallowed by a transparent overlay all used to return the identical
// `Clicked at (x, y)` and nothing else — the caller could not tell them apart
// without instrumenting the page itself. Every click-accuracy bug found so far
// was invisible for exactly this reason.
//
// Resolving the point through the content script (isolated world) lets the
// answer include the ref of whatever is there, in the same ref space that
// read_page and find hand out. Best-effort throughout: this is an observability
// aid, so a failure here must never fail the action it is describing.
// Probe what is at a point. Split into three pieces on purpose: the probe, the
// full descriptor, and the (usually empty) response note.
//
// The tool response is deliberately silent when a click lands cleanly, because
// annotating every successful click would be noise on the overwhelmingly common
// path. But "omitted from the response" must not mean "discarded": the debug
// stream is where everything the response leaves out is supposed to end up, so
// the descriptor is computed once and always recorded, whatever the response
// chooses to say.
export async function probeHit(tabId, x, y) {
  try {
    const resp = await sendContentMessage(tabId, { type: "describePoint", x, y });
    const r = resp && resp.result;
    return r ? { ok: true, r } : { ok: false, err: "content script returned no result" };
  } catch (e) {
    return { ok: false, err: String(e && e.message).slice(0, 120) };
  }
}

// Compact one-line descriptor for the debug stream. Always produced — including
// on the success path, where the response itself says nothing.
export function formatHit(p) {
  if (!p.ok) {
    // A failed probe is NOT a clean hit. Saying so explicitly is the whole
    // point: silence here would be indistinguishable from success.
    return `PROBE FAILED (${p.err}) — nothing is known about what is at this point`;
  }
  const r = p.r;
  const vp = r.viewport ? r.viewport.join("x") : "?";
  if (!r.hit) {
    return r.outside
      ? `NOTHING — point lies outside the ${vp} viewport`
      : `NOTHING — no element at that point in the ${vp} viewport`;
  }
  const h = r.hit;
  const a = h.attrs || {};
  const id = a.id ? `#${a.id}` : "";
  const cls = h.cls ? `.${h.cls}` : "";
  const extra = [];
  if (a["data-testid"] || a["data-test"]) extra.push(`testid=${a["data-testid"] || a["data-test"]}`);
  if (a.role) extra.push(`role=${a.role}`);
  if (a["aria-label"]) extra.push(`aria="${a["aria-label"]}"`);
  if (a.name) extra.push(`name=${a.name}`);
  if (a.type) extra.push(`type=${a.type}`);
  if (h.ref) extra.push(h.ref);
  const text = h.text ? ` "${h.text}"` : "";
  return `<${h.tag}${id}${cls}>${text}${extra.length ? " " + extra.join(" ") : ""}` +
    `${r.bare ? " (page background)" : ""} in ${vp} viewport`;
}

// The response note. Silent on success; only the two cases a caller cannot
// otherwise detect get a word. A failed probe stays silent here too — it is a
// fault in the instrument, not a finding about the click, and it is recorded in
// the debug stream instead of being guessed at in the result.
export function hitNote_(p) {
  if (!p.ok) return "";
  const r = p.r;
  if (r.hit && !r.bare && !r.deadLabel) return "";
  const vp = r.viewport ? `${r.viewport[0]}x${r.viewport[1]}` : "the";
  // A label with no activatable control and no interactive ancestor: browsers
  // forward activation only for a label actually wired to a live control, so
  // nothing native is guaranteed to receive this click. It may still be caught
  // by a delegated handler we can't see, so warn rather than claim it failed.
  if (r.deadLabel) {
    return ` — WARNING: landed on a <label> whose control is missing or disabled, so the click may not have activated the widget it labels. Pass the control's ref instead of raw coordinates if that widget was intended.`;
  }
  if (!r.hit) {
    return r.outside
      ? ` — WARNING: nothing received this. The point is outside the ${vp} viewport, so it landed on no element. Pass the element's ref instead of raw coordinates and it will be scrolled into view automatically.`
      : ` — WARNING: no element at that point in the ${vp} viewport, so nothing received this.`;
  }
  return ` — WARNING: landed on <${r.hit.tag}> (page background), not on any element. Pass the element's ref instead of raw coordinates and it will be scrolled into view automatically.`;
}

