# Capstone page assembly for build_capstone.py — pure refactor,
# behavior unchanged.

from capstone_data import *

PAGE_A = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCIC benchmark &middot; post-fix capstone</title><style>{CSS}</style></head><body><div class="wrap">
<div class="eyebrow">OCIC BENCHMARK &middot; POST-FIX CAPSTONE &middot; COLD BASELINES THROUGH PHASE 5 &middot; 2026-07-17</div>
<h1>Every way we tried to beat a cold browser agent, and the one that finally did</h1>
<p class="lede">Thirteen post-fix configurations on the same 12 held-out REAL webclone tasks (dashdish, zilloft), sonnet at
medium effort, fresh seeded tab per rollout, deterministic + judged grading. This report walks each arm in order: the
three cold baselines, then four ways of delivering prior experience. It asks two questions of each: is it more
accurate, and is it faster. The answer is a story about delivery, not knowledge.</p>
{kpis}

<h2>1 &middot; The arms, in order</h2>
<div class="card">{arm_registry_html()}</div>
<p class="note">Prep = one-time cost to produce the experience (recording, generation, study, or recipe authoring),
excluded from the per-task run times below and reported separately. tok/turn = context carried per model turn, the
lever that turned out to matter most.</p>

<h2>2 &middot; Accuracy</h2>
<div class="card">
<div class="charttitle">Accuracy by arm <span class='sub'>tasks passed of 12</span></div>
<div id="c_acc"></div>
<p class="note">Tasks passed of 12, deterministically re-graded. <b>Two grading problems, corrected separately.</b>
First, dashdish-8 is a broken rubric: all 13 arms give the cuisine-carousel answer, and the rubric's ground-truth answer
is the curated collection rows, which no arm produces. The single judged pass (5D) was re-evaluated to check consistency
and came back <b>3 pass / 2 fail over 5 runs</b>, confirming the LLM judge is a coin flip on the identical answer, so we
fall back to the rubric ground truth and mark dashdish-8 fail for all 13 (the original judged verdict is preserved on
disk). Second, three tasks (zilloft-2, zilloft-5, zilloft-10) ask for an exact listing count, and the same judge disagreed
with itself there too: reading every run's actual reported number against the rubric's stated correct count overturned
<b>7 of the 39 arm&times;task verdicts on those three tasks alone, all of them false positives</b> (the grader passed a
wrong count, never failed a right one). Every arm's score above is the corrected count. Accuracy still cannot separate
the methods cleanly, the corrected range is a narrow 8 to 11 of 12, but it is no longer flat, and it is no longer
trustworthy to read off the raw judged verdicts.</p>
<div class="charttitle">Pass, slow, or fail <span class='sub'>every arm against every task</span></div>
<div id="c_accgrid"></div>
<p class="note"><b style="color:#0f8a5f">&#9679;</b> pass &nbsp; <b style="color:#ca8a04">&#9679;</b> passed but
<b>slow for that arm</b> (a within-arm upper outlier: its time is a robust outlier against that arm's own task times,
so it flags "this task underperformed here", independent of how long the task is elsewhere) &nbsp; <b style="color:#c13a2e">F</b> fail.
The failures concentrate in four tasks: dashdish-8 (broken rubric, universal) and the location-mirage counts zilloft-2 /
zilloft-5 / zilloft-10 (grader-inconsistent; corrected against the rubric's ground-truth count, &sect;2 above). The yellow
marks vary by arm and are the more interesting signal: 4B's slow spot is zilloft-5 (not the usual marathon), 3D's is
dashdish-10, and <b>5A has none</b> (uniformly efficient). Cold does not solve everything solvable (it ties the floor at
8/12), so accuracy separates the methods a little, but within-arm slowness is still the sharper signal.</p>
<div class="charttitle">Accuracy per leg <span class='sub'>tasks passed of 12; one value per leg, toggle to focus</span></div>
<div class="ctl" id="ov_acc_ctl"></div>
<div id="c_dist_acc"></div>
<p class="note">Accuracy is a single value per leg (a pass count of 12), not a per-task spread, so instead of a curve each
selected leg is a dot on the score axis (ties stacked). The ceiling is <b>11/12</b> (4 of 13 legs: 2b, 3b, 5b, 6b) and the
floor is <b>8/12</b>, tied four ways by all three cold baselines and 4a. Toggle legs to isolate. The spread is narrow
enough (8 to 11) that accuracy separates the methods only weakly; the whole story is in performance.</p>
</div>

<h2>3 &middot; Performance</h2>
<div class="card">
<div class="ctl">
  <label><input type="checkbox" id="t_task" checked onchange="renderPerf()"> Task time (12 runs)</label>
  <label><input type="checkbox" id="t_prep" checked onchange="renderPerf()"> Preparation steps</label>
  <span class="sep"></span>
  <label><input type="radio" name="lay" value="stacked" checked onchange="renderPerf()"> Stacked (total)</label>
  <label><input type="radio" name="lay" value="aligned" onchange="renderPerf()"> Aligned (compare)</label>
</div>
<div class="charttitle">Run time per arm <span class='sub'>task time and preparation, toggleable</span></div>
<div id="c_perf"></div>
<div id="perf_legend" class="plegend"></div>
<p class="note"><b>Stacked</b> lays every segment end-to-end so the bar length is the true total cost (prep, then the
12 task runs). <b>Aligned</b> gives each segment its own bar from a shared left edge, so you compare magnitudes directly.
Preparation is now broken into its real steps with a consistent color per step type: producing the source material
(experiential runs, expert recordings) is a shared, reused cost shown for full provenance. The recipe arms carry the
longest prep chain because a recipe is distilled from BOTH raw sources plus one shared authoring session, yet their task
time is near cold. The forks invert it: cheap-ish prep, heavy task time. <b>Preparation is hatched, task time is solid</b>, so the two never blend.</p>
<div class="charttitle">Time saved or lost versus cold <span class='sub'>minutes per arm</span></div>
<div id="c_deltas"></div>
<p class="note">Mean minutes saved vs cold per task (positive = faster than cold). Ordered by phase. The recipe and
atomic-warmup arms hover at zero; the full forks lose 2-3 minutes/task; 5D alone is clearly negative (faster). Every
arm's win, where it has one, comes from the hard tasks.</p>
<div class="charttitle">Latency distribution, per leg <span class='sub'>density of each leg's 12 task times; toggle legs to overlay</span></div>
<div class="ctl" id="ov_lat_ctl"></div>
<div id="c_dist_lat"></div>
<p class="note">Each curve is one leg's distribution over its 12 task times; toggle any legs to overlay them (the default
shows a contrasting few, with a rug of the raw 12 points under each). The shapes diverge: cold is a moderate hump around
one to two minutes; the <b>fork (4A) shifts far right and spreads wide</b>; the <b>warm-up (5D) is tight and pulled
left</b>, the most concentrated; the <b>analysis mount (3D) carries a right tail</b> from one hard task (dashdish-10). Pooled
across all 156 runs the median is 1.9 min, but the per-leg curves are where the methods actually separate.</p>
<div class="charttitle">Consistency, per leg <span class='sub'>mean vs standard deviation of latency; distance from the line is the signal</span></div>
<div id="c_reliability"></div>
<p class="note"><b>Standard deviation on its own is misleading, because it tracks the mean</b> (correlation <b>+0.87</b>
across arms): slow arms simply vary more. The dashed line is what "typical" spread looks like (SD = <b>0.63</b> times the
mean, the median coefficient of variation). What matters is <b>distance from that line</b>, not height. Three readings
fall out, and they revise the mean-only story. <b>The forks sit right on the line:</b> their large SD is entirely a
consequence of their large mean (CV ~0.63, same as cold), so they are <i>uniformly</i> ~2x slow, predictable, not chaotic.
On reliability the fork is not the villain. <b>The recipe and warm-up sit below the line</b> (5A at CV 0.49, 5D at 0.54):
they tighten the relative spread, so run times cluster predictably, a reliability gain stacked on top of the speed gain.
<b>3D sits above it</b> (CV <b>0.90</b>): the analysis mount is fast on most tasks but still has a real tail, a
dashdish-10 run runs 7.7 minutes against a ~1-3 minute norm elsewhere, so its risk is concentrated in a minority of
tasks rather than spread evenly. And this is one underlying leg property: an arm's latency CV and its turn CV correlate
<b>+0.93</b>, a leg that is erratic in time is erratic in path length too.</p>
</div>

<h2>4 &middot; The mechanism: context weight owns latency</h2>
<div class="card">
<p style="margin-top:0">One number explains the entire performance ranking: how many tokens each arm's agent carries
per turn. Cold and mounted arms carry ~54-61k (the task + page). The forks carry the whole checkpoint on every turn.</p>
<div class="charttitle">Context carried per turn <span class='sub'>thousands of tokens, by arm</span></div>
<div id="c_ktok"></div>
<p class="note">Context carried per turn. The phase-4 forks (480k, 251k) are 5-9x everything else, not because they
reason more, but because the entire study transcript is re-processed on every call. Phase 5's atomic warm-up (5C/5D)
cut this to ~92k by keeping only one task of history.</p>
<div class="charttitle">The turn-latency law <span class='sub'>seconds per turn versus tokens carried</span></div>
<div id="c_lawscatter"></div>
<p class="note"><b>The turn-latency law.</b> Each dot is an arm: context carried per turn vs the resulting per-task time
penalty against cold. The line is tight (heavier context, slower). This is why the phase-4 forks lost and why shrinking
the checkpoint (P4&rarr;P5) recovered almost all of it: the loss was delivery weight, never the knowledge itself.</p>
<h3 style="margin-top:26px">Once context is divided out: thinking is flat, turns is the only thing that moves</h3>
<p>Per-turn latency is context, and that is just transformer physics. So we divided context out and asked what else
varies between experiments. There are only two candidates: how much the model <b>generates</b> per turn (its deliberation)
and how many <b>turns</b> it takes. Measured on the SDK's real per-task turn count, the answer is clean and a little
deflating: thinking per turn barely moves at all, and the only behavioral variable is the step count.</p>
<div class="charttitle">Thinking per turn, by experiment <span class='sub'>output tokens per turn: nearly flat across every arm</span></div>
<div id="c_thinkbar"></div>
<p class="note"><b>Thinking per turn is not a lever.</b> Every arm generates ~130 to 170 output tokens per turn (a short
reasoning span plus the tool call), a spread of about &plusmn;7% around cold's ~135. Reading experience (mounts, recipe)
leaves it at cold; the forks nudge slightly higher (148, 168), a mild side-effect of having a whole session to reconcile;
the warm-up is cold-like (128, 136). Whatever prior experience does, it does not change how much the model deliberates per
step. Since total time varies 2.5x while thinking-per-turn holds flat, the time differences cannot be thinking, they are
context, confirmed from the other direction.</p>
<p class="note"><b>What does move is the turn count.</b> A recipe or warm-up cuts steps below cold; raw or analysed docs
on disk push it up (the agent spends turns reading). But turn count is <b>orthogonal to total time</b> (correlation
<b>0.00</b>): taking fewer turns does not make you faster, because per-turn cost varies more than step count does, and
per-turn cost is context. That makes turns a separate axis from latency, a <i>precision</i> axis rather than a speed one,
so we give it its own treatment next in <b>Section 5</b>. The one-liner for this section: thinking is flat, context is
the cost, and turns is a behavior worth measuring on its own.</p>
</div>

<h2>5 &middot; Turns taken: the precision axis</h2>
<div class="card">
<p style="margin-top:0">Latency is one cost of a browser agent; <b>imprecision is another</b>. Every turn is an action on a
live, stateful page, and a wrong action, a filter mis-set, a wrong listing opened, a form half-submitted, has downstream
consequences the agent then has to notice and unwind. The most direct path to the answer is also the one with the
smallest blast radius. Turn count is our measurable proxy for that path length, and, as Section 4 established, it is
<b>independent of latency</b> (correlation 0.00 with time), so a method can make the agent more precise without making it
faster, and the two must be judged separately.</p>

<div class="callout" style="border-left-color:#b45309">
<h4 style="margin:0 0 6px;font-size:12.5px;text-transform:uppercase;letter-spacing:.05em;color:#5b6571">How we count turns</h4>
<p style="margin:0;font-size:13px">A <b>turn</b> is one model step: a single round-trip in which the agent observes the
page, reasons, and emits an action (a tool call). We count turns with the Agent SDK's authoritative per-task
<span class="mono">num_turns</span>, <b>not</b> the raw trajectory length. This matters because the forked warm-up arms
(5C, 5D) resume a prior session, so the warm-up's transcript rides in the trajectory and inflates the raw count by
<b>~7 to 8x</b> (versus a steady ~1.5x for every other arm). The same contamination hits every trajectory-derived action
count (tool calls, browser calls, steps), so <span class="mono">num_turns</span> is the only path-length metric that is
clean for these arms. An earlier version of this report used the raw count and drew the wrong conclusion; this section is
built on the corrected metric.</p>
</div>

<div class="charttitle">Turns versus cold, by method <span class='sub'>fewer = more direct path (green); more = extra steps (red)</span></div>
<div id="c_turndelta"></div>
<p class="note"><b>Carrying knowledge in-context shortens the path; making the agent retrieve it from disk lengthens it.</b>
The warm-up (5D) runs the most direct route, <b>26% fewer turns</b> than cold; recipe and even the fork run ~14 to 19%
fewer, because the knowledge is already in the window and the agent wastes fewer exploratory moves. The disk mounts go the
other way, up to <b>+24%</b>: agentic retrieval is itself navigation, and every file the agent opens is another step that
can go wrong. Note the fork here: it takes among the <i>fewest</i> turns (most direct) yet is the slowest arm overall,
the clearest proof that precision and speed are different axes.</p>

<div class="charttitle">Turn savings versus task length <span class='sub'>turns saved vs cold against naive baseline turns; toggle legs</span></div>
<div class="ctl" id="ts_ctl"></div>
<div id="c_turnscale"></div>
<p class="note"><b>And the path-shortening grows with the task.</b> For the warm-up (5D) the turns saved correlate
<b>+0.86</b> with how many turns the task naively takes; on the longest task in the suite it removes <b>~28 turns</b>, more
than a third of the naive path. Recipe scales the same way (+0.77). The disk mount does the opposite (it adds steps, and
tends to add more on longer tasks). So the precision benefit concentrates exactly where the risk is highest: on long,
multi-step tasks with the most opportunities for a consequential wrong move. The efficient methods do not just finish in
fewer steps, they widen that lead as the task gets longer.</p>
<div class="charttitle">Turn-count distribution, per leg <span class='sub'>density of each leg's 12 task turn-counts; toggle legs to overlay</span></div>
<div class="ctl" id="ov_turns_ctl"></div>
<div id="c_dist_turns"></div>
<p class="note">Each curve is one leg's path-length distribution across its 12 tasks; toggle legs to compare. The
<b>warm-up (5D) sits left and narrow</b> (short, consistent paths), the <b>raw mount (2B) sits right</b> (longer paths),
and cold falls in between; the fork is left-of-cold but with a wider spread. Pooled median is 28.5 turns.</p>
</div>

<h2>6 &middot; Two rankings that disagree: turns vs latency</h2>
<div class="card">
<p style="margin-top:0">We now have two efficiency metrics that measure different things: <b>turns</b> (path directness, Section 5)
and <b>latency</b> (wall-clock time, Section 3). If they ranked the arms the same way, one would be redundant. They do
not. The rank correlation between them is only <b>+0.30</b> (Spearman), so knowing an arm is turn-efficient tells you
almost nothing about whether it is fast. This section puts the two orderings side by side and reads the arms that move.</p>

<div class="charttitle">The reshuffle <span class='sub'>vertical height is proportional to the actual value (turns left, minutes right); crossings = disagreement</span></div>
<div id="c_slope"></div>
<p class="note"><b>Red lines fall, green lines rise.</b> The story lives in the crossings. <b>4A, the experiential fork,
is the whole point</b>: it takes the 2nd-most-direct path of any arm (rank 2 on turns) yet finishes dead last on latency
(rank 13), a plunge of eleven places, because every one of its few, direct turns drags ~365k of context. Efficiency of
path and efficiency of time are not the same thing, and the fork is the proof. Mirroring it, <b>2A, the raw disk mount,
rises seven places</b> (rank 9 on turns to rank 2 on latency): it wanders down a long path, but each of those turns is
cheap, so the wandering is nearly free. Only <b>5D sits at rank 1 on both</b>, the one arm that is both the most direct
and the fastest.</p>

<div class="charttitle">The same arms in scalar space <span class='sub'>turns vs minutes; the bottom-left corner is the goal</span></div>
<div id="c_rankscatter"></div>
<p class="note">Ranks flatten magnitude, so here are the raw values, and the arms fall into <b>three groups that the delivery
mechanism draws for you</b>. <b>Prompt-embedded</b> (green: recipe and warm-up) clusters in the bottom-left prize corner,
few turns and fast, because the knowledge is in the window and costs almost nothing to carry. <b>Cold and on-disk
retrieval</b> (blue: the cold legs plus the raw and analysis mounts) sits just to the right, still fast but on a longer
path, cheap per turn, yet the agent spends extra steps because it has no in-window guidance or must go read files.
<b>In-context forks</b> (red) break away to the top: the context tax strands them there regardless of turn count, 4A
lands in the worst corner despite a near-best path. The asymmetry underneath it all: turns span just <b>1.7x</b> (24 to 40)
while latency spans <b>2.7x</b> (21 to 57 minutes), so being a few turns more direct buys a little, but being context-heavy
costs enormously. Judge a method on turns and latency separately; a good position on one axis is no guarantee on the
other.</p>
</div>

<h2>7 &middot; Hypotheses, tested</h2>
"""
