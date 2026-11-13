// Small shared helpers for the options page modules — split out of
// options.js so both it and options-detail.js use one definition.

export function fmtTime(ms) {
  try { return new Date(ms).toLocaleString(); } catch { return String(ms); }
}
export function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
// Truncate with an explicit ellipsis so a cutoff is always visible; the full
// value lives in the detail popup.
export function trunc(s, n) {
  s = String(s ?? "");
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
// recording_id -> sorted { beh, cog }, so a clicked timeline item can be
// resolved to its full record for the popup.
export const traceCache = new Map();
