// Options page: OpenAI key management + sessions viewer with progressive
// disclosure (§9). All captured data is visible to the operator — metadata
// first, then the two tracks, then per-action anchors and effects — nothing
// hidden. Reads the same IndexedDB the offscreen buffer writes.

import { validateOpenAiKey } from "./transcribe.js";
import { wireAuditTabs } from "./audits.js";

const keyInput = document.getElementById("key");
const keyStatus = document.getElementById("keyStatus");

// ---- API key ----
chrome.storage.local.get("openai_api_key").then(({ openai_api_key }) => {
  if (openai_api_key) keyInput.value = openai_api_key;
});

document.getElementById("reveal").addEventListener("click", () => {
  keyInput.type = keyInput.type === "password" ? "text" : "password";
});

// ---- microphone grant ----
// The Options page is a visible surface, so getUserMedia here shows the Chrome
// permission prompt. Once granted, the permission persists for the extension
// origin and the offscreen recorder can capture the mic without prompting.
const micStatus = document.getElementById("micStatus");
async function refreshMicStatus() {
  try {
    const p = await navigator.permissions.query({ name: "microphone" });
    if (p.state === "granted") { micStatus.textContent = "Enabled."; micStatus.className = "status ok"; }
    else if (p.state === "denied") { micStatus.textContent = "Blocked — allow mic for this extension in browser settings."; micStatus.className = "status err"; }
    else { micStatus.textContent = "Not enabled yet."; micStatus.className = "status"; }
  } catch { micStatus.textContent = ""; }
}
refreshMicStatus();
document.getElementById("mic").addEventListener("click", async () => {
  micStatus.textContent = "Requesting…";
  micStatus.className = "status";
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((t) => t.stop()); // release immediately
    micStatus.textContent = "Enabled. You can record now.";
    micStatus.className = "status ok";
  } catch (e) {
    micStatus.textContent =
      e && e.name === "NotAllowedError"
        ? "Denied. Allow the microphone for this extension and retry."
        : `Error: ${e && e.message}`;
    micStatus.className = "status err";
  }
});

document.getElementById("save").addEventListener("click", async () => {
  const key = keyInput.value.trim();
  keyStatus.textContent = "Validating…";
  keyStatus.className = "status";
  const v = await validateOpenAiKey(key);
  if (v.ok) {
    await chrome.storage.local.set({ openai_api_key: key });
    keyStatus.textContent = "Saved and valid.";
    keyStatus.className = "status ok";
  } else {
    keyStatus.textContent = v.error;
    keyStatus.className = "status err";
  }
});

// ---- sessions viewer ----
function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("ocic-recorder", 3);
    req.onupgradeneeded = () => {
      const d = req.result;
      if (!d.objectStoreNames.contains("sessions"))
        d.createObjectStore("sessions", { keyPath: "recording_id" });
      if (!d.objectStoreNames.contains("events"))
        d.createObjectStore("events", { keyPath: "seq", autoIncrement: true });
      if (!d.objectStoreNames.contains("audio"))
        d.createObjectStore("audio", { keyPath: "seq", autoIncrement: true });
      if (!d.objectStoreNames.contains("cursor"))
        d.createObjectStore("cursor", { keyPath: "seq", autoIncrement: true });
      if (!d.objectStoreNames.contains("images"))
        d.createObjectStore("images", { keyPath: "seq", autoIncrement: true });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

import { esc, trunc, fmtTime, traceCache } from "./options-shared.js";
import "./options-detail.js";


async function renderSessions() {
  const container = document.getElementById("sessions");
  let db;
  try { db = await openDb(); } catch { return; }
  const rows = await new Promise((resolve) => {
    const tx = db.transaction("sessions", "readonly");
    const req = tx.objectStore("sessions").getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => resolve([]);
  });
  if (!rows.length) return;
  rows.sort((a, b) => b.started_at - a.started_at);

  container.innerHTML = "";
  for (const s of rows) {
    const dur = Math.round(((s.ended_at || 0) - s.started_at) / 1000);
    const host = (() => { try { return new URL(s.url0).host; } catch { return "—"; } })();
    const audioUrl = s.audio && s.audio.size ? URL.createObjectURL(s.audio) : null;
    // An empty narration track is ambiguous on its own — silent operator, or
    // lost teaching? Say which, loudly, and never let it read as success.
    const tstat = s.transcriptStatus || (s.trace && s.trace.transcript_status) || "";
    const status =
      tstat && tstat !== "ok"
        ? `<div class="tstatus"><strong>Transcript ${esc(tstat.split(":")[0])}</strong> — ${esc(
            tstat.replace(/^[^:]*:\s*/, "")
          )}. The narration track is empty or incomplete; the audio is on disk in <code>audio/</code>.</div>`
        : "";
    const player = audioUrl
      ? `<audio controls src="${audioUrl}" style="width:100%;margin:6px 0"></audio>`
      : `<div class="empty">No audio captured (mic not enabled?).</div>`;
    // First words spoken, so sessions are tellable apart at a glance.
    const snip = (s.trace?.cognitive || []).slice(0, 2).map((u) => u.text).join(" ").trim();
    const snippet = snip ? `<span class="snip">“${esc(snip)}”</span>` : "";
    const pathText = s.path ? esc(s.path) : "not written to disk (mic or native-host issue)";
    const pathrow = `<div class="pathrow"><code>${pathText}</code><button class="copy-ref" data-rid="${esc(s.recording_id)}" data-path="${esc(s.path || "")}" data-tstatus="${esc(tstat)}">Copy reference</button></div>`;
    const frames = s.images && s.images.length ? ` · ${s.images.length} frames` : "";
    const el = document.createElement("details");
    el.className = "sess";
    el.innerHTML = `
      <summary>
        <span class="id">${esc(s.recording_id)}</span>
        <span class="meta">${esc(host)} · ${dur}s · ${s.events} events · ${s.utterances} utterances${frames} · ${fmtTime(s.started_at)}</span>
        ${snippet}
      </summary>
      <div class="body">${status}${pathrow}${player}${renderTracks(s.trace, s.recording_id, s.images)}</div>`;
    container.appendChild(el);
  }
}

// The three tracks, side by side and aligned by time. All share one clock
// (ms since started_at), and — this is the load-bearing part — one mapping
// from that clock to a y position, so what was said sits exactly beside what
// was done. Quiet stretches show as visible gaps. Raw per-event JSON is one
// layer deeper.
import { renderTracks } from "./options-tracks.js";
