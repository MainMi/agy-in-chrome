// IndexedDB layer for the audit recorder, split out of index.js — pure
// refactor, behavior unchanged. The service worker and the options page share
// an extension origin, so the options page reads these stores directly.
const DB_NAME = "ocic-audit";
const DB_VERSION = 1;

let dbPromise = null;

// --- IndexedDB --------------------------------------------------------------
// The service worker and the options page share an extension origin, so the
// options page reads these stores directly rather than messaging the worker.
export function openDb() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("streams")) {
        db.createObjectStore("streams", { keyPath: "streamId" });
      }
      if (!db.objectStoreNames.contains("chunks")) {
        // Events are appended as chunks, never as one growing array: a
        // read-modify-write of a multi-megabyte event list on every flush
        // would be the thing that made recording expensive.
        db.createObjectStore("chunks", { keyPath: ["streamId", "seq"] });
      }
      if (!db.objectStoreNames.contains("sessions")) {
        db.createObjectStore("sessions", { keyPath: "sessionId" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbPromise;
}

export function tx(db, stores, mode) {
  return db.transaction(stores, mode);
}

export function reqDone(r) {
  return new Promise((resolve, reject) => {
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}

export async function put(store, value) {
  const db = await openDb();
  const t = tx(db, [store], "readwrite");
  await reqDone(t.objectStore(store).put(value));
}

export async function get(store, key) {
  const db = await openDb();
  const t = tx(db, [store], "readonly");
  return await reqDone(t.objectStore(store).get(key));
}

export async function getAll(store, query) {
  const db = await openDb();
  const t = tx(db, [store], "readonly");
  return await reqDone(t.objectStore(store).getAll(query));
}

