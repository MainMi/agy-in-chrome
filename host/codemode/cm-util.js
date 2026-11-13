// Shared bits for the codemode plumbing modules — split out of common.js.
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const WORKER_DIR = path.join(__dirname, "worker");

export const log = (...args) => process.stderr.write(`[codemode] ${args.join(" ")}\n`);
