#!/usr/bin/env python3
"""benchmark_deep_dive.html: task-level anatomy, semantic categories, and the
fork-paradox forensics. Net-new report; charts are client-side SVG (vanilla JS,
self-contained), arms toggleable, box plots with visible outliers.

Reproduce: harvest.py -> stats.py -> (usage/deep extraction) -> build_deep_dive.py
"""
from deep_dive_data import *
from deep_dive_sections import *
from deep_dive_js import JS
from deep_dive_js2 import JS2

page_head = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCIC benchmark · deep dive</title><style>{CSS}</style></head><body><div class="wrap">
<div class="eyebrow">OCIC BENCHMARK · DEEP DIVE · TASK ANATOMY &amp; THE FORK PARADOX · 2026-07-16</div>
<h1>The forks thought less and still lost: a token-level anatomy of every task</h1>
<p class="lede">Companion to the main report. Interactive, task-itemized, and built to answer one question honestly:
why did the phase-4 forks, which carry the most knowledge, run the slowest? Toggle arms in the sticky bar; click any
task row for its full cross-arm anatomy. All charts render from the embedded per-rollout data.</p>

<div class="kpis">
<div class="kpi"><div class="n">315 turns · 4k out</div><div class="l">the experiential fork THOUGHT THE LEAST of all arms (cold: 391 · 5k)</div></div>
<div class="kpi"><div class="n">493k tok/turn</div><div class="l">but every fork turn carried 4-8x the context of any mounted arm (~65k)</div></div>
<div class="kpi"><div class="n">3.1 &#8594; 5.7 &#8594; 8.8s</div><div class="l">median seconds per turn: cold &#8594; expert fork &#8594; experiential fork</div></div>
<div class="kpi"><div class="n">r &#8776; 0.99</div><div class="l">per-turn latency vs context weight across arms: a straight line</div></div>
<div class="kpi"><div class="n">4 groups · 12 tasks</div><div class="l">semantic categories: carts, homepage reading, tour forms, filtered counting</div></div>
</div>
"""

page = (page_head + FORK_SECTION + page_mid
        + JS.replace("__PAYLOAD__", json.dumps(PAYLOAD)) + JS2)
out = os.path.join(BENCH, "benchmark_deep_dive.html")
open(out, "w").write(page)
print("wrote", out, f"({os.path.getsize(out)/1024:.0f} KB)")

