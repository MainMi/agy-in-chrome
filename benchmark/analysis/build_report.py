#!/usr/bin/env python3
"""Generate benchmark_report.html from analysis JSONs.

Inputs : analysis/harvest.json, analysis/stats.json, analysis/amortization.json,
         archive/benchmark_report_pre_fix.html (dashdish-8 exhibits, ported)
Output : benchmark_report.html (self-contained)

Reproduce: python3 analysis/harvest.py && python3 analysis/stats.py &&
           python3 analysis/deepdive.py && python3 analysis/build_report.py
"""
from report_data import *
from report_charts import *

figs = re.findall(r'<figure class="shot">.*?</figure>', OLD, re.S)
assert len(figs) == 3, f"expected 3 dd8 exhibits, found {len(figs)}"

acts = {a: A[a]["med_act"] for a in ("exp1a-fixed-chrome", "exp1a-fixed-brave", "exp1b-cinc-cold")}
speedup = acts["exp1b-cinc-cold"] / statistics.mean([acts["exp1a-fixed-chrome"], acts["exp1a-fixed-brave"]])
repl_total = sum(A[a]["replays"] for a in list(ARM_META))

page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCIC benchmark · post-fix studies</title>
<style>{re.search(r"<style>(.*?)</style>", OLD, re.S).group(1)}</style></head><body><div class="wrap">

<div class="eyebrow">OCIC BENCHMARK · REAL WEBCLONES · POST-FIX STUDIES · 2026-07-15</div>
<h1>The harness is what got faster: OCIC beats the official stack on every task's round-trip, and a healthy harness absorbs the pre-training effect</h1>
<p class="lede">Two paired studies on the same 12 held-out REAL webclone tasks (dashdish, zilloft), sonnet at medium effort,
one fresh tab per rollout, deterministic + judged evaluation. Study 1 compares the fixed OCIC extension against official
Claude in Chrome. Study 2 asks what compressed prior experience (expert vs the agent's own) is still worth once the
harness is healthy. All tests are exact paired permutation tests; accuracy is the guardrail everywhere.</p>

<div class="kpis">
<div class="kpi"><div class="n">0.12s vs 0.26s</div><div class="l">median browser-action round-trip, OCIC-fixed vs official CinC ({speedup:.1f}x)</div></div>
<div class="kpi"><div class="n">12/12 · p=.0005</div><div class="l">tasks where OCIC's per-action median beats CinC on the same browser (exact floor at n=12)</div></div>
<div class="kpi"><div class="n">&minus;0.65 min/task</div><div class="l">run time, Brave arm vs CinC on tasks both passed (p=.008)</div></div>
<div class="kpi"><div class="n">11/12 cold</div><div class="l">post-fix baseline accuracy with no prior experience at all</div></div>
<div class="kpi"><div class="n">0/12 arms</div><div class="l">dashdish-8 passes nowhere; verdict unchanged from the pre-fix deep dive</div></div>
</div>

<h2>1 &middot; Study 1: OCIC vs official Claude in Chrome</h2>
<p><span class="verdict v-conf">H1 CONFIRMED</span><strong>Hypothesis: OCIC performs no worse than the official stack, possibly marginally better.</strong>
It is never worse, and where the comparison is powered it is significantly faster. The cleanest signal is harness
round-trip time, which excludes model thinking: OCIC's per-task median action latency beats CinC on 12 of 12 tasks on the
same browser (Chrome), p=.0005, the smallest p an exact paired test can produce at n=12. In-harness time per task is
{A['exp1a-fixed-chrome']['tot_act']:.0f}s vs {A['exp1b-cinc-cold']['tot_act']:.0f}s (p=.021).</p>

<div class="card"><h3 style="margin-top:2px">per-task median action round-trip, same browser (Chrome)</h3>{paired_dot_chart()}
<p class="note">One row per test task; the connecting bar is the gap. OCIC-fixed is left of CinC on every row.
Round-trip = tool_use to tool_result wall time across all browser MCP calls in the rollout trajectory.</p></div>

<h3>Task completion time and accuracy</h3>
{stat_table([("OCIC fixed (Chrome) vs CinC, same browser", T_CHROME), ("OCIC fixed (Brave) vs CinC", T_BRAVE)])}
<p>Whole-task time is mostly model thinking, so harness gains dilute: the same-browser comparison is directionally faster
(&minus;1.29 min/task) but not significant (p=.14), dominated by outliers on failed tasks. The Brave arm is significant on all 12
(p=.007) and stays significant restricted to tasks both arms passed (&minus;0.65 min/task, 8/8 tasks faster, p=.008).
Accuracy never favors CinC: every discordant task flips toward OCIC (3+/0&minus; on Brave, 2+/1&minus; on Chrome), though
n=12 has no power to certify accuracy gaps (McNemar p&ge;.25). CinC's 18-minute zilloft-9 failure is the single largest
time entry in the whole dataset.</p>

<div class="callout"><strong>Caveats, stated plainly.</strong> CinC ran three weeks earlier than the fixed arms (same model,
same CLI family, same tasks, same evaluator; the OCIC fix does not touch the official extension). The Brave-vs-CinC
comparison crosses browsers; the same-browser Chrome comparison is the primary and its per-action result carries the
conclusion. zilloft-10's LLM-judged verdict is noisy: it accepted answers of 12, 13, and one of two 160s; zilloft-5 shows the same
pattern (a bare '3 results' fails, '3 shown but only 1 in San Jose' passes). Treat those cells as grading noise plus a
test of noticing the location-filter mirage, not pure capability signal.</div>

<h2>2 &middot; Study 2: what is pre-training + analysis still worth?</h2>
<p><span class="verdict v-deb">H2 NOT SUPPORTED POST-FIX</span><strong>Hypothesis: compressed prior experience makes runs faster, more effective, higher-accuracy.</strong>
That was true on the broken harness; the fix absorbed it. Pre-fix, priors lifted accuracy from 8/12 (cold) to 11/12
(expert). Post-fix, the cold baseline alone reaches 11/12 at {A['exp1a-fixed-brave']['run_min']/12:.1f} min/task, and neither analysis arm moves
either number: expert analysis is +0.05 min/task (p=.81) with literally zero discordant tasks against baseline; the
experiential arm is one task behind (10/12, McNemar p=1.0). The accuracy guardrail holds, with no regressions anywhere, but the measured benefit is gone.</p>

<div class="card"><h3 style="margin-top:2px">the fix absorbed the prior: accuracy and pace, before vs after</h3>{bridge_chart()}</div>

{stat_table([("3C expert analysis vs cold baseline (both Brave)", T_3C), ("3D experiential analysis vs cold baseline", T_3D), ("3C expert vs 3D experiential", T_3C3D)])}

<p><strong>Expert vs experiential source.</strong> The two analysis docs were produced by the same method from different
raw material (operator demonstrations vs the agent's own train-split rollouts). They are statistically indistinguishable
(p=.47 on time; one discordant task on accuracy). Self-distilled experience is as good as expert demonstrations once
compressed, and it is the cheaper pipeline, since it needs no operator.</p>

<p><strong>Why no effect? The agent barely consults the prior, and no longer needs it.</strong> 3C read its analysis docs in
7/12 rollouts, 3D in only 3/12 (always before acting when read at all). The one task where the doc's recipe demonstrably
mattered cut both ways: on zilloft-10, 3C read the doc and answered from the filtered header count (pass); 3D skipped the
doc, hand-paginated 160 listings across 4 pages for 121 turns, and failed with 158. The knowledge is right; compliance is
the bottleneck, and a healthy harness makes the floor high enough that skipping the docs usually costs nothing.
execute_code tells the same story it told pre-fix: encouragement inflates usage (32 calls in 3B) but silence nearly
eliminates it (4 in 3C, 7 in 3D) with identical outcomes. It is a red herring for performance.</p>

<div class="card"><h3 style="margin-top:2px">total time, preparation stacked onto runs (preserved view)</h3>{totals_chart()}
<p class="note">Preparation = source material + analysis authoring: 17m operator recording + 3.5m authoring for the expert
arms; 26.1m of agent train-split runs + 6.5m authoring for the experiential arm (file-timestamp measured). Cold arms pay nothing.</p></div>

<div class="card"><h3 style="margin-top:2px">amortization: cumulative time vs number of tasks (preserved view)</h3>{amortization_chart()}
<p class="note">Hollow markers are the one-time preparation offset. Post-fix, the prior-experience lines never catch the
cold baselines within the 12-task horizon: there is nothing left to amortize against. Pre-fix (archived report), the
gap they had to close was 2x wider.</p></div>

<div class="card"><h3 style="margin-top:2px">does the prior save more time on longer tasks?</h3>{SAV_SVG}
<p class="note">One point per test task per arm. x = the cold baseline of that era's minutes on the task (task length);
y = minutes the pre-trained arm saved on the same task (above the zero line = prior was faster). Hue = experience source
(pink experiential, emerald expert); hollow = raw traces, solid = compressed analysis. Off-scale points are clipped to
the border; hover any point for exact values.</p>
{SAV_TABLE}
<p class="note">Read: the correlation is positive in both eras but it is substantially a one-task story. zilloft-9, the
marathon (rightmost points), carries most of the savings; on the other eleven tasks the differences hover within about a
minute of zero. The prior pays off roughly in proportion to task length, and only the longest task in the suite is long
enough for it to matter.</p></div>

<h2>3 &middot; Accuracy grid (preserved view)</h2>
<p>Pass/fail identity for every arm; muted columns are the archived pre-fix arms. The post-fix suite is near-ceiling:
most current arms sit at 10&ndash;11 of 12 (the raw-traces arm dips to 9), and the failures concentrate in three
tasks: dashdish-8 (universal, below) and the two location-mirage counts, zilloft-5 and zilloft-10 (judged tasks that
reward noticing the app's location filter barely filters; bare header-count answers fail).</p>
{accuracy_grid()}

<h2 id="dd8">4 &middot; Deep dive: dashdish-8, still the task no arm can pass</h2>
<p>Ported from the pre-fix report and re-verified against the six current arms: <strong>0 of 12 arms have ever passed
dashdish-8</strong>, and the failure signature is identical post-fix: every arm answers fast (0.13&ndash;0.35 min,
3&ndash;9 turns) and wrong. The task: <em>"What are first three categories of deliverable food displayed on the
homepage?"</em> The rubric wants the first three curated collection rows ("Under $1 delivery fee", "Best of lunch",
"The Infatuation's picks"), verified post-hoc as literally the first three section headers in both DOM and visual
order. Every arm instead answers from the cuisine icon carousel at the top (Breakfast / Fast Food / Coffee). The same
taxonomy misreading, twelve independent times, across both harnesses, every experience condition, and with code
forbidden, permitted, and unmentioned. Neither analysis doc prevents it: both note the cuisine bar is a separate
taxonomy from the collections, but neither says which one "categories" means, and the ambiguity wins every time.
The three exhibits below are the original evidence, unchanged.</p>
{''.join(figs)}

<h2>5 &middot; The pre-fix record, corrected and archived</h2>
<p>The earlier report attributed OCIC's slow clicks to a Brave-specific debugger-ack quirk. That was wrong. The root cause
was <strong>background-tab input throttling</strong>: any Chromium stalls synthesized input ~5s to a non-visible tab
(measured live: 0.001s foreground vs 5.13s background for the same click on Chrome). The fix activates the workspace tab
once at creation, never stealing OS focus, and cut mean in-harness time per task from {A['exp1a-chrome']['tot_act']:.0f}s to
{A['exp1a-fixed-chrome']['tot_act']:.0f}s on Chrome (p=.032, 7x). OS focus is irrelevant to latency (verified: 0.002s with
Chrome visible but unfocused). Six pre-fix arms are preserved in the
<a href="archive/benchmark_report_pre_fix.html">archived report</a>; their totals appear muted in the grid above.</p>

<div class="scroll"><table><thead><tr><th>pre-fix arm</th><th>passed</th><th>12-run time</th><th>note</th></tr></thead><tbody>
{''.join(f"<tr><td>{esc(PREFIX_LABEL[a])}</td><td class='num'>{A[a]['passed']}/12</td><td class='num'>{A[a]['run_min']:.0f}m</td><td>{esc(n)}</td></tr>" for a, n in [
    ("exp1a-ocic-cold", "headline baseline, throttled inputs"),
    ("exp1a-chrome", "same, Chrome; the arm that exposed the 67-minute wall clock"),
    ("exp2a-experiential", "raw self-traces mounted; +2 tasks over cold"),
    ("exp2b-expert", "raw expert recordings; +3 tasks over cold"),
    ("exp3a-code", "expert raw + execute_code encouraged"),
    ("exp3b-code-analysis", "first compressed-analysis arm; fastest pre-fix"),
])}
</tbody></table></div>

<h2>6 &middot; Methods &amp; data integrity</h2>
<ul>
<li><strong>Pipeline.</strong> Per rollout: fresh tab &rarr; navigate &rarr; clear cache &rarr; /config seed &rarr; verify clean /finish &rarr;
detached <span class="mono">claude -p --model sonnet --effort medium</span> &rarr; capture /finish &rarr; close tab &rarr; evaluate
(REAL WebCloneEvaluator: jmespath deterministic checks + rubric-judged retrieval). Artifacts per rollout: prompt, raw result,
trajectory, finish state, evaluation, timing.</li>
<li><strong>Statistics.</strong> Exact paired sign-flip permutation test on mean per-task difference (4096 patterns at n=12),
exact Wilcoxon signed-rank alongside (agrees everywhere), exact McNemar for accuracy. Time comparisons reported twice:
all 12 pairs and the pass-both subset (a failed run's duration measures something else). Six planned comparisons, nominal p values.</li>
<li><strong>Replays.</strong> {repl_total} timeout-exceeded replays occurred within the six current arms; every scored trajectory is a clean single attempt. Pre-fix replay counts live in the archived report.</li>
<li><strong>Taint handling.</strong> One 3D rollout (zilloft-9) was interrupted and operator-touched mid-run; it was discarded and
rerun clean along with the three tasks behind it. The rerun passed all six checks.</li>
<li><strong>Known grading noise.</strong> zilloft-10 (LLM-judged) accepted 12, 13, and one of two 160-answers across arms;
zilloft-5 rewards acknowledging the location-filter mirage (bare counts fail). dashdish-8's rubric contradiction is
section 4. All affect every arm symmetrically.</li>
<li><strong>Earlier false alarm.</strong> Pre-fix runs paused on spurious rate-limit detections (a 429 regex matching inside JSON numbers);
detection is now failure-gated with digit boundaries. No current-arm rollout hit a real throttle.</li>
<li><strong>Reproduce.</strong> <span class="mono">python3 analysis/harvest.py && python3 analysis/stats.py && python3 analysis/deepdive.py && python3 analysis/build_report.py</span></li>
</ul>

<p class="note" style="margin-top:40px">OCIC benchmark · REAL webclones (dashdish, zilloft) · 12 held-out test tasks ·
sonnet, medium effort · exact paired tests · generated {__import__('datetime').date.today().isoformat()} ·
archived pre-fix report: <a href="archive/benchmark_report_pre_fix.html">archive/benchmark_report_pre_fix.html</a></p>
</div></body></html>"""

out_p = os.path.join(BENCH, "benchmark_report.html")
open(out_p, "w").write(page)
print("wrote", out_p, f"({os.path.getsize(out_p)/1024:.0f} KB)")

