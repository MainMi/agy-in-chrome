# Split out of runner.py — pure refactor, behavior unchanged.

import os, shutil

from runner_common import BENCH
from runner_prompts import (
    CINC_NOCODE_HEADER, COWORK_ANALYZED_SILENT_HEADER,
    OCIC_ANALYZED_CODE_HEADER, OCIC_ANALYZED_SILENT_HEADER,
    OCIC_EXPERIENTIAL_ANALYZED_SILENT_HEADER, OCIC_EXPERIENTIAL_HEADER,
    OCIC_EXPERT_CODE_HEADER, OCIC_EXPERT_HEADER,
    OCIC_NEW_ANALYZED_SILENT_HEADER, OCIC_NOCODE_HEADER)
from runner_prompts2 import (
    CINC_PARITY_HEADER, P4A_FORK_HEADER, P4B_FORK_HEADER,
    P5D_FORK_RECIPE_HEADER, P5_FORK_HEADER, P5_RECIPE_HEADER,
    RECIPES_DIR_COWORK, RECIPES_DIR_OCIC_NEW)

EXPERIMENTS = {
    # Experiential-experience generation: phase-1 pipeline over the TRAIN set.
    "gen-experiential": {
        "system": "ocic", "split": "train_order", "header": OCIC_NOCODE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
    },
    # Phase 1
    "exp1a-ocic-cold": {
        "system": "ocic", "split": "test_order", "header": OCIC_NOCODE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
    },
    "exp1b-cinc-cold": {
        "system": "cinc", "split": "test_order", "header": CINC_NOCODE_HEADER,
        "claude_args": ["--chrome"], "execute_code_allowed": False,
    },
    # Control re-run of the official-CinC cold baseline (2026-07-16), identical
    # config to exp1b-cinc-cold. The original ran ~3 weeks earlier in a
    # different environment epoch (older CLI, pre-fix era); this re-run checks
    # that the large OCIC-vs-CinC gap is not an artifact of environmental
    # drift. New arm name preserves the original data.
    "exp1b-cinc-rerun": {
        "system": "cinc", "split": "test_order", "header": CINC_NOCODE_HEADER,
        "claude_args": ["--chrome"], "execute_code_allowed": False,
    },
    # Setup-parity CinC arm, v2 (2026-07-16): the official topology forces the
    # agent to create its own session-scoped tab group (see CINC_PARITY_HEADER
    # note), so parity = a deterministically scripted two-action preamble plus
    # setup-excluded accounting in analysis. Seed/teardown use the original
    # orchestrator-side adapter (state is origin-scoped; always was correct).
    # Fresh per-rollout tabs self-activate in their window: keep the Chrome
    # window visible and every rollout runs in an active tab.
    "exp1b-cinc-parity": {
        "system": "cinc", "split": "test_order", "header": CINC_PARITY_HEADER,
        "claude_args": ["--chrome"], "execute_code_allowed": False,
    },
    # Phase 2: same OCIC pipeline + prior experience mounted at ./experience/.
    "exp2a-experiential": {
        "system": "ocic", "split": "test_order", "header": OCIC_EXPERIENTIAL_HEADER,
        "claude_args": [], "execute_code_allowed": False, "experience": "experiential",
    },
    "exp2b-expert": {
        "system": "ocic", "split": "test_order", "header": OCIC_EXPERT_HEADER,
        "claude_args": [], "execute_code_allowed": False, "experience": "expert",
    },
    # Post-fix re-run of 2A (raw experiential traces, execute_code forbidden) on
    # Brave with the tab-activation fix. New arm name so the pre-fix
    # exp2a-experiential data stays intact for historical comparison. Completes
    # the post-fix matrix: cold / expert-analysis / experiential-analysis /
    # experiential-raw.
    "exp2a-fixed-brave": {
        "system": "ocic", "split": "test_order", "header": OCIC_EXPERIENTIAL_HEADER,
        "claude_args": [], "execute_code_allowed": False, "experience": "experiential",
    },
    # Post-fix re-run of 2B (raw expert recordings, execute_code forbidden) on
    # Brave. New arm name so the pre-fix exp2b-expert data stays intact. Fills
    # the last cell of the post-fix matrix: expert-raw.
    "exp2b-fixed-brave": {
        "system": "ocic", "split": "test_order", "header": OCIC_EXPERT_HEADER,
        "claude_args": [], "execute_code_allowed": False, "experience": "expert",
    },
    # 1A repeated with OCIC connected to CHROME instead of Brave (post ack-fix,
    # v2 extension). Identical header/pipeline; browser selection is operational
    # (extension enabled only in Chrome). Verify identity before running.
    "exp1a-chrome": {
        "system": "ocic", "split": "test_order", "header": OCIC_NOCODE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
    },
    # Post-fix (tab-activation) re-runs of the cold baseline, one per browser.
    # Same OCIC no-code pipeline; the browser is whichever is primary at run
    # time (Chrome, or Brave after switch_browser). Windows sized to the
    # standard 1512x948 so results compare to the earlier arms.
    "exp1a-fixed-chrome": {
        "system": "ocic", "split": "test_order", "header": OCIC_NOCODE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
    },
    "exp1a-fixed-brave": {
        "system": "ocic", "split": "test_order", "header": OCIC_NOCODE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
    },
    # Phase 3: execute_code permitted (usage tracked). Control = exp2b-expert.
    "exp3a-code": {
        "system": "ocic", "split": "test_order", "header": OCIC_EXPERT_CODE_HEADER,
        "claude_args": [], "execute_code_allowed": True, "experience": "expert",
    },
    "exp3b-code-analysis": {
        "system": "ocic", "split": "test_order", "header": OCIC_ANALYZED_CODE_HEADER,
        "claude_args": [], "execute_code_allowed": True, "experience": "expert_analyzed",
    },
    # Post-fix re-run of 3b on Brave (analysis env, execute_code encouraged).
    "exp3b-brave": {
        "system": "ocic", "split": "test_order", "header": OCIC_ANALYZED_CODE_HEADER,
        "claude_args": [], "execute_code_allowed": True, "experience": "expert_analyzed",
    },
    # 3c: same analysis env, but the prompt makes NO mention of execute_code —
    # the tool is available and the model decides on its own whether to use it.
    "exp3c-analysis": {
        "system": "ocic", "split": "test_order", "header": OCIC_ANALYZED_SILENT_HEADER,
        "claude_args": [], "execute_code_allowed": True, "experience": "expert_analyzed",
    },
    # 3d: the experiential twin of 3c. Same silent phase-3 pipeline (execute_code
    # available, no prompt mention), same Brave browser, same analysis-doc format
    # — the ONLY difference from 3c is the source of the analysis: docs distilled
    # from the agent's OWN past runs instead of the expert recordings. Isolates
    # "experiential vs expert" as the source of the compressed knowledge.
    "exp3d-experiential-analysis": {
        "system": "ocic", "split": "test_order",
        "header": OCIC_EXPERIENTIAL_ANALYZED_SILENT_HEADER,
        "claude_args": [], "execute_code_allowed": True,
        "experience": "experiential_analyzed",
    },
    # Phase 4: every rollout forks the checkpointed study session (see the
    # phase-4 block above). Requires `runner.py p4study --arm <arm>` to have
    # produced data/phase4/<arm>_study/{study.json, workdir_snapshot.tar.gz}.
    "exp4a-experiential-fork": {
        "system": "ocic", "split": "test_order", "header": P4A_FORK_HEADER,
        "claude_args": [], "execute_code_allowed": True, "phase4": "experiential",
    },
    "exp4b-expert-fork": {
        "system": "ocic", "split": "test_order", "header": P4B_FORK_HEADER,
        "claude_args": [], "execute_code_allowed": True, "phase4": "expert",
    },
    # Phase 5 (see block above). 5A/5B: cold + recipe in the prompt.
    "exp5a-recipe-site": {
        "system": "ocic", "split": "test_order", "header": P5_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": False, "recipe": "site",
    },
    "exp5b-recipe-single": {
        "system": "ocic", "split": "test_order", "header": P5_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": False, "recipe": "single",
    },
    # 5C: fork the website-matched atomic warm-up checkpoint.
    "exp5c-atomic-warmup": {
        "system": "ocic", "split": "test_order", "header": P5_FORK_HEADER,
        "claude_args": [], "execute_code_allowed": True, "p5route": True,
    },
    # 5D: 5C's routed fork + 5A's site recipe in the prompt.
    "exp5d-warmup-recipe": {
        "system": "ocic", "split": "test_order", "header": P5D_FORK_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": True, "p5route": True,
        "recipe": "site",
    },
    # ---- Phase 7: recording-system comparison (OCIC raw vs cowork artifacts).
    # Both systems captured the SAME six train sessions simultaneously, so the
    # underlying events are held constant and only the representation differs.
    # 7A/7B replay the phase-3 regime (analysis + sources mounted on disk);
    # 7C/7D replay the 5b regime (site-routed recipe spliced into the prompt).
    # Within each pair the header, flags and delivery are identical.
    "exp7a-ocic-analysis": {
        "system": "ocic", "split": "test_order", "header": OCIC_NEW_ANALYZED_SILENT_HEADER,
        "claude_args": [], "execute_code_allowed": True,
        "experience": "ocic_new_analyzed",
    },
    "exp7b-cowork-analysis": {
        "system": "ocic", "split": "test_order", "header": COWORK_ANALYZED_SILENT_HEADER,
        "claude_args": [], "execute_code_allowed": True,
        "experience": "cowork_analyzed",
    },
    "exp7c-ocic-recipe": {
        "system": "ocic", "split": "test_order", "header": P5_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
        "recipe": "site", "recipe_dir": RECIPES_DIR_OCIC_NEW,
    },
    "exp7d-cowork-recipe": {
        "system": "ocic", "split": "test_order", "header": P5_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": False,
        "recipe": "site", "recipe_dir": RECIPES_DIR_COWORK,
    },
    # 7E = 6b's exact design (same warm-up checkpoints, same fork routing, same
    # header) with ONLY the recipe swapped for the phase-7 OCIC one. Isolates
    # the recipe's contribution against the study's winning arm.
    "exp7e-ocic-warmup-recipe": {
        "system": "ocic", "split": "test_order", "header": P5D_FORK_RECIPE_HEADER,
        "claude_args": [], "execute_code_allowed": True, "p5route": True,
        "recipe": "site", "recipe_dir": RECIPES_DIR_OCIC_NEW,
    },
}

# Phase-2 experience sources (built from phase-1 train runs / operator demos).
# experiential = Claude Code session traces with image-bytes swapped for frame
# references (build_experiential_env.py); expert = operator OCIC recordings.
ENV_EXPERIENTIAL = os.path.join(BENCH, "environments", "experiential", "mounted")
ENV_EXPERT = os.path.join(BENCH, "environments", "expert", "recordings")
ENV_EXPERT_ANALYZED = os.path.join(BENCH, "environments", "expert_analyzed", "mounted")
ENV_EXPERIENTIAL_ANALYZED = os.path.join(BENCH, "environments", "experiential_analyzed", "mounted")
# Phase 7: two recording systems captured the SAME six train sessions
# simultaneously. ocic_new = raw 4-track recordings (nothing distilled at
# capture time); cowork = one generated markdown artifact per task, already
# analyzed at capture time by that system (no raw layer is retained by it).
# Both analyzed environments carry per-site ANALYSIS docs authored from their
# own sources only, by the same isolated Fable-5 distiller.
ENV_OCIC_NEW_ANALYZED = os.path.join(BENCH, "environments", "ocic_new_analyzed", "mounted")
ENV_COWORK_ANALYZED = os.path.join(BENCH, "environments", "cowork_analyzed", "mounted")

def populate_experience(workdir, kind, log):
    """Copy the read-only prior-experience environment VERBATIM into
    <workdir>/experience/ so it lives INSIDE the agent's cwd (no --add-dir,
    tight jail). Rebuilt disposably each rollout. Each environment is fully
    defined on disk (data + its own README.md); this is a pure copy, no
    per-rollout generation. No finish/evaluation artifacts exist in either
    source (ground-truth leak). Both arms keep viewable frames; they differ
    only in the source of experience."""
    src = {"experiential": ENV_EXPERIENTIAL, "expert": ENV_EXPERT,
           "expert_analyzed": ENV_EXPERT_ANALYZED,
           "experiential_analyzed": ENV_EXPERIENTIAL_ANALYZED,
           "ocic_new_analyzed": ENV_OCIC_NEW_ANALYZED,
           "cowork_analyzed": ENV_COWORK_ANALYZED}.get(kind)
    if not src:
        raise ValueError("unknown experience kind: %s" % kind)
    dst = os.path.join(workdir, "experience")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    nfiles = sum(len(fs) for _, _, fs in os.walk(dst))
    log("  experience mounted: %s, %d file(s) under ./experience/ (verbatim copy)" % (kind, nfiles))

# ---- small utils ------------------------------------------------------------

