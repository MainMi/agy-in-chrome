# Split out of runner.py — pure refactor, behavior unchanged.

# ---- experiment definitions -------------------------------------------------
# The HEADER is the per-experiment constant scaffolding; the task goal is
# appended per rollout. Phases 1 and 2 forbid execute_code explicitly.

OCIC_NOCODE_HEADER = """[BENCHMARK ROLLOUT]
You are an autonomous web agent completing one task in a real browser.

Browser access: use ONLY the "open-claude-in-chrome-hybrid" MCP server tools
(Open Claude in Chrome). If its tools are deferred, load them with a single
ToolSearch call first. Work ONLY in tabId {tab}. That tab is already open on
{app_name} at {app_url} (a self-contained demo web app; you are already
logged in).

Rules:
- Act only in tabId {tab}. Do not create tabs. Do not visit any other website.
- Never navigate to a URL containing "/config" or "/finish".
- Never read or write localStorage/sessionStorage or inject state directly.
- You are NOT allowed to use the execute_code tool in this experiment. Drive
  the UI only with discrete tool calls (screenshot, click, type, scroll, find,
  read_page, navigate within the app).
- Work autonomously to completion. If a click misses, look again and retry.
  Do not stop early. Do not ask questions.

TASK:
{goal}

When the task is complete, end your reply with a line starting
"FINAL ANSWER:" followed by the answer (for action tasks, a one-line summary
of what you did)."""

# Phase 2 adds prior experience mounted on disk at ./experience/ and a
# filesystem boundary. Everything else (execute_code forbidden, browser jail)
# is identical to phase 1. The %s slots are filled at import; {tab}/{app_name}/
# {app_url}/{goal} stay for per-rollout .format().
_FS_RULE = """- This working directory is your ONLY filesystem environment. You may read the
  files under ./experience/ (that is why they are there). Do NOT read, list,
  write, or search any path outside this directory, and do not run shell
  commands that escape it (no `..`, no absolute paths elsewhere, no `cd /`)."""

_PRIOR_EXPERIENTIAL = """Prior experience: you (this same agent) have already completed several similar
tasks in THIS SAME environment. Your own past runs are saved on disk at
./experience/ as traces extracted directly from a Claude Code session — the
normal trace format you already understand. One folder per task (trace.jsonl +
images/). The only change from a raw session: inline screenshots are stored as
image files, referenced in the trace as `[screenshot -> images/NNNN.jpg]`; open
that file to view the frame. BEFORE you start clicking, read
./experience/README.md, open the past run whose goal is closest to your task,
and reuse the UI flow that already worked. This is memory to adapt, not a script."""

_PRIOR_EXPERT = """Prior experience: an expert operator recorded themselves completing several
similar tasks in THIS SAME environment. Their demonstrations are on disk at
./experience/ (one folder per task; README.md lists them, SCHEMA_v0.md explains
the recording format, each task folder has a trace.json with the
behavior/cursor/narration track and an images/ folder of frames). BEFORE you
start clicking, read ./experience/README.md, study the demonstration whose goal
is closest to your task, and follow the same UI flow. Adapt it to the current task."""

def _phase2_header(prior):
    base = OCIC_NOCODE_HEADER
    # inject the prior-experience block after the "logged in)." intro paragraph
    base = base.replace("logged in).\n\nRules:", "logged in).\n\n%s\n\nRules:" % prior)
    # append the filesystem boundary as the last hard rule before the autonomy line
    base = base.replace(
        "- Work autonomously to completion.",
        _FS_RULE + "\n- Work autonomously to completion.")
    return base

OCIC_EXPERIENTIAL_HEADER = _phase2_header(_PRIOR_EXPERIENTIAL)
OCIC_EXPERT_HEADER = _phase2_header(_PRIOR_EXPERT)

# Phase 3 flips the execute_code clause from forbidden to permitted (usage is
# tracked, not capped). 3A keeps the plain expert experience; 3B mounts the
# analyzed environment and its prior block points at the ANALYSIS docs first.
_NOCODE_CLAUSE = """- You are NOT allowed to use the execute_code tool in this experiment. Drive
  the UI only with discrete tool calls (screenshot, click, type, scroll, find,
  read_page, navigate within the app)."""

_CODE_CLAUSE = """- You MAY use the execute_code tool in this experiment, and you are encouraged
  to lean on it where it helps: it runs JavaScript with the other browser tools
  exposed as functions (chrome.computer, chrome.find, chrome.navigate, ...), so
  a deterministic multi-step sequence can run in ONE call instead of many.
  Batch what is predictable; look first (screenshot) where the next move
  depends on what the page shows."""

_PRIOR_EXPERT_ANALYZED = """Prior experience: an expert operator recorded themselves completing several
similar tasks in THIS SAME environment, and those demonstrations have ALREADY
been analyzed for you. On disk at ./experience/ you will find:
- ANALYSIS_dashdish.md and ANALYSIS_zilloft.md: compressed per-site insights
  (page map, which controls are real vs decorative, search and filter
  mechanics, recipes, gotchas). Read the one for your task's site FIRST; it is
  intended to be sufficient on its own.
- The raw recordings (one folder per task: trace.json + SCHEMA_v0.md +
  images/), only if you need to verify a detail.
Read ./experience/README.md and the relevant ANALYSIS file BEFORE you start
clicking, then act."""

_PRIOR_EXPERIENTIAL_ANALYZED = """Prior experience: you (this same agent) have already completed several similar
tasks in THIS SAME environment, and your own past runs have ALREADY been
analyzed for you. On disk at ./experience/ you will find:
- ANALYSIS_dashdish.md and ANALYSIS_zilloft.md: compressed per-site insights
  distilled from your own attempts (page map, what worked vs what stalled,
  search and filter mechanics, recipes, gotchas). Read the one for your task's
  site FIRST; it is intended to be sufficient on its own.
- The raw runs (one folder per task: trace.jsonl + images/), only if you need
  to verify a detail.
Read ./experience/README.md and the relevant ANALYSIS file BEFORE you start
clicking, then act."""

def _phase3_header(prior):
    return _phase2_header(prior).replace(_NOCODE_CLAUSE, _CODE_CLAUSE)

def _phase3_silent_header(prior):
    # No execute_code clause at all — neither forbidden nor encouraged. The tool
    # is available (execute_code_allowed=True); whether to use it is left
    # entirely to the model, with zero prompt steering either way.
    return _phase2_header(prior).replace(_NOCODE_CLAUSE + "\n", "")

OCIC_EXPERT_CODE_HEADER = _phase3_header(_PRIOR_EXPERT)
OCIC_ANALYZED_CODE_HEADER = _phase3_header(_PRIOR_EXPERT_ANALYZED)
OCIC_ANALYZED_SILENT_HEADER = _phase3_silent_header(_PRIOR_EXPERT_ANALYZED)

# ---- Phase 7 prior blocks: same phase-3 regime, one per recording system.
# Deliberately parallel in structure and length so the ONLY prompt difference
# is what the underlying source material actually is; the analysis filename
# and the read-this-first instruction are identical in both.
_PRIOR_OCIC_NEW_ANALYZED = """Prior experience: an expert operator was recorded completing several similar
tasks in THIS SAME environment, and those recordings have ALREADY been analyzed
for you. On disk at ./experience/ you will find:
- ANALYSIS_dashdish.md and ANALYSIS_zilloft.md: compressed per-site insights
  (page map, which controls are real vs decorative, search and filter
  mechanics, recipes, gotchas). Read the one for your task's site FIRST; it is
  intended to be sufficient on its own.
- The raw recordings (one folder per task: trace.json + SCHEMA_v0.md +
  images/), only if you need to verify a detail.
Read ./experience/README.md and the relevant ANALYSIS file BEFORE you start
clicking, then act."""

_PRIOR_COWORK_ANALYZED = """Prior experience: an expert operator was recorded completing several similar
tasks in THIS SAME environment, and those recordings have ALREADY been analyzed
for you. On disk at ./experience/ you will find:
- ANALYSIS_dashdish.md and ANALYSIS_zilloft.md: compressed per-site insights
  (page map, which controls are real vs decorative, search and filter
  mechanics, recipes, gotchas). Read the one for your task's site FIRST; it is
  intended to be sufficient on its own.
- The per-task artifacts the recording system generated (one markdown file per
  task), only if you need to verify a detail.
Read ./experience/README.md and the relevant ANALYSIS file BEFORE you start
clicking, then act."""

OCIC_NEW_ANALYZED_SILENT_HEADER = _phase3_silent_header(_PRIOR_OCIC_NEW_ANALYZED)
COWORK_ANALYZED_SILENT_HEADER = _phase3_silent_header(_PRIOR_COWORK_ANALYZED)
# Experiential twin of the analyzed-silent header: same silent (no execute_code
# mention) phase-3 prompt, but the prior block points at analysis distilled from
# the agent's OWN past runs rather than the expert recordings.
OCIC_EXPERIENTIAL_ANALYZED_SILENT_HEADER = _phase3_silent_header(_PRIOR_EXPERIENTIAL_ANALYZED)

# EXP-1B: the official Claude-in-Chrome extension in the user's CHROME.
# Mirrors OCIC_NOCODE_HEADER with three deliberate differences, all forced by
# the official topology and documented as caveats: (1) the MCP is
# "claude-in-chrome"; (2) there is no orchestrator-assigned tab (the session
# owns its own tab group), so the agent opens ONE tab itself; (3) the no-code
# bullet bans javascript_tool (the official MCP has no execute_code).
CINC_NOCODE_HEADER = """[BENCHMARK ROLLOUT]
You are an autonomous web agent completing one task in a real browser.

Browser access: use ONLY the "claude-in-chrome" MCP server tools
(Claude in Chrome). If its tools are deferred, load them with a single
ToolSearch call first. Get the tab context (create the tab group if needed),
open ONE new tab, and navigate it to {app_url} ({app_name}, a self-contained
demo web app; you are already logged in).

Rules:
- Work ONLY in that one tab. Do not open more tabs. Do not visit any other
  website.
- Never navigate to a URL containing "/config" or "/finish".
- Never read or write localStorage/sessionStorage or inject state directly.
- You are NOT allowed to use the javascript_tool in this experiment. Drive
  the UI only with discrete tool calls (screenshot, click, type, scroll, find,
  read_page, navigate within the app).
- Work autonomously to completion. If a click misses, look again and retry.
  Do not stop early. Do not ask questions.

TASK:
{goal}

When the task is complete, end your reply with a line starting
"FINAL ANSWER:" followed by the answer (for action tasks, a one-line summary
of what you did)."""

# ---- Phase 4: fork-and-resume from a checkpoint session ---------------------
# Phase 3 mounted a library next to the task ("here are the docs, go read
# them"); phase 4 has ALREADY read the library: a one-time study/experience
# session is checkpointed, and every test rollout FORKS that session
# (claude -p --resume <sid> --fork-session) with the study's working directory
# restored VERBATIM at the SAME absolute path (forks only resolve from the
# session's own project cwd; verified empirically). execute_code is never
# mentioned in any phase-4 prompt; using it is neither encouraged nor a
# violation. Model/effort are the global AGENT_MODEL/AGENT_EFFORT (sonnet,
# medium) for study, train segments, and forks alike.

_P4_SILENT_BASE = OCIC_NOCODE_HEADER.replace(_NOCODE_CLAUSE + "\n", "")

_P4_FS_RULE = """- This working directory is your ONLY filesystem environment. It contains
  whatever it contained earlier in this session (any notes or materials,
  including ./experience/ if present). Do NOT read, list, write, or search any
  path outside this directory, and do not run shell commands that escape it
  (no `..`, no absolute paths elsewhere, no `cd /`)."""

