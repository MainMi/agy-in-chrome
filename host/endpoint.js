// Where the native host and the MCP servers meet.
//
// A named pipe on Windows, a unix socket on POSIX, named deterministically from
// the username. There is no number to allocate, so there is no EADDRINUSE race
// and nothing for a stale process to squat; and the OS scopes it to the user,
// where a loopback TCP port is reachable by any process any local user is
// running — worth caring about, since every call across this bridge drives a
// real browser holding real logged-in sessions.
//
// This replaced a shared TCP port. The port is gone rather than deprecated:
// keeping both alive meant keeping the election, the yield protocol and the
// peer-classification sniff alive with it, which is most of what used to go
// wrong here.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

function configFile() {
  try {
    return JSON.parse(
      fs.readFileSync(
        path.join(os.homedir(), ".config", "agy-in-chrome", "config.json"),
        "utf-8"
      )
    );
  } catch {
    return {};
  }
}

// os.userInfo() THROWS rather than returning null when the account has no
// passwd entry — routine inside containers — and this runs before anything
// else, so an unhandled throw here would look like the bridge simply not
// existing. Fall back to the environment, then to a constant: a wrong-but-
// stable name still rendezvouses correctly, since both sides compute it the
// same way.
function currentUser() {
  try {
    const { username } = os.userInfo();
    if (username) return username;
  } catch {}
  return process.env.USER || process.env.USERNAME || "default";
}

export function getPipePath() {
  // Env override first, so a test harness can stand up a whole host + client
  // fleet on a scratch address without disturbing the live one.
  if (process.env.AGY_CHROME_PIPE) return process.env.AGY_CHROME_PIPE;
  if (process.env.OCIC_PIPE) return process.env.OCIC_PIPE;
  const configured = configFile().pipe;
  if (configured) return configured;
  // Windows pipe names live in a flat namespace and allow almost anything;
  // POSIX socket paths are length-limited (~104 bytes), so keep both short.
  const user = currentUser().replace(/[^\w.-]/g, "_").slice(0, 32);
  if (process.platform === "win32") {
    return `\\\\.\\pipe\\agy-in-chrome-${user}`;
  }
  return path.join(socketDir(), "bridge.sock");
}

// POSIX only: a 0700 directory so the socket inside it is unreachable by other
// users regardless of the socket's own mode. Windows named pipes get the
// equivalent from their default ACL.
export function socketDir() {
  let uid;
  try {
    uid = os.userInfo().uid;
  } catch {}
  return path.join(
    os.tmpdir(),
    `agy-in-chrome-${uid ?? currentUser().replace(/[^\w.-]/g, "_")}`
  );
}

export function ensureSocketDir() {
  if (process.platform === "win32") return;
  try {
    fs.mkdirSync(socketDir(), { recursive: true, mode: 0o700 });
    fs.chmodSync(socketDir(), 0o700);
  } catch {}
}

// The 0700 directory is the real guard, but set the socket's own mode too, so
// that a permissive umask — or a directory someone widens later — doesn't
// quietly leave the bridge open to other accounts on the machine.
export function secureSocket(pipePath) {
  if (process.platform === "win32") return; // pipe ACLs already scope this
  try {
    fs.chmodSync(pipePath, 0o600);
  } catch {}
}

// A unix socket file outlives the process that made it, so a host that was
// killed leaves a path that listen() will refuse with EADDRINUSE even though
// nobody is home. Only unlink when a connect attempt proves it is dead —
// unlinking a live socket would silently strand every client on it.
export async function clearStaleSocket(pipePath) {
  if (process.platform === "win32") return; // pipes vanish with their process
  if (!fs.existsSync(pipePath)) return;
  const net = await import("node:net");
  const alive = await new Promise((resolve) => {
    const probe = net.createConnection(pipePath);
    const done = (v) => {
      probe.destroy();
      resolve(v);
    };
    probe.on("connect", () => done(true));
    probe.on("error", () => done(false));
    setTimeout(() => done(false), 500);
  });
  if (!alive) {
    try {
      fs.unlinkSync(pipePath);
    } catch {}
  }
}
