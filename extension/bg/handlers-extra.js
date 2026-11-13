// Split out of extension/background.js — pure refactor, behavior unchanged.
import { DEBUG_MAX, debugBootedAt, debugLog } from "./debuglog.js";
import { detectBrowser } from "./detect.js";
import { SWITCH_RELEASE_MS, stopHeartbeat } from "./native.js";
import { state } from "./state.js";

export const handlersExtra = {
  async switch_browser(args) {
    const current = await detectBrowser();
    // Release AFTER this reply is delivered — it goes out over the very native
    // port we are about to drop. Suspending reconnect lets a target browser
    // whose extension is enabled bind the shared runtime and become primary;
    // if none takes over, this browser reconnects when the window elapses.
    setTimeout(() => {
      state.suspendReconnectUntil = Date.now() + SWITCH_RELEASE_MS;
      if (state.nativePort) {
        try { state.nativePort.disconnect(); } catch (e) {}
        state.nativePort = null;
        stopHeartbeat();
      }
    }, 300);
    return {
      content: [{
        type: "text",
        text:
          `Releasing the connection from ${current}. Enable this extension in the ` +
          `target browser (no restart needed) — for the next ~${SWITCH_RELEASE_MS / 1000}s it can take over ` +
          `the shared runtime automatically. Only one browser drives automation at a ` +
          `time. If nothing takes over, ${current} reconnects when the window elapses. ` +
          `Re-run tabs_context_mcp after a few seconds to confirm the active browser.`,
      }],
    };
  },

  async update_plan(args) {
    const { domains, approach } = args;
    let text = `Plan:\n\nDomains: ${domains.join(", ")}\n\nApproach:\n`;
    for (const step of approach) {
      text += `- ${step}\n`;
    }
    text += "\nPlan auto-approved (no permission restrictions in this extension).";
    return { content: [{ type: "text", text }] };
  },

  async debug(args) {
    const limit = Math.min(Math.max(Number(args?.limit) || 100, 1), DEBUG_MAX);
    const kind = args?.kind;
    const filter = args?.filter;
    const tabId = args?.tabId;
    const sinceMs = Number(args?.since_ms) || 0;
    const now = Date.now();

    let re = null;
    let reErr = "";
    if (filter) {
      try {
        re = new RegExp(filter, "i");
      } catch (e) {
        // Fall back to substring rather than failing the call: a debug tool
        // that errors on its own input is useless exactly when it is needed.
        reErr = ` (filter "${filter}" is not valid regex — matched as plain text)`;
      }
    }

    let rows = debugLog;
    const total = rows.length;
    if (sinceMs) rows = rows.filter((e) => now - e.t <= sinceMs);
    if (kind) rows = rows.filter((e) => e.kind === kind);
    if (tabId !== undefined && tabId !== null) rows = rows.filter((e) => e.tab === tabId);
    if (filter) {
      rows = rows.filter((e) => {
        const hay = `${e.kind} ${e.detail} ${e.err || ""}`;
        return re ? re.test(hay) : hay.toLowerCase().includes(String(filter).toLowerCase());
      });
    }
    const matched = rows.length;
    rows = rows.slice(-limit);

    // Everything the reader needs to know about what is NOT here. Silence in a
    // debug stream must never be mistaken for silence in the system.
    const ageS = Math.round((now - debugBootedAt) / 1000);
    const head = [
      `OCIC debug — ${rows.length} shown of ${matched} matching, ${total} in buffer${reErr}`,
      `Buffer keeps the most recent ${DEBUG_MAX} events${state.debugDropped ? `; ${state.debugDropped} older event(s) have been DROPPED` : ""}.`,
      `Recording started ${ageS}s ago (service worker start). NOTHING before that is in here — MV3 evicts the worker, which clears the buffer, so an empty or short log may mean the worker restarted rather than that nothing happened.`
    ];
    if (!rows.length) {
      head.push("", "No events matched. If you expected some, check the window above before concluding the action did not occur.");
      return { content: [{ type: "text", text: head.join("\n") }] };
    }

    const t0 = rows[0].t;
    const lines = rows.map((e) => {
      const rel = `+${String(e.t - t0).padStart(6)}ms`;
      const ms = e.ms !== undefined ? ` (${e.ms}ms)` : "";
      const tab = e.tab !== undefined ? ` tab=${e.tab}` : "";
      const err = e.err ? `  ERR: ${e.err}` : "";
      return `${rel}  ${e.kind.padEnd(5)} ${e.detail}${ms}${tab}${err}`;
    });

    // Timing roll-up: the question after "what happened" is nearly always
    // "what was slow", and it is cheap to answer here.
    const byKind = {};
    for (const e of rows) {
      if (typeof e.ms !== "number") continue;
      const k = e.detail.split(" ")[0];
      (byKind[k] = byKind[k] || []).push(e.ms);
    }
    const slow = Object.entries(byKind)
      .map(([k, v]) => ({ k, n: v.length, total: v.reduce((a, b) => a + b, 0), max: Math.max(...v) }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 6)
      .map((r) => `  ${r.k} x${r.n}: ${r.total}ms total, ${r.max}ms slowest`);

    const span = rows[rows.length - 1].t - t0;
    const out = [
      ...head,
      `Window shown spans ${span}ms.`,
      "",
      ...lines
    ];
    if (slow.length) out.push("", "Slowest by total time:", ...slow);
    if (args?.clear) {
      debugLog.length = 0;
      state.debugDropped = 0;
      out.push("", "Buffer cleared.");
    }
    return { content: [{ type: "text", text: out.join("\n") }] };
  },

};
