# Split out of runner.py — pure refactor, behavior unchanged.

import os

from runner_common import BENCH
from runner_prompts import OCIC_NOCODE_HEADER, _P4_FS_RULE, _P4_SILENT_BASE

def _p4_fork_header(prior_line):
    base = _P4_SILENT_BASE
    base = base.replace("logged in).\n\nRules:", "logged in).\n\n%s\n\nRules:" % prior_line)
    base = base.replace("- Work autonomously to completion.",
                        _P4_FS_RULE + "\n- Work autonomously to completion.")
    return base

P4A_FORK_HEADER = _p4_fork_header(
"""Prior experience: earlier in THIS SAME session you completed several similar
tasks in this same environment yourself. Draw on that experience directly —
you already know how these apps work.""")

P4B_FORK_HEADER = _p4_fork_header(
"""Prior experience: earlier in THIS SAME session you studied expert
demonstrations of similar tasks in this same environment and internalized how
these apps work. Draw on that understanding directly.""")

# 4A study: the first train segment uses the standard silent header + the
# phase-4 FS rule; segments 2..6 continue the SAME session with a short
# next-task message (new tab, fresh seeded state, same rules).
P4_TRAIN_HEADER = _P4_SILENT_BASE.replace(
    "- Work autonomously to completion.",
    _P4_FS_RULE + "\n- Work autonomously to completion.")

P4_TRAIN_CONT = """[BENCHMARK ROLLOUT — NEXT TASK]
The previous task is finished. A NEW task follows in the same app family.
Your workspace is now tabId {tab}, already open on {app_name} at {app_url}
(fresh, reset state; you are already logged in). The same rules as before
apply unchanged: act only in tabId {tab}; do not create tabs; never navigate
to a URL containing "/config" or "/finish"; never read or write
localStorage/sessionStorage; your working directory remains your ONLY
filesystem environment. Work autonomously to completion.

TASK:
{goal}

When the task is complete, end your reply with a line starting
"FINAL ANSWER:" followed by the answer (for action tasks, a one-line summary
of what you did)."""

# 4B study: thorough internalization of the expert recordings. Deliberately
# says NOTHING about the browser (neither offered nor forbidden — the model's
# own discretion) and nothing about execute_code. Only the filesystem boundary
# is stated. App state cannot be polluted: every test rollout re-seeds and
# asserts a clean /finish before the agent starts.
P4_EXPERT_STUDY_PROMPT = """[BENCHMARK STUDY SESSION]
You are preparing to work in a pair of demo web apps (dashdish, a food
delivery app; zilloft, a real-estate app). An expert operator recorded
themselves completing several tasks in these exact apps. The recordings are
on disk at ./experience/ (README.md lists them; SCHEMA_v0.md explains the
format; one folder per task holds trace.json and an images/ folder of frames).

Your job in this session is to STUDY those demonstrations and internalize how
these apps actually work. This is deep preparation, not a skim:
- Work through EVERY recording, action by action, alongside its frames.
- Reconstruct what the operator did and, more importantly, WHY it worked:
  page structure, which controls are real vs decorative, search and filter
  mechanics, form flows, quirks and gotchas of each app.
- Cross-check your understanding across the recordings until the apps'
  behavior is predictable to you — until you could complete similar tasks
  yourself without consulting the recordings again.
Take the time this needs. Do not stop at a summary of file contents; the goal
is that you INTERNALIZE the mechanics of these environments.

Boundary: this working directory is your ONLY filesystem environment. Do NOT
read, list, write, or search any path outside it, and do not run shell
commands that escape it (no `..`, no absolute paths elsewhere, no `cd /`).

You may organize the session however serves the goal; anything you leave in
the working directory stays available to you later. When you are done, end
your reply with a line starting "STUDY COMPLETE:" followed by one sentence on
the depth of understanding you reached."""

# Setup-parity CinC header, v2. The official extension scopes tab control to a
# per-session tab group (verified 2026-07-16: a tab created by one session
# cannot be driven by another; javascript_tool/get_page_text refuse foreign
# tabs), so an orchestrator-prepared persistent tab is impossible and the
# agent MUST create its own group/tab. Parity is therefore achieved by
# (a) scripting that preamble deterministically (two fixed actions, zero
# deliberation) and (b) tagging the setup prefix in analysis so times are
# reported raw and setup-excluded. State seeding stays orchestrator-side and
# was never a parity issue (localStorage is origin-scoped, shared across tabs).
CINC_PARITY_HEADER = """[BENCHMARK ROLLOUT]
You are an autonomous web agent completing one task in a real browser.

Browser access: use ONLY the "claude-in-chrome" MCP server tools
(Claude in Chrome). If its tools are deferred, load them with a single
ToolSearch call first.

SETUP PREAMBLE (do these two actions first, exactly, no exploration):
1. tabs_context with createIfEmpty true (a tab group with one tab appears).
2. Navigate that tab to {app_url} ({app_name}, a self-contained demo web app;
   you are already logged in; its state is pre-seeded and ready).
The preamble is expected overhead, not part of the task. After it, begin the
task immediately in that same tab.

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

# ---- Phase 5: leakage-free recipes + atomic warm-ups ------------------------
# Recipes are authored by an ISOLATED Fable-5 session that saw ONLY the raw
# train-derived material (experiential traces + expert recordings); the
# orchestrating session (which carries test knowledge) never writes recipe
# content. 5A/5B append a recipe to the COLD header (execute_code stays
# forbidden: the recipe text is the only delta vs the cold baseline).
# 5C forks a website-matched single-task warm-up checkpoint (silent header,
# phase-4 convention). 5D = 5C's fork + 5A's site recipe.
RECIPES_DIR = os.path.join(BENCH, "environments", "recipes")
# Phase 7 recipe sets: same site routing as 5b/6b, one set per recording
# system, each authored from that system's material only.
RECIPES_DIR_OCIC_NEW = os.path.join(BENCH, "environments", "recipes_ocic_new")
RECIPES_DIR_COWORK = os.path.join(BENCH, "environments", "recipes_cowork")

_P5_RECIPE_BLOCK = """Field notes for {app_name}, compiled by an earlier agent from prior runs on
similar tasks in this same app (use what helps; ignore what does not):

{recipe}"""

P5_RECIPE_HEADER = OCIC_NOCODE_HEADER.replace(
    "logged in).\n\nRules:", "logged in).\n\n" + _P5_RECIPE_BLOCK + "\n\nRules:")

P5_FORK_HEADER = _p4_fork_header(
"""Prior experience: earlier in THIS SAME session you completed a similar task
on this same website. Draw on that experience directly.""")

P5D_FORK_RECIPE_HEADER = P5_FORK_HEADER.replace(
    "logged in).\n\nPrior experience:",
    "logged in).\n\n" + _P5_RECIPE_BLOCK + "\n\nPrior experience:")

def load_recipe(kind, app, recipe_dir=None):
    """kind: site|single. Site recipes are RECIPE_<app>.md; single is
    RECIPE_combined.md. Authored by the isolated generator; read-only here.
    recipe_dir overrides RECIPES_DIR so an arm can carry its own recipe set
    (phase 7 runs one recipe set per recording system, same site routing)."""
    name = "RECIPE_combined.md" if kind == "single" else "RECIPE_%s.md" % app
    with open(os.path.join(recipe_dir or RECIPES_DIR, name)) as f:
        return f.read().strip()

