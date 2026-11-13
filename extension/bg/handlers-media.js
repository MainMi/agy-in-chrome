// Split out of extension/background.js — pure refactor, behavior unchanged.
import { cdp, ensureAttached, ensureDomain } from "./cdp.js";
import { sendContentMessage } from "./cs-message.js";
import { nativeRequest } from "./native.js";
import { saveBundleToDisk } from "./rec-save.js";
import { ensureOffscreen, getApiKey } from "./rec-util.js";
import { screenshotStore } from "./state.js";
import { isInGroup } from "./tabgroup.js";

export const handlersMedia = {
  async upload_image(args) {
    const { imageId, tabId, ref, filename = "image.png" } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };
    if (!ref) {
      return { content: [{ type: "text", text: "upload_image requires 'ref' (element reference from read_page/find) identifying the target <input type=file>." }] };
    }

    const base64 = screenshotStore.get(imageId);
    if (!base64) {
      return { content: [{ type: "text", text: `Image ${imageId} not found. Take a screenshot first.` }] };
    }

    await ensureAttached(tabId);
    await ensureDomain(tabId, "DOM");

    // 1) Resolve the ref through the content-script channel (isolated world,
    //    where resolveRef lives), stamping a DOM attribute CDP can find. A
    //    main-world Runtime.evaluate can't see the isolated-world globals.
    const mark = await sendContentMessage(tabId, { type: "markElementForUpload", ref });
    if (!mark || !mark.ok) {
      return { content: [{ type: "text", text: `No element found for ref=${ref}. Re-run read_page/find to get a fresh ref.` }] };
    }
    if (!mark.isFileInput) {
      await sendContentMessage(tabId, { type: "unmarkElementForUpload" }).catch(() => {});
      return { content: [{ type: "text", text: `Target ref=${ref} is a <${mark.tag}>, not a file input.` }] };
    }

    // 2) Stage the screenshot bytes as a real temp file via the native host.
    //    The screenshot lives in-memory (base64), so setFileInputFiles needs a
    //    path on disk to attach.
    let tempPath;
    try {
      tempPath = await nativeRequest({ type: "write_temp_file", dataUrl: base64, filename });
    } catch (e) {
      await sendContentMessage(tabId, { type: "unmarkElementForUpload" }).catch(() => {});
      return { content: [{ type: "text", text: `Failed to stage temp file for ${imageId}: ${String(e && e.message)}` }] };
    }
    if (!tempPath) {
      await sendContentMessage(tabId, { type: "unmarkElementForUpload" }).catch(() => {});
      return { content: [{ type: "text", text: `Failed to stage temp file for ${imageId}.` }] };
    }

    // 3) Find the marked file input via CDP, then attach the staged file.
    try {
      const doc = await cdp(tabId, "DOM.getDocument", {});
      const q = await cdp(tabId, "DOM.querySelector", {
        nodeId: doc.root.nodeId,
        selector: "[data-ocic-upload-target]",
      });
      if (!q || !q.nodeId) {
        return { content: [{ type: "text", text: `Could not resolve the file input node for ref=${ref}.` }] };
      }
      await cdp(tabId, "DOM.setFileInputFiles", { nodeId: q.nodeId, files: [tempPath] });
    } finally {
      await sendContentMessage(tabId, { type: "unmarkElementForUpload" }).catch(() => {});
    }

    return { content: [{ type: "text", text: `Uploaded ${filename} (${imageId}) to the file input. Temp file: ${tempPath}` }] };
  },

  // Re-run a failed transcription for a saved recording. The offscreen doc
  // re-assembles the durable segments from IndexedDB and re-maps them onto the
  // shared clock; we then persist the patched trace.json on disk.
  async retranscribe_recording(args) {
    const { recording_id } = args;
    if (!recording_id)
      return { content: [{ type: "text", text: "recording_id is required." }] };

    const apiKey = await getApiKey();
    // The offscreen document owns the durable audio buffer; make sure it's alive
    // before asking it to retranscribe, or the message is dropped (res undefined).
    await ensureOffscreen();
    const res = await chrome.runtime.sendMessage({
      __ocic_offscreen: true,
      cmd: "retranscribe",
      recording_id,
      apiKey,
    });
    if (!res || !res.ok) {
      return { content: [{ type: "text", text: res?.error || "retranscription failed." }] };
    }

    // Persist the patched trace via the SAME disk-write path used at stop
    // (saveBundleToDisk -> save_recording -> native host), rather than a
    // bespoke retry-only write path. Reuse keeps the retry a thin re-run.
    const path = await saveBundleToDisk({
      recording_id,
      schema: res.trace?.schema || "v0",
      trace: res.trace,
    }).catch(() => null);
    const synopsis =
      `Recording ${recording_id} retranscribed: ${res.transcript_status}. ` +
      `${(res.cognitive || []).length} utterances. ` +
      (path ? `trace.json updated on disk (${path}).` : "WARNING: trace.json could not be written to disk.");
    return { content: [{ type: "text", text: synopsis }] };
  },

  async file_upload(args) {
    const { tabId, paths, ref } = args;
    if (!(await isInGroup(tabId))) return { content: [{ type: "text", text: `Tab ${tabId} is not in the MCP group.` }] };
    if (!Array.isArray(paths) || paths.length === 0 || !paths.every((p) => typeof p === "string" && p)) {
      return { content: [{ type: "text", text: "file_upload requires 'paths' — a non-empty array of absolute file paths that already exist on this machine." }] };
    }
    if (!ref || typeof ref !== "string") {
      return { content: [{ type: "text", text: "file_upload requires 'ref' — the element reference of an <input type=file> from read_page or find." }] };
    }

    await ensureAttached(tabId);
    await ensureDomain(tabId, "DOM");

    // Resolve the ref through the content-script channel (isolated world, where
    // resolveRef/__unblockedChrome live), which stamps a DOM attribute on the
    // element. CDP Runtime.evaluate runs in the page's MAIN world and can't see
    // the isolated-world globals, so we locate the element via that shared-DOM
    // attribute instead. Works for hidden file inputs too.
    const mark = await sendContentMessage(tabId, { type: "markElementForUpload", ref });
    if (!mark || !mark.ok) {
      return { content: [{ type: "text", text: `No element found for ref=${ref}. Re-run read_page/find to get a fresh ref.` }] };
    }
    if (!mark.isFileInput) {
      return { content: [{ type: "text", text: `Target ref=${ref} is a <${mark.tag}>, not a file input. Point at the <input type=file> element (read_page/find can locate hidden ones).` }] };
    }

    // The files are already on disk on the same machine as the browser, so pass
    // the real paths straight to CDP — no temp staging needed. Find the marked
    // node via CDP, then DOM.setFileInputFiles.
    try {
      const doc = await cdp(tabId, "DOM.getDocument", {});
      const q = await cdp(tabId, "DOM.querySelector", {
        nodeId: doc.root.nodeId,
        selector: "[data-ocic-upload-target]",
      });
      if (!q || !q.nodeId) {
        return { content: [{ type: "text", text: `Could not resolve the file input node for ref=${ref}.` }] };
      }
      await cdp(tabId, "DOM.setFileInputFiles", { nodeId: q.nodeId, files: paths });
    } finally {
      await sendContentMessage(tabId, { type: "unmarkElementForUpload" }).catch(() => {});
    }

    const label = paths.length === 1 ? paths[0] : `${paths.length} files`;
    return { content: [{ type: "text", text: `Attached ${label} to the file input (ref=${ref}).` }] };
  },

  async gif_creator(args) {
    return { content: [{ type: "text", text: "GIF recording is not yet implemented in this extension." }] };
  },

  async shortcuts_list(args) {
    return { content: [{ type: "text", text: "No shortcuts available. Shortcuts are not supported in this extension." }] };
  },

  async shortcuts_execute(args) {
    return { content: [{ type: "text", text: "Shortcuts are not supported in this extension." }] };
  },

};
