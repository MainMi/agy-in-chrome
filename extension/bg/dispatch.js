// Split out of extension/background.js — pure refactor, behavior unchanged.
import * as audit from "../audit/index.js";
import { argSummary, dbg, resultShape } from "./debuglog.js";
import { handlersComputer } from "./handlers-computer.js";
import { handlersConfig } from "./handlers-config.js";
import { handlersExtra } from "./handlers-extra.js";
import { handlersInspect } from "./handlers-inspect.js";
import { handlersMedia } from "./handlers-media.js";
import { handlersPage } from "./handlers-page.js";
import { handlersResize } from "./handlers-resize.js";
import { handlersTabs } from "./handlers-tabs.js";
import { sendError, sendResponse } from "./native.js";
import { recorder } from "./rec-state.js";
import { state } from "./state.js";
import { recordTiming } from "./timing.js";

const toolHandlers = Object.assign({}, handlersTabs, handlersComputer, handlersPage, handlersInspect, handlersResize, handlersMedia, handlersExtra, handlersConfig);

// --- Tool dispatch ---
export async function handleToolRequest(id, tool, args) {
  // recording_ack arrives from the MCP server when Claude confirms receipt of
  // a recording_complete event. Mark it delivered so stopRecording() can
  // report the "delivered to Claude Code" state (§4).
  if (tool === "recording_ack") {
    if (args && args.recording_id) recorder.deliveredIds.add(String(args.recording_id));
    sendResponse(id, { content: [{ type: "text", text: "ack received" }] });
    return;
  }

  const handler = toolHandlers[tool];
  if (!handler) {
    sendError(id, `Unknown tool: ${tool}`);
    return;
  }

  const t0 = Date.now();
  const label = tool === "computer" ? `computer.${args && args.action}` : tool;
  dbg("tool", `${label} <- ${argSummary(args)}`, { tab: args && args.tabId });

  // Attribute this action to the Claude Code session that asked for it. The
  // host namespaces every request as `h{clientId}_{id}` and we echo that id
  // back untouched, so the client is already identifiable here with no
  // protocol change on either side. Two sessions driving two tabs therefore
  // produce two independent audits rather than one interleaved mess.
  //
  // Awaited deliberately: the recorder must be attached BEFORE the action runs,
  // or the first action on a tab is the one action the replay is missing.
  if (audit.isEnabled()) {
    const clientId = (String(id).match(/^h(\d+)_/) || [])[1] ?? null;
    await audit
      .noteAction({
        clientId,
        tool,
        action: args && args.action,
        tabId: args && args.tabId,
        detail: argSummary(args),
        // Passed rather than imported so the audit module stays free of any
        // native-host coupling — the seam that keeps it foldable later.
        postToHost: (m) => {
          try {
            if (state.nativePort) state.nativePort.postMessage(m);
          } catch {}
        }
      })
      .catch(() => {});
  }
  try {
    const t0 = Date.now();
    const result = await handler(args);
    // Record the SHAPE of the reply, not the reply. Echoing the response text
    // here would make the stream a copy of what the caller already received,
    // which is worth nothing to them; what they cannot see is how long it took
    // and how much came back.
    dbg("tool", `${label} -> ${resultShape(result)}`, { tab: args && args.tabId, ms: Date.now() - t0 });
    // Upstream's separate per-call timing buffer, kept so its debug_timings tool
    // still reports. javascript_tool records its own richer entry (preMs/evalMs);
    // debug_timings reading the buffer should not pollute it.
    if (tool !== "javascript_tool" && tool !== "debug_timings") {
      recordTiming({ t: t0, tool, tab: args?.tabId, ms: Date.now() - t0 });
    }
    sendResponse(id, result);
  } catch (err) {
    dbg("tool", `${label} -> THREW`, { tab: args && args.tabId, ms: Date.now() - t0, err: String(err.message).slice(0, 160) });
    sendError(id, `${tool} failed: ${err.message}`);
  }
}

// ===========================================================================
// Imitation-learning recorder (NEEDS LIVE TESTING)
