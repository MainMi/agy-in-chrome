# Split out of build_deep_dive.py — pure refactor, behavior unchanged.

CSS = """
:root{--bg:#fbfbf9;--surface:#fff;--ink:#1b1f24;--muted:#5b6571;--dim:#8a929c;--line:#e7e6e1;--soft:#f3f2ee;--red:#c13a2e;--green:#0f8a5f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:40px 28px 110px}
h1{font-size:28px;line-height:1.18;letter-spacing:-.02em;margin:4px 0 8px}
h2{font-size:21px;margin:52px 0 6px;padding-bottom:7px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:24px 0 6px}
p{margin:8px 0}
.eyebrow{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);font-weight:600}
.lede{font-size:16.5px;color:var(--muted)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}
.scroll{overflow-x:auto;padding-bottom:6px}
table{border-collapse:collapse;font-size:13px;width:100%}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);white-space:nowrap}
td.num{font-variant-numeric:tabular-nums;text-align:right}
.mono{font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .n{font-size:21px;font-weight:700;letter-spacing:-.02em}
.kpi .l{font-size:11.5px;color:var(--muted)}
.note{font-size:12.5px;color:var(--muted)}
.callout{background:var(--surface);border:1px solid var(--line);border-left:3px solid #3b82f6;border-radius:8px;padding:12px 16px;margin:14px 0;font-size:13.5px}
.togglebar{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:5;border-bottom:1px solid var(--line)}
.tg{display:inline-flex;align-items:center;gap:6px;font-size:12px;border:1px solid var(--line);border-radius:14px;padding:3px 10px;cursor:pointer;user-select:none;background:var(--surface)}
.tg .sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.badge{display:inline-block;font-size:10px;font-weight:700;border-radius:4px;padding:1px 6px}
.b-pass{background:#0f8a5f14;color:var(--green)}.b-fail{background:#c13a2e14;color:var(--red)}
tr.clickable{cursor:pointer}tr.clickable:hover{background:var(--soft)}
#detail{position:sticky;bottom:0;background:var(--surface);border:1px solid var(--line);border-radius:10px 10px 0 0;box-shadow:0 -4px 18px rgba(0,0,0,.06);padding:12px 18px;display:none;max-height:46vh;overflow:auto}
#detail.open{display:block}
#detail .x{float:right;cursor:pointer;color:var(--dim);font-size:18px}
.legendline{font-size:12px;color:var(--muted);margin:4px 0}
svg text{font-family:inherit}
"""

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

FORK_SECTION = """
<h2>1 &middot; The fork paradox, resolved</h2>
<div class="card">
<p style="margin-top:0"><strong>The hypothesis was half right, and the half that failed is invisible in turn counts.</strong>
Forks were invoked as true continuations: <span class="mono">claude -p --resume &lt;study-sid&gt; --fork-session</span>, with a
task prompt byte-identical to the cold arm's except a three-line prior notice and the filesystem rule (the prompt diff is
in the main report's methods; execute_code goes unmentioned). The ONLY functional difference is the conversation prefix:
the entire study transcript rides in front of every fork rollout. What the data shows:</p>
<ul>
<li><strong>Forks reasoned least, exactly as hypothesized.</strong> Fewest turns (315 for 4A vs 391 cold), least output
(4k tokens/task). In-context knowledge DID cut deliberation and search.</li>
<li><strong>But every turn re-processes the checkpoint.</strong> Total input per turn (cache reads + writes + fresh):
493k tokens (4A) and 278k (4B) vs 62-79k for every disk-mounted arm. Time-to-first-token scales with prefix length, so
each of the fork's ~300+ turns pays a fixed context toll before its first output token.</li>
<li><strong>The toll shows up everywhere timing is measured:</strong> median think-gap 8.8s / 5.7s vs ~3.1s; first
browser action 24s / 10s vs 4s (the first turn must ingest the whole checkpoint before acting at all); p90 gaps 13.3s /
9.2s vs 4.7s; worst single gap 41s.</li>
<li><strong>Cache economics make it worse, not better.</strong> Each rollout re-wrote 212-262k tokens of cache (vs ~55k
elsewhere): the study session's cache was hours dead, rollouts sit at the TTL boundary, and every fork diverges from the
shared prefix at its own first message.</li>
</ul>
<div id="c_turnsout"></div>
<div id="c_ktok"></div>
<div id="c_scatter"></div>
<p class="note">One dot per arm: median seconds per turn against thousand-tokens carried per turn. The relationship is
linear across an 8x context range; the forks are not thinking harder, they are hauling more.</p>
<div id="c_ctxcurve"></div>
<p class="note">The turn-latency law, at task resolution: one dot per rollout (84 total: every task in every arm with
usage data), x = thousand tokens carried per turn in THAT rollout, y = that rollout's mean seconds per turn. The fit is
linear across the full 65k-to-505k range: <b>s/turn &#8776; 2.2 + 1.6s per 100k tokens carried</b> (r = 0.88). The
clusters left to right: all mounted arms (~65-80k), the expert fork (~250-290k), the experiential fork (~475-505k).
Every 100k tokens of history costs about a second and a half on every single turn, before any work happens.</p>
<div id="c_series"></div>
<p class="note">Median think-gap at each turn index (first 40 turns, arms toggleable above). The forks are elevated from
turn 1, flat, and never converge to the mounted arms: a constant tax, present before any task work begins.</p>
<div id="c_box"></div>
<p class="note">Box = interquartile range with median line, whiskers to p90, dots = outliers beyond 1.5 IQR. Trimming
outliers narrows every arm but changes no ordering: the fork gap is in the body of the distribution, not the tail.
Axis capped at 45s; clipped outliers render as +. The single largest stall in the dataset is a 332s API-retry pause
inside the experiential-analysis arm's zilloft-10 marathon, unrelated to the fork mechanism.</p>
<h3>Where the minutes actually went: work vs delivery</h3>
<p class="note" style="margin-top:2px"><b>Vocabulary for this block.</b> A <b>turn</b> is one model step: read the
situation, emit one tool call, get the result. <b>Work</b> = how many turns a run needs to finish the 12 tasks: turns
measure searching, clicking, checking. <b>Pace</b> = seconds each turn takes. <b>Work savings</b> = turns the fork did
NOT need because it already knew the apps (it searched less). <b>Reading tax</b> = the extra seconds EVERY fork turn
pays because the whole study transcript sits in front of the conversation and is re-processed on each call
(~300-500k tokens re-read per turn, worth roughly +3 to +6 s/turn here). Total time = work &times; pace, so:
<b>fork time = cold time &minus; work savings + reading tax</b>.</p>
<div id="c_waterfall"></div>
<p class="note">Reading the waterfall: start at the cold baseline's actual 12-task total. The green step is the work
the fork's knowledge genuinely eliminated, priced at cold's pace: the experiential fork needed 76 FEWER turns than
cold (for example zilloft-9 took cold 106 turns but the fork only 68), which would have made it ~5 minutes FASTER than
cold if each turn had cost the same. The red step is the reading tax those remaining turns actually paid. The tax
outweighs the savings roughly 8-to-1 (experiential) and dwarfs the expert fork's small extra-work term too.</p>
<div id="c_turnscmp"></div>
<p class="note">The savings are real: turns needed per task, cold vs the experiential fork. The fork's bar is shorter
on 10 of 12 tasks: knowing the apps genuinely cut the searching and checking. The one big exception (zilloft-10) is
the checkpoint misleading it into hand-counting listings. Speed is a different question from work: each of those
shorter bars was made of much slower turns.</p>
<div class="callout"><strong>Terminology, once.</strong> RAW MOUNT (2A/2B) = the untouched traces/recordings placed on
disk at ./experience/ next to the task. ANALYSIS MOUNT (3C/3D) = the compressed per-site ANALYSIS docs on disk. FORK
(4A/4B) = no files needed: the study session itself, resumed and forked, knowledge in the context window. The baseline
is none of these: a cold agent with the fixed harness. Mounted knowledge is pay-per-read (and the agent mostly does not
read it); forked knowledge is pay-every-turn.</div>
</div>
"""

page_mid = """
<h2>2 &middot; Arm toggles</h2>
<div class="togglebar" id="togglebar"></div>

<h2>3 &middot; Itemized latency and accuracy, per task</h2>
<div class="card">
<div id="c_taskbars"></div>
<p class="note">Grouped bars: minutes per task for the toggled arms; a red F under a bar marks a failed verdict. Click
any task label for the full cross-arm drill-down.</p>
<div id="c_passgrid"></div>
</div>

<h2>4 &middot; Semantic categories: who wins where</h2>
<div class="card">
<div id="c_cats"></div>
<div id="cat_table"></div>
<p class="note" id="cat_notes"></p>
</div>

<h2>5 &middot; Task drill-down</h2>
<p>Click a row for the itemized per-arm anatomy (time, turns, pace, first action, verdicts, failing answers).</p>
<div class="scroll"><table id="taskindex"></table></div>

<h2>6 &middot; Method complexity vs task difficulty (post-fix only)</h2>
<div class="card">
<p style="margin-top:0"><strong>Question: judged against the cold baseline, how does each way of providing
context behave as tasks get harder?</strong> Methods ordered by machinery: raw mounts (2A/2B: untouched material on
disk) &rarr; analysis mounts (3D/3C: compressed briefs on disk) &rarr; forks (4A/4B: the study session in context).
Hardness measured two ways: the labeled tier and the cold arm's own minutes on the task (the labels are miscalibrated:
post-fix medium runs FASTER cold than easy, 1.6 vs 1.8 m/task, so the empirical axis is the honest one).</p>
<div id="c_tierben"></div>
<p class="note">Benefit = cold minutes minus method minutes on the same task (positive = method faster). The mounted
methods are difficulty-FLAT: every tier mean sits within &plusmn;0.7m of zero except one cell, 3D's hard tier, which is
a single catastrophic task (zilloft-10, 121 turns of hand-pagination), not a trend. The forks are negative in every
tier and worst where tasks are hardest.</p>
<div id="c_diffscatter"></div>
<p class="note">Per-task benefit vs empirical hardness, pooled by method class, with least-squares trends. Raw and
analysis mounts: slopes indistinguishable from flat (rank correlations +0.30/-0.06 and +0.54/+0.25, collapsing to
+0.10/-0.38/+0.40/+0.02 without the zilloft-9 marathon; the one that survives, 3D, pairs a positive RANK trend with a
deeply negative hard-tier MEAN, i.e. it helps a little often and catastrophically fails once). Forks: robustly negative
(-0.78 and -0.69, unchanged by the jackknife): more difficulty means more turns means more checkpoint re-reads.</p>
<div id="rho_table"></div>
<div id="c_flips"></div>
<p class="note">Accuracy, post-fix: the cold baseline solves 11/12 (everything but the unwinnable dashdish-8), so a
method can only lose ground here, and the losses cluster in the harder tiers: 0 easy regressions, 4 medium, 3 hard
across the six methods, with the fork arms owning 4 of the 7. No method rescued any task the cold baseline failed.</p>
<div class="callout"><strong>Verdict, post-fix scope.</strong> Difficulty moderation is real but ADVERSE: as method
machinery grows (raw &rarr; analysis &rarr; fork), sensitivity to task difficulty grows in the harmful direction.
Mounted material of either kind is difficulty-neutral noise on a healthy harness; forked context is a difficulty
AMPLIFIER (the tax scales with turns); and on the hardest tasks the best method is the cold baseline itself. The
original hypothesis, restricted to post-fix, is not supported for benefit and inverted for cost.</div>
</div>

<h2>7 &middot; Conclusions</h2>
<div class="card"><ul>
<li><strong>Latency is owned by the harness and the context, not by knowledge.</strong> The two levers that ever moved
whole-task time: fixing input dispatch (phase 1) and NOT carrying a 300-500k-token prefix (phase 4's inverse lesson).
Knowledge delivery on disk is latency-neutral; knowledge delivery in context costs 2.6-5.7s per turn at these sizes.</li>
<li><strong>Where accuracy moved, it moved for three reasons only:</strong> the broken dashdish-8 rubric (0 of 18 arms),
judge phrasing sensitivity on the filtered-counting group (same numeric answers pass and fail across arms), and one real
capability effect: the experiential fork inheriting its checkpoint's failures. No experience condition beat cold's
11/12 anywhere.</li>
<li><strong>Category anatomy:</strong> cart flows are the harness showcase (every OCIC arm beats every CinC arm on every
cart task); tour forms are the longest tasks and the only group where compressed analysis reliably saved time (the
header-count recipe); filtered counting is judge-lottery territory where verdicts, not capabilities, differ; homepage
reading is trivially fast everywhere and dashdish-8 is unwinnable.</li>
<li><strong>If forks are to win, the checkpoint must shrink:</strong> compact the study session (summary-distill, then
fork), or cache-pin the prefix with rollout scheduling inside the TTL, or deliver the distilled knowledge as a system
prompt rather than a transcript. At 65k tokens/turn the fork design would break even on its turn savings.</li>
</ul></div>

<div id="detail"><span class="x" onclick="document.getElementById('detail').classList.remove('open')">&times;</span><div id="detailbody"></div></div>
"""

