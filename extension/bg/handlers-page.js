// Split out of extension/background.js — pure refactor, behavior unchanged.
import { cdp, ensureAttached } from "./cdp.js";
import { sendContentMessage } from "./cs-message.js";
import { isInGroup } from "./tabgroup.js";
import { recordTiming } from "./timing.js";

export const handlersPage = {
  async read_page(args) {
    const { tabId } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };

    const resp = await sendContentMessage(tabId, {
      type: "generateAccessibilityTree",
      options: {
        filter: args.filter,
        depth: args.depth,
        max_chars: args.max_chars,
        ref_id: args.ref_id,
      },
    });

    let tree = resp?.result || "Error: Could not generate accessibility tree";
    // Append viewport dimensions so AGY knows the coordinate space
    try {
      await ensureAttached(tabId);
      const vp = await cdp(tabId, "Runtime.evaluate", {
        expression: "window.innerWidth + 'x' + window.innerHeight",
      });
      if (vp?.result?.value) tree += `\n\nViewport: ${vp.result.value}`;
    } catch {}
    return { content: [{ type: "text", text: tree }] };
  },

  async get_page_text(args) {
    const { tabId } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };

    const resp = await sendContentMessage(tabId, { type: "getPageText" });
    if (!resp?.result) return { content: [{ type: "text", text: "Error: Could not extract page text" }] };

    try {
      const data = JSON.parse(resp.result);
      return {
        content: [
          {
            type: "text",
            text: `Title: ${data.title}\nURL: ${data.url}\nSource: <${data.sourceTag}>\n\n${data.text}`,
          },
        ],
      };
    } catch {
      return { content: [{ type: "text", text: resp.result }] };
    }
  },

  async find(args) {
    const { query, tabId } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };

    const resp = await sendContentMessage(tabId, { type: "findElements", query });
    const results = resp?.result || [];

    if (results.length === 0) {
      return { content: [{ type: "text", text: `No elements found matching "${query}"` }] };
    }

    let text = `Found ${results.length} element(s) matching "${query}":\n\n`;
    let anyOff = false;
    for (const r of results) {
      text += `[${r.ref}] ${r.role} "${r.name}" at (${r.coordinates[0]}, ${r.coordinates[1]})`;
      if (r.offViewport) {
        anyOff = true;
        text += ` [OFF-VIEWPORT]`;
      }
      text += `\n`;
    }
    if (anyOff) {
      // Handing out coordinates that cannot be clicked is how a silent miss
      // starts: the click dispatches fine and lands on the document root.
      text +=
        `\nNote: entries marked [OFF-VIEWPORT] are scrolled out of view. Clicking their ` +
        `coordinates would land on the page background, not the element. Bring one into ` +
        `view first (computer scroll_to with its ref, or scroll its container), then re-run ` +
        `find to get fresh coordinates.\n`;
    }

    return { content: [{ type: "text", text }] };
  },

  async form_input(args) {
    const { ref, value, tabId } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };

    const resp = await sendContentMessage(tabId, { type: "setFormValue", ref, value });
    const result = resp?.result;

    if (result?.error) return { content: [{ type: "text", text: `Error: ${result.error}` }] };
    return { content: [{ type: "text", text: `Set ${ref} to "${value}". Result: ${JSON.stringify(result)}` }] };
  },

  async javascript_tool(args) {
    const { text, tabId } = args;
    const tIn = Date.now();
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };

    await ensureAttached(tabId);
    try {
      const tEval = Date.now();
      const result = await cdp(tabId, "Runtime.evaluate", {
        expression: text,
        returnByValue: true,
        awaitPromise: true,
      });
      // preMs = group check + debugger attach; evalMs = the evaluate alone.
      // The split is the whole point: it separates "the renderer serviced the
      // task late" from every other stage of the pipe.
      recordTiming({ t: tIn, tool: "javascript_tool", tab: tabId,
                     preMs: tEval - tIn, evalMs: Date.now() - tEval,
                     bytes: (text || "").length });

      if (result.exceptionDetails) {
        return {
          content: [{ type: "text", text: `Error: ${result.exceptionDetails.text || JSON.stringify(result.exceptionDetails)}` }],
        };
      }

      const val = result.result;
      if (val.type === "undefined") return { content: [{ type: "text", text: "undefined" }] };
      return {
        content: [{ type: "text", text: val.value !== undefined ? JSON.stringify(val.value) : val.description || String(val) }],
      };
    } catch (e) {
      return { content: [{ type: "text", text: `Error: ${e.message}` }] };
    }
  },

  // Read the per-call timing ring (live + storage.session backlog from before
  // any worker restart) plus a live snapshot of every group tab's scheduling-
  // relevant state. The snapshot is what turns a timing anomaly into a
  // diagnosis: it says which tabs were active/audible/discarded/frozen and
  // what state their windows were in while the quantum was being paid.
};
