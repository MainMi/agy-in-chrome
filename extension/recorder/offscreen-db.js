// IndexedDB durable-buffer layer, split out of offscreen.js — pure refactor,
// behavior unchanged. `db` is the shared handle: callers run `await ensureDb()`
// before using the store helpers (the old inline `db = db || (await openDb())`).
let db = null;

export async function ensureDb() {
  db = db || (await openDb());
}

export function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("ocic-recorder", 3);
    req.onupgradeneeded = () => {
      const d = req.result;
      if (!d.objectStoreNames.contains("events"))
        d.createObjectStore("events", { keyPath: "seq", autoIncrement: true });
      if (!d.objectStoreNames.contains("audio"))
        d.createObjectStore("audio", { keyPath: "seq", autoIncrement: true });
      if (!d.objectStoreNames.contains("sessions"))
        d.createObjectStore("sessions", { keyPath: "recording_id" });
      if (!d.objectStoreNames.contains("cursor"))
        d.createObjectStore("cursor", { keyPath: "seq", autoIncrement: true });
      if (!d.objectStoreNames.contains("images"))
        d.createObjectStore("images", { keyPath: "seq", autoIncrement: true });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
export function put(store, value) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).add(value);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
}
// add() throws on a duplicate key; the session record is written once at stop
// and again after transcription, so that one needs an upsert.
export function putRecord(store, value) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put(value);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
}
export function getAll(store) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readonly");
    const req = tx.objectStore(store).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
export function getRow(store, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readonly");
    const req = tx.objectStore(store).get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
export function clearStore(store) {
  return new Promise((resolve) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).clear();
    tx.oncomplete = resolve;
  });
}
export function patchSession(recording_id, patch) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("sessions", "readwrite");
    const store = tx.objectStore("sessions");
    const get = store.get(recording_id);
    get.onsuccess = () => {
      const rec = get.result;
      if (rec) {
        Object.assign(rec, patch);
        store.put(rec);
      }
      resolve(!!rec);
    };
    get.onerror = () => reject(get.error);
  });
}

