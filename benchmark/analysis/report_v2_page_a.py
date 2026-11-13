# Page assembly (head) for build_report_v2.py — pure refactor,
# behavior unchanged.

from report_v2_data import *
from report_v2_charts import *

kpi = f"""
<div class="kpis">
<div class="kpi"><div class="n">18 arms · 0</div><div class="l">arms that ever passed dashdish-8 (the rubric-ambiguity task)</div></div>
<div class="kpi"><div class="n">12/12 · 2.2x</div><div class="l">tasks where OCIC beats CinC on action round-trip, reproduced in 3 CinC runs</div></div>
<div class="kpi"><div class="n">24.5 &asymp; 23.4m</div><div class="l">CinC under setup parity vs OCIC: whole-task dead heat (p=.44)</div></div>
<div class="kpi"><div class="n">+1.5 to +2.9 m/task</div><div class="l">context tax of forked sessions, replicated in 4 of 4 comparisons</div></div>
<div class="kpi"><div class="n">6&#8594;10&#8594;14&#8594;24s</div><div class="l">first-action latency ladder: cold &#8594; mounted &#8594; expert fork &#8594; experiential fork</div></div>
</div>"""

matrix_js_cells = json.dumps({
    "raw": {"experiential": "exp2a-fixed-brave", "expert": "exp2b-fixed-brave"},
    "analysis": {"experiential": "exp3d-experiential-analysis", "expert": "exp3c-analysis"},
    "fork": {"experiential": "exp4a-experiential-fork", "expert": "exp4b-expert-fork"},
})


PAGE_A = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCIC benchmark · phases 1-4</title>
<style>{CSS}</style></head><body><div class="wrap">

<div class="eyebrow">OCIC BENCHMARK · REAL WEBCLONES · PHASES 1&ndash;4 · POST-FIX · 2026-07-16</div>
<h1>A healthy harness beats every form of experience we tried: mounted, compressed, and forked into context</h1>
<p class="lede">Eighteen arms over the same 12 held-out tasks (dashdish + zilloft), sonnet at medium effort, fresh seeded
tab per rollout, deterministic + judged grading. Phase 1 fixed the harness; phases 2&ndash;4 handed the agent experience
three ways: raw material on disk, compressed analysis on disk, and a checkpointed session forked so the experience sits
in context. At n=12 we argue by showing every pair, effect sizes with bootstrap CIs, task-level win/loss records, and
replication across independent contrasts; exact permutation p-values are footnotes.</p>
{kpi}

<h2>0 &middot; The scorecard</h2>
<div class="card">
<p><span class="verdict v-part">H1 REVISED BY CONTROLS</span><strong>OCIC's real win is per-action latency and orchestration capability; under setup parity, whole-task time and accuracy are equivalent.</strong>
The per-action claim is robust: 0.12s vs 0.27-0.30s median round-trip, OCIC faster on 12/12 tasks in all three CinC runs.
The original whole-task gap was two parts artifact: a fresh control re-run of the June baseline scored 11/12 (was 8/12,
three judged flips, none the other way) and cut the time gap in half; a parity arm that scripts CinC's mandatory
tab-bootstrap preamble closed the rest (24.5 vs 23.4 min raw; 22.6 vs 23.2 excluding the preamble; p=.44). What remains
architectural: the official extension's session-scoped tab groups PROHIBIT orchestrator-prepared tabs (verified live),
so its agent must always self-bootstrap; OCIC accepts orchestrated setup.</p>
<p><span class="verdict v-deb">H2 NOT SUPPORTED</span><strong>Mounted priors do not move a healthy harness.</strong>
Cold is 11/12 at 1.95 min/task. Raw mounts: 9/12 and 11/12, &plusmn;0.5 min/task with mixed win/loss records. Compressed
analysis: 11/12 and 10/12, +0.05 min/task (6-6 record) for the expert version. Nothing separates from baseline.</p>
<p><span class="verdict v-deb">H3 REFUTED, WITH A MECHANISM</span><strong>Forked in-context experience is strictly worse here: it cannot be ignored, so it taxes every turn.</strong>
Both forks lose time on 11 or 12 of 12 tasks against cold (+1.96 and +2.76 min/task; CIs exclude zero by a wide margin)
with no accuracy gain (10/12, 8/12 vs 11/12). The mechanism is visible at three levels: forks start acting 2-4x later,
run fewer turns, and pay more seconds per turn.</p>
<p><span class="verdict v-part">H4 SOURCE MATTERS ONLY WHEN DELIVERY IS HEAVY</span><strong>Expert vs experiential: indistinguishable when compressed, decisive when forked.</strong>
As analysis docs the two sources tie (11 vs 10, one discordant task). As forks, the expert checkpoint (all-positive
study, max effort) beats the experiential one (carries 3 failed train segments): 10/12 vs 8/12, faster on 8-4 tasks,
and it flipped two of the experiential fork's three real failures. In-context delivery amplifies prior quality, both ways.</p>
</div>

<h2>1 &middot; The delivery matrix (click any cell)</h2>
<p>The experiment is a 3&times;2 grid: how experience is delivered &times; where it came from, all against the same cold
baseline. Pass count, mean minutes per task, and the one-time preparation cost.</p>
<div id="matrix" class="matrix"></div>
<p class="note">Amortization never arrives: at 12 tasks, no experience arm has repaid its preparation, and the fork arms
also pay a per-task context tax with no accuracy return. Cold reference: <b>11/12 · 1.95 m/task · 0 prep</b> (OCIC Brave) /
9/12 · 2.21 (OCIC Chrome) / CinC control 11/12 · 2.73 / CinC parity 9/12 · 2.04 (both parity fails are judge-phrasing
noise; the June CinC original, 8/12 · 3.50, did not reproduce and is retained only as history).</p>

<h2>2 &middot; Study 1: the harness (OCIC vs official CinC), with controls</h2>
<div class="card">
<p style="margin-top:0"><strong>Three CinC runs tell the story in layers.</strong> The June original (8/12, 42 min) does
not reproduce: an identical fresh control scored 11/12 in 32.8 min (three judged tasks flipped F&rarr;P, none P&rarr;F;
its 18-minute zilloft-9 churn was an episode, not a property). A second control adds setup parity: the official
topology forces the agent to create its own session-scoped tab group and navigate to the app inside the timed run, so
the parity arm scripts that preamble deterministically. Result: whole-task dead heat with OCIC.</p>
{ev_table(["s1chrome", "s1brave", "s1control", "s1parity", "s1pc"],
"Positive &Delta; = A slower. Rows 1-2 use the unrepresentative June baseline and OVERSTATE the gap; row 3 is the honest topology-default comparison; row 4 is the setup-parity comparison (dead heat); row 5 isolates the preamble-scripting effect itself.")}
<p><strong>What stays true across all three CinC runs:</strong> per-action round-trip medians of 0.26-0.30s vs OCIC's
0.12s (screenshots 0.34s vs 0.07s; find 2.4s vs 0.02s), OCIC faster on 12/12 tasks each time. A focus-adjustment
heuristic (calls &gt;1.5s replaced by the tool's clean median, applied symmetrically) moves CinC's mechanical time only
3.3&rarr;2.7 min and flags find-search calls, not input events: zero of 141 control clicks stalled, so background-tab
throttling does NOT explain the per-action gap. And an architectural finding from the failed persistent-tab design:
the official extension scopes tab control to a per-session tab group; a tab created by one session cannot be driven by
another (javascript_tool and get_page_text refuse; verified live, twice). Orchestrated setup is impossible for the
official system by design, which is exactly the capability OCIC's spawnable server adds.</p>
<h3>As-run vs focus-adjusted (the active-tab question, quantified)</h3>
<p class="note" style="margin-top:2px">During these runs the acted-on tab was not guaranteed to be the active/visible
tab, and background tabs are known to throttle synthesized input. Adjustment heuristic, applied identically to every
arm: any browser call with round-trip &gt;1.5s is treated as a possible visibility artifact and replaced by that tool's
own clean (&le;1.5s) median; the adjusted 12-task total subtracts the difference. This is deliberately generous: it
assumes EVERY slow call was a focus artifact.</p>
{focus_table()}
<p class="note">The adjustment moves no arm by more than 0.9 min and changes no ranking: the parity dead heat and the
per-action gap both stand. The flagged calls are dominated by find (element search, not input dispatch); input events
show no stall signature (0 of 141 control clicks &gt;1.5s), which is how genuine background-tab throttling would present.
Conclusion: tab visibility cannot account for the observed differences.</p>
<div class="callout"><strong>Judge sensitivity, exposed by the controls.</strong> The parity arm's two non-dashdish-8
fails are phrasing lotteries: zilloft-2's answer "147" is the same number the cold baseline PASSED with (phrasing
omitted "exactly"), and zilloft-10's "160" passed in one arm and failed in two others. The &plusmn;2-3 task noise floor
this implies applies to every single-run arm in this report.</div>
</div>

<h2>3 &middot; Study 2: mounted experience (raw and compressed)</h2>
<div class="card">
<p style="margin-top:0">Four arms mount experience on disk next to the task. None separates from cold: effect sizes are
within &plusmn;0.5 min/task with straddling CIs and near-even records. The agent barely opens the material (expert
analysis read in 7/12 rollouts, experiential in 3/12, raw mounts near zero on a healthy harness).</p>
{ev_table(["s2_2a", "s2_2b", "s2_3d", "s2_3c"])}
</div>

<h2>4 &middot; Study 3: forked experience, and the context tax</h2>
<div class="card">
<p style="margin-top:0"><strong>Every fork comparison, same direction.</strong> Against cold and against their own
mounted counterparts, both forks lose wall-clock on nearly every task. The effect replicates in four independent
contrasts; the accuracy column never compensates.</p>
{ev_table(["s3_4a", "s3_4b", "s3_4b3c", "s3_4b2b", "s3_4a3d", "s3_4a2a", "s3_4b4a"],
"The one positive: within forks, the expert checkpoint beats the experiential one on time (8-4) and accuracy (+2 tasks), the delivery-amplifies-quality result.")}
<h3>Every pair, shown</h3>
<div style="display:flex;flex-wrap:wrap;gap:10px">
{slope_chart("exp4b-expert-fork", "exp1a-fixed-brave", title="cold → expert fork (min/task)")}
{slope_chart("exp4a-experiential-fork", "exp1a-fixed-brave", title="cold → experiential fork")}
{slope_chart("exp4b-expert-fork", "exp3c-analysis", title="expert analysis → expert fork")}
</div>
<p class="note">Red lines rise (fork slower), green fall. No aggregation: each line is one task. The pattern needs no test.</p>
<h3>The mechanism</h3>
{ladder_chart()}
<h3>Turns down, time up</h3>
{scatter_turns_time()}
<p class="note">Hollow = raw mount, solid = analysis mount, dashed ring = fork. Forks sit upper-LEFT: fewer turns
(the knowledge does reduce search) at far higher minutes (context processed on every one of them). Neither fork
consulted its on-disk materials even once (0 reads; the mounted-analysis arm read its docs 13 times), so the effect is
purely in-context. First-turn cost alone: cold 6s, expert fork 14s, experiential fork 24s.</p>
</div>

<h2>5 &middot; Per-task explorer</h2>
<p>Toggle arms, click a row for the full per-arm breakdown of a task (verdicts, minutes, turns, failing answers).</p>
<div class="togglebar" id="togglebar"></div>
<div class="scroll"><table id="taskgrid"></table></div>

<h2>6 &middot; Arm census (sortable)</h2>
<div class="scroll"><table id="census"></table></div>
<p class="note">per-turn s = total run seconds / total turns. first-action = median seconds from run start to the first
browser tool call. reads = opens of ./experience or notes files during test rollouts. ec = execute_code calls (never
mentioned in any post-fix prompt except 3B's encouragement; violations impossible, usage free).</p>

<h2>7 &middot; Failure anatomy</h2>
<div class="card">
<ul>
<li><strong>dashdish-8, 0 of 16 arms ever.</strong> "First three categories of deliverable food": every arm answers
from the cuisine carousel; the rubric wants the curated collection rows. No harness, prior, or delivery mode touches it:
task-specification failure. Exhibits in the <a href="archive/benchmark_report_postfix_v1.html#dd8">archived deep dive</a>.</li>
<li><strong>The location-mirage pair (zilloft-5, zilloft-10).</strong> The app's location search barely filters; judged
answers that acknowledge the mirage pass, bare header counts fail. These two account for most non-dashdish-8 failures
across arms, including two of the experiential fork's three misses.</li>
<li><strong>zilloft-2 in both forks.</strong> Filter semantics ("exactly 3 bd" vs "3+ bd"): both forks skipped the
exact-match toggle that the expert material demonstrates, cold passed it. The expert fork's scored attempt ran clean and
post-reset (its two rate-limited attempts were quarantined, never scored, evidence on disk).</li>
<li><strong>The experiential fork's checkpoint carries failure.</strong> Its study session failed 3 of 6 train segments
(uncurated by design); its forks then under-performed the all-positive expert checkpoint by 2 tasks and 0.8 min/task.
Context is not ignorable: bad experience in-context is worse than no experience.</li>
</ul>
</div>

"""
