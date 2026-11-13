// Recording/audit/screenshot disk-write handlers, split out of
// native-host.js — pure refactor, behavior unchanged.
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { writeNativeMessage } from "./native-msg.js";

// --- Recording bundle write ---
// The recorder saves the trace to disk here, in the native host, instead of
// via chrome.downloads — the browser download path shows an OS save dialog on
// some setups, and this also lets us write to a stable location the coding
// agent can open. Returns the absolute directory so the extension can notify
// Claude Code with a real path.
// Audits live beside recordings but in their own tree: they answer "what did
// this agent session do", not "how is a task performed", and they are written
// on a checkpoint rather than at the end, so a session can be reviewed while
// its tabs are still open.
export function handleSaveAudit(msg) {
  try {
    const dir = path.join(
      os.homedir(),
      ".config",
      "agy-in-chrome",
      "audits",
      String(msg.session_id || "unknown")
    );
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, "audit.json"), JSON.stringify(msg.payload ?? {}, null, 2));
  } catch (e) {
    process.stderr.write(`save_audit failed: ${String(e && e.message)}\n`);
  }
}

export function handleSaveRecording(msg) {
  try {
    const dir = path.join(
      os.homedir(),
      ".config",
      "agy-in-chrome",
      "recordings",
      String(msg.recording_id || "unknown")
    );
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(
      path.join(dir, "trace.json"),
      JSON.stringify(msg.trace ?? {}, null, 2)
    );
    // Ship the schema descriptor alongside so the agent knows how to read it.
    if (typeof msg.schema_md === "string" && msg.schema_md) {
      fs.writeFileSync(path.join(dir, `SCHEMA_${msg.schema || "v0"}.md`), msg.schema_md);
    }
    writeNativeMessage({
      type: "recording_saved",
      recording_id: msg.recording_id,
      path: dir,
      ok: true
    });
  } catch (e) {
    writeNativeMessage({
      type: "recording_saved",
      recording_id: msg.recording_id,
      ok: false,
      error: String(e && e.message)
    });
  }
}

// Write one slice of a recording's audio into audio/NNN.webm. Arrives in
// ~768KB slices (base64 over native messaging) with append=false on the first
// slice of each segment. This is the artifact that makes a failed transcript
// recoverable, so it is written before transcription is even attempted.
export function handleSaveAudio(msg) {
  try {
    const rel = String(msg.name || "").replace(/\\/g, "/");
    // Contain the write to the bundle: no absolute paths, no traversal.
    if (rel.startsWith("/") || rel.split("/").includes("..")) return;
    const base = path.join(
      os.homedir(),
      ".config",
      "agy-in-chrome",
      "recordings",
      String(msg.recording_id || "unknown")
    );
    const file = path.join(base, rel);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const buf = Buffer.from(String(msg.b64 || ""), "base64");
    if (msg.append) fs.appendFileSync(file, buf);
    else fs.writeFileSync(file, buf);
  } catch {
    // best-effort: the trace is already on disk
  }
}

// Write one 240p frame into the recording's images/ dir. Fire-and-forget:
// the reference is already in the trace, so a dropped frame just means the
// agent finds no file at that ref.
export function handleSaveScreenshot(msg) {
  try {
    const dir = path.join(
      os.homedir(),
      ".config",
      "agy-in-chrome",
      "recordings",
      String(msg.recording_id || "unknown"),
      "images"
    );
    fs.mkdirSync(dir, { recursive: true });
    const b64 = String(msg.dataUrl || "").replace(/^data:image\/\w+;base64,/, "");
    if (b64) fs.writeFileSync(path.join(dir, String(msg.name)), Buffer.from(b64, "base64"));
  } catch {
    // best-effort
  }
}

// Write a full screenshot to a stable, user-visible location
// (~/.config/open-claude-in-chrome/screenshots/<timestamp>.jpg) so Claude Code
// can open the absolute path. Unlike save_screenshot (fire-and-forget), this
// replies with the written path so the caller can report it to the agent.
export function handleSaveScreenshotToDisk(msg) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const dir = path.join(
    os.homedir(),
    ".config",
    "agy-in-chrome",
    "screenshots"
  );
  try {
    fs.mkdirSync(dir, { recursive: true });
    const b64 = String(msg.dataUrl || "").replace(/^data:image\/\w+;base64,/, "");
    if (!b64 || !/^[A-Za-z0-9+/]+={0,2}$/.test(b64)) throw new Error("empty or malformed image data");
    const file = path.join(dir, `${timestamp}.jpg`);
    fs.writeFileSync(file, Buffer.from(b64, "base64"));
    writeNativeMessage({ type: "screenshot_saved", id: msg.id, path: file, ok: true });
  } catch (e) {
    writeNativeMessage({ type: "screenshot_saved", id: msg.id, ok: false, error: String(e && e.message) });
  }
}

// Stage an in-memory screenshot as a real temp file so the extension can
// attach it to a file input via CDP DOM.setFileInputFiles. The extension holds
// screenshots as base64 in a Map (never on disk), but setFileInputFiles needs
// a path, so we materialize the bytes here and return the absolute path.
// Reply is keyed by msg.id so the extension can correlate it to its request.
export function handleWriteTempFile(msg) {
  const reply = (payload) => writeNativeMessage({ id: msg.id, type: "temp_file_written", ...payload });
  try {
    const dir = path.join(os.homedir(), ".config", "agy-in-chrome", "tmp");
    fs.mkdirSync(dir, { recursive: true });
    // Sanitize the requested name: no path separators, no traversal.
    const name = String(msg.filename || "upload.png").replace(/[^\w.\-]/g, "_");
    const file = path.join(dir, `${Date.now()}_${name}`);
    const b64 = String(msg.dataUrl || "").replace(/^data:[^;]+;base64,/, "");
    if (!b64) return reply({ ok: false, error: "no data" });
    fs.writeFileSync(file, Buffer.from(b64, "base64"));
    // Best-effort GC: staged uploads have a "<epoch>_<name>" prefix; prune only
    // files WE staged (that prefix) and only those older than a day, so we never
    // delete anything another process put in the shared tmp dir. Cap the scan
    // so a giant directory can't stall this request.
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    try {
      let scanned = 0;
      for (const f of fs.readdirSync(dir)) {
        if (!/^\d+_/.test(f)) continue; // not ours
        if (++scanned > 200) break; // bound the sync scan
        const p = path.join(dir, f);
        if (fs.statSync(p).mtimeMs < cutoff) fs.unlinkSync(p);
      }
    } catch { /* best-effort */ }
    reply({ ok: true, result: file });
  } catch (e) {
    reply({ ok: false, error: String(e && e.message) });
  }
}

