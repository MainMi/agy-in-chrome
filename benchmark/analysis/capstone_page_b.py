# Capstone page assembly for build_capstone.py — pure refactor,
# behavior unchanged.

from capstone_data import *

PAGE_B = f"""<div class="card">
<p><span class="verdict v-yes">H1 SUPPORTED</span><strong>OCIC is at least as good as the official extension.</strong>
Cold OCIC-Brave, official CinC (setup-parity), and OCIC-Chrome all tie at 8/12 once the grader's inconsistent verdicts
are corrected against ground truth (an earlier apparent OCIC-Brave accuracy edge was two flaky judge passes on wrong
answers, &sect;2). OCIC leads on per-action latency (0.12s vs 0.27s median round-trip); whole-task time is a tie under
setup parity. The big early gap was an unrepresentative old CinC run plus a setup-parity artifact, both corrected.</p>
<p><span class="verdict v-no">H2 REFUTED</span><strong>Mounted prior experience improves a healthy harness.</strong>
Raw mounts 9/12 and 11/12; analysis mounts 10/12 and 11/12; every mean within &plusmn;1 min/task of cold, records
near-even. The agent barely opens the files, and the healthy harness leaves nothing for them to fix.</p>
<p><span class="verdict v-no">H3 REFUTED (with a mechanism)</span><strong>Forking the experience into context helps.</strong>
The full forks are the worst arms in the benchmark: 8/12 and 10/12, +2-3 min/task, because each turn re-reads a
250-490k-token prefix. In-context knowledge cut search (fewer turns) but paid an ~8x reading tax on delivery.</p>
<p><span class="verdict v-part">H4 SUPPORTED (the corollary)</span><strong>The fork's loss is delivery weight, not the
knowledge.</strong> Phase 5's atomic warm-up shrank the checkpoint 480k&rarr;92k and the fork flipped from worst arm to a
tie with cold (11/12, +0.13 min/task). Exactly what the turn-latency law predicts.</p>
<p><span class="verdict v-part">H5 SUPPORTED (narrowly)</span><strong>A cheap, non-distracting recipe can beat cold.</strong>
The recipe alone lands 10/12 and 11/12, at or above cold's 8/12, but its fixed reading cost cancels most of the time
benefit on this easy-heavy suite.
Combined with the atomic warm-up (5D), it is the first arm faster than cold: 20.9 vs 23.4m, faster on 7/12 tasks, the
gains concentrated in the hard tasks, the difficulty effect paying off.</p>
<div class="callout"><strong>The one-line conclusion.</strong> Knowledge never hurt and rarely helped; <em>delivery</em>
decided everything. On disk it is ignored (free, useless); forked whole it is a per-turn tax (expensive, harmful);
distilled to a recipe plus one task of warm-up it is finally net-positive (5D). And it only shows up on hard tasks , 
this suite is at ceiling, so the honest headline is a modest time win, not an accuracy breakthrough.</div>
</div>

<h2>8 &middot; Difficulty is where the wins live</h2>
<div class="card">
<div class="charttitle">Time benefit versus cold, by task difficulty <span class='sub'>easy, medium, hard tiers</span></div>
<div id="c_diffbars"></div>
<p class="note">Mean time benefit vs cold, split by task difficulty, for the arms that ever help. Every positive bar is
in the hard tier; easy tasks show flat-to-negative (the fixed cost of any delivery exceeds the tiny task). This is the
consistent thread across all phases: prior experience pays in proportion to task difficulty, and this suite has too few
hard tasks for it to dominate the totals.</p>
<h3 style="margin-top:26px">The longer the naive task, the more the winning method pays</h3>
<p>Every task carries a baseline latency: what it costs to hand a browser agent the task cold, which grows with the
number of turns the task naively takes. The question that matters for continual learning is whether its benefit grows
with that baseline. It does, and cleanly.</p>
<div class="charttitle">Time saved versus baseline task length <span class='sub'>seconds saved vs cold against naive turn count; toggle legs</span></div>
<div class="ctl" id="ls_ctl"></div>
<div id="c_lengthscale"></div>
<p class="note"><b>The prompt-embedded method (5D, warm-up + recipe) saves more the longer the task is</b> (correlation
<b>+0.73</b> between seconds saved and baseline turn count; 5A recipe alone +0.66). On the shortest tasks it is roughly
break-even, the fixed cost of carrying the recipe eats the gain, but on the longest task in the suite (zilloft-9, ~69
naive turns) 5D returns <b>~106 seconds</b>. The fork runs the other way (correlation <b>&minus;0.42</b>): the longer the
task, the deeper it sinks, because its per-turn context tax compounds over every additional turn. So the two families
diverge with length, prompt-embedded expertise pays off increasingly, in-context history costs increasingly. This suite
is only medium-length; the trend lines say the gap widens on anything longer.</p>
<p class="note" style="margin-top:10px"><b>Accuracy does not scale much, and the dataset is the reason.</b> Every arm lands at
8 to 11 of 12; cold sits at the floor (8/12, tied across all three baseline arms) and most later-phase arms sit a little
above it, up to a 11/12 ceiling reached by four arms. The two things that keep any arm off a perfect score are a broken
rubric (dashdish-8, universal) and, before correction, an inconsistent LLM judge on three count-based tasks (&sect;2).
The suite sits near its accuracy ceiling either way, so it can measure <i>latency</i> gains from continual learning far
more cleanly than <i>accuracy</i> gains. Whether these methods lift success on genuinely hard tasks is a question this
data leaves open; it would need a harder, un-capped suite to answer.</p>
</div>

<h2>9 &middot; How each leg scales with difficulty</h2>
<div class="card">
<p style="margin-top:0"><b>Difficulty is defined per task as an equal blend of its classification (easy/medium/hard)
and its denoised baseline time</b> (the mean run time across the three phase-1 cold legs, averaged to cancel
single-run noise), scaled 0&ndash;10. Then each leg's per-task time is measured against that same 3-leg baseline, and we
ask how that performance moves as difficulty rises.</p>
<div class="charttitle">Difficulty sensitivity <span class='sub'>does each leg hold up as tasks get harder?</span></div>
<div id="c_sens"></div>
<p class="note"><b>Difficulty sensitivity</b> = the slope of (minutes vs baseline) against difficulty, per leg. Negative
(green) = the leg holds up or improves as tasks get harder; positive (red) = it degrades. The picture is unambiguous:
the <b>forks are difficulty-fragile</b> (4A +0.44 min per difficulty point, Spearman +0.58; 4B +0.12/+0.44) because
their per-turn context tax compounds with the extra turns hard tasks demand. Every <b>recipe / warm-up-recipe</b> leg is
flat-to-negative (5D &minus;0.09, 5A/5B ~&minus;0.08): difficulty-robust. Mounts are largely flat overall.</p>
<div class="ctl" id="sc_ctl"></div>
<div class="charttitle">Performance versus difficulty <span class='sub'>per task and leg, with trends</span></div>
<div id="c_diffscatter2"></div>
<p class="note">Each dot is one task at its difficulty (x) against that leg's minutes saved or lost vs the denoised
baseline (y, below zero = faster than baseline). Dashed lines are per-leg trends; toggle legs above. The fork trends
tilt UP with difficulty (they bleed time on the hard tasks); the recipe and 5D trends stay flat or tilt gently down.
The answer to the question: <b>a leg's delivery mechanism decides its difficulty behavior</b>. Carrying knowledge
in-context is a tax that grows with difficulty, while a recipe on the page is a fixed near-zero cost that lets its small
hard-task savings survive.</p>
</div>

<h3>Long is not the same as hard: two axes underneath "difficulty"</h3>
<div class="card">
<p style="margin-top:0">The blend above leans on time, and time hides a fork in the road. A task can eat minutes because it
is <b>long</b> (many routine steps) or because it is <b>cognitively hard</b> (the agent stalls, backtracks, and
sometimes fails outright). Those are different problems, and across the suite they turn out to be nearly independent:
duration and failure rate correlate just <b>&minus;0.24</b>. Worse for the composite, the time-blended difficulty score
tracks duration (<b>+0.67</b>) while staying almost blind to failure (<b>+0.06</b>): it measures <i>how long</i>, not
<i>how hard</i>.</p>
<div class="charttitle">Task landscape <span class='sub'>duration versus failure rate</span></div>
<div id="c_landscape"></div>
<p class="note"><b>x = denoised cold duration; y = failure rate across all 22 arms.</b> Dot color is the hand
classification (easy / medium / hard). The two axes pull the four hard tasks apart: <b>zilloft-9 is the marathon</b>
(longest task, 118 turns, yet fails only 5%: long, not hard), while <b>zilloft-10 is the trap</b> (middling length but
fails 32%: the genuinely hard one). Failure is not even confined to the hard label, zilloft-2 and zilloft-5 are
medium-classified and fail ~30%. And dashdish-8 sits alone at 100% failure with near-zero duration: not hard, just a
broken, judge-random rubric. The time-blend crowns the marathon as "hardest" (score 10.0) and rates the real trap only
6.5. If we want a difficulty axis that predicts <i>failure</i>, it has to be built from failures, not from the clock.</p>
</div>

<h2>10 &middot; Itemized: every task against its phase-1 baseline</h2>
<div class="card">
<p style="margin-top:0">The granular view underneath every average above. One row per task, sorted by baseline duration.
The baseline is the <b>mean of the three phase-1 cold legs</b> for that task (the gray diamond in absolute mode, the
darker 0 line otherwise); each colored dot is one other leg on that same task. Toggle legs to keep it readable, and pick
one of three views: minutes vs baseline, <b>percent faster or slower than baseline</b>, or absolute minutes.</p>
<div class="ctl" id="it_mode"></div>
<div class="ctl" id="it_ctl"></div>
<div class="charttitle">Every task against its phase-1 baseline <span class='sub'>per leg, granular</span></div>
<div id="c_itemized"></div>
<p class="note">The <b>percent view is the higher-signal one</b>: it normalizes each gap by the task's own length, so a
minute saved counts for little on a long task and a lot on a short one. It exposes what the minute view flattens: the
fork legs are <i>relatively</i> catastrophic on short tasks (4A runs +556% on zilloft-10, +368% on dashdish-1), points
that ride off the right edge with their true value labeled, while on the long tasks that same fork looks mild. The
recipe and warm-up legs sit within a tight band around the baseline everywhere. Hover any mark for the exact minutes,
the percent, and the times-faster/slower factor. The dashed vertical line for each leg is its average across all twelve
tasks, with the value labeled underneath.</p>
</div>

<h2>11 &middot; Thematic patterns: how the knowledge is delivered</h2>
<div class="card">
<p style="margin-top:0">Set aside the phase numbers and group the arms by their <b>delivery mechanism</b> instead: where the
prior knowledge physically lives when the agent runs. Six themes fall out, and they behave as families.</p>
<div class="scroll"><table id="themetab"></table></div>
<p class="note" style="margin-top:12px">Three patterns unravel once you group this way. <b>One: context weight is the whole story
for time</b> (correlation between tokens-per-turn and time-vs-cold is <b>+0.91</b>; against seconds-per-turn, also <b>+0.91</b>).
The two disk-mount themes and the recipe theme keep tokens-per-turn near cold (~54&ndash;61k) and land near cold time;
the forked-session theme balloons to ~365k and pays <b>+27 minutes</b>. <b>Two: neither turns nor thinking is a lever.</b>
Turn count sits in a narrow band (25 to 40 across every theme) and correlates <b>0.00</b> with time; per-turn thinking is
flat too (~130 to 170 output tokens). The warm-up takes the <i>fewest</i> turns (25) and the disk mounts the most (37),
yet both land near cold, because what decides time is not how many turns or how hard each thinks, it is how much context
each turn drags. <b>Three: accuracy is theme-invariant, and cold is the outlier, not the ceiling.</b> Corrected against
ground truth, cold sits lowest at 8.0/12 and every other theme sits at 9.0&ndash;10.5, a tight band with no separation
between them; the delivery mechanism changes what the run costs, not what it can solve. (An earlier reading of this
chart had cold artificially tied for the top on the strength of two flaky judge verdicts, &sect;2; corrected, the honest
story is that <i>any</i> prior knowledge, regardless of delivery, edges out none at all, but recipe and warm-up do not
distinctly outperform the disk-mount or fork themes on accuracy the way they do on time.)</p>
<div class="charttitle">Where the time goes <span class='sub'>turns versus per-turn cost, by theme</span></div>
<div id="c_theme"></div>
<p class="note">Each dot is one arm placed by how it spends its time: turns (x) against real seconds per turn (y). Color is
the theme. The faint curves are lines of constant per-task time (turns times seconds-per-turn, labeled in per-task
minutes), with the cold baseline curve drawn heavier. The vertical axis is what decides the winner: the forks sit near
the top (every turn crushed by history) and are stranded on a high-time curve; the warm-up sits just above and to the
left of cold, fewer turns but each a touch heavier from its cached prefix, netting a hair below cold's curve; the disk
mounts drift right, more turns but light ones, landing right on cold. Nobody wins by taking the fewest or the cheapest
turns; the winner is whoever keeps per-turn context lowest. The channel you deliver through, disk or prompt or context,
decides the cost far more than the content you deliver.</p>
</div>

<h2>12 &middot; Per-arm &amp; per-task explorer</h2>
<p>Click any arm row for its 12-task breakdown; click a task for the cross-arm view.</p>
<div class="scroll"><table id="census"></table></div>

<h2>13 &middot; Methods &amp; integrity</h2>
<div class="card"><ul>
<li><strong>Pipeline.</strong> Fresh tab &rarr; clear &rarr; /config seed &rarr; clean /finish assert &rarr; detached
<span class="mono">claude -p</span> (sonnet, medium) &rarr; gate &rarr; byte-exact /finish + trajectory &rarr; close &rarr; REAL
evaluator (jmespath deterministic + sonnet-judged rubric). Forks add a workdir-snapshot restore + <span class="mono">--resume --fork-session</span>.</li>
<li><strong>Leakage discipline (phase 5).</strong> Recipes authored by an ISOLATED Fable-5 agent seeing only the
train-derived material; audited against test-set identifiers before use; never edited by the orchestrating session.</li>
<li><strong>Known grading noise + the dashdish-8 consistency decision.</strong> dashdish-8 is judge-nondeterministic:
5D's carousel answer, identical to what all 13 arms give, re-evaluated 3 pass / 2 fail over 5 runs. Because the rubric's
ground-truth answer is the collection rows (which no arm produced) and the judge verdict on the shared answer is a coin
flip, we mark dashdish-8 fail for all 13 arms for consistency (original judged verdicts preserved on disk under
evaluation_original_judge.json). zilloft-5/10 show the same judge sensitivity (mirage-aware phrasing passes, bare counts
fail). The &plusmn;2-3 task noise floor applies to every single-run arm.</li>
<li><strong>Metrics.</strong> tok/turn from per-rollout usage (cache reads + writes + fresh input). first-action =
median seconds to the first browser call. All per-task times are run-only, prep excluded. Full statistical treatment
(paired permutation, bootstrap CIs, win/loss) is in the archived deep-dive and main reports.</li>
<li><strong>Recipe prep attribution (caveat).</strong> All recipe variants were authored in ONE isolated Fable-5
session (~8.1 min compute; longer wall clock because it slept on a scheduled wakeup mid-run). The transcript splits into
a study/analysis phase (~4.9 min, reading BOTH sources and working out the app mechanics) and a writing phase (~3.2 min).
<b>Per-site (5A) and single (5B) recipes are shown with equal prep on purpose:</b> the dominant cost is the shared
cross-source analysis, which is incurred whether the output is two site recipes or one combined, so their totals are
legitimately near-identical (this is the answer to why they benchmarked the same). The writing phase did touch zilloft
more than dashdish and the combined least, but write-op count is a weak proxy for authoring effort, and the difference is
marginal, so we do not split the writing per variant. Upstream source-material steps (experiential runs, expert
recordings) are shown for full provenance but are a shared, reused cost, not re-incurred per arm. No rollouts were
re-run; only the prep accounting changed.</li>
<li><strong>Reproduce.</strong> <span class="mono">python3 analysis/harvest.py &amp;&amp; python3 analysis/build_capstone.py</span>.
Companion reports: <a href="benchmark_report.html">main (studies 1-3)</a> &middot;
<a href="benchmark_deep_dive.html">deep dive (fork forensics, difficulty)</a>.</li>
</ul></div>

<div id="detail"><span class="x" onclick="document.getElementById('detail').classList.remove('open')">&times;</span><div id="detailbody"></div></div>

<script>
const D = {json.dumps(D)};
const A = D.arms, ORDER = D.order, DIFF = D.diff;
const BY = {{}}; A.forEach(a=>BY[a.id]=a);
const S='http://www.w3.org/2000/svg';
function sv(w,h){{const s=document.createElementNS(S,'svg');s.setAttribute('viewBox',`0 0 ${{w}} ${{h}}`);s.setAttribute('width','100%');s.style.maxWidth=w+'px';return s}}
function E(n,at,tx){{const e=document.createElementNS(S,n);for(const k in at)e.setAttribute(k,at[k]);if(tx!=null)e.textContent=tx;return e}}
function tip(e,t){{e.appendChild(E('title',{{}},t));return e}}
const COLD=BY['exp1a-fixed-brave'];

function accChart(){{
  const w=1060,h=270,pl=40,pb=60,pt=20;const bw=Math.min(56,(w-pl-20)/A.length-8);
  const vmax=12;const Y=v=>h-pb-(h-pt-pb)*v/vmax;const s=sv(w,h);
  for(let g=0;g<=12;g+=3){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-10,y2:Y(g),stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},g))}}
  s.appendChild(E('line',{{x1:pl,y1:Y(COLD.passed),x2:w-10,y2:Y(COLD.passed),stroke:'#c9c7c1','stroke-dasharray':'6 4','stroke-width':1.5}}));
  s.appendChild(E('text',{{x:w-12,y:Y(COLD.passed)-4,'text-anchor':'end','font-size':10,fill:'#8a929c'}},`cold ${{COLD.passed}}/12`));
  A.forEach((a,i)=>{{const x=pl+14+i*(bw+8),y=Y(a.passed);
    s.appendChild(tip(E('rect',{{x,y,width:bw,height:Y(0)-y,rx:3,fill:a.color}}),`${{a.label}}: ${{a.passed}}/12`));
    s.appendChild(E('text',{{x:x+bw/2,y:y-4,'text-anchor':'middle','font-size':11,'font-weight':700,fill:a.color}},a.passed));
    s.appendChild(E('text',{{x:x+bw/2,y:h-pb+14,'text-anchor':'middle','font-size':9,fill:'#5b6571',transform:`rotate(35 ${{x+bw/2}} ${{h-pb+14}})`}},a.short));
  }});
  document.getElementById('c_acc').appendChild(s);
}}
function accGrid(){{
  let h='<div class="scroll"><table><thead><tr><th>task</th><th>diff</th>'+A.map(a=>`<th style="color:${{a.color}}" title="${{a.label}}">${{a.short}}</th>`).join('')+'</tr></thead><tbody>';
  ORDER.forEach(t=>{{h+=`<tr class="clickable" onclick="showTask('${{t}}')"><td class="mono">${{t}}</td><td>${{DIFF[t]}}</td>`+
    A.map(a=>{{const c=a.per_task.find(x=>x.t===t);
      const dot = c.passed ? (c.slow
        ? `<span style="color:#ca8a04" title="passed but slow for ${{a.short}} (${{c.min}}m)">●</span>`
        : `<span style="color:#0f8a5f" title="passed (${{c.min}}m)">●</span>`)
        : '<span class="badge b-fail">F</span>';
      return `<td style="text-align:center">${{dot}}</td>`}}).join('')+'</tr>';}});
  document.getElementById('c_accgrid').innerHTML=h+'</tbody></table></div>';
}}
const SM=D.step_meta;
function renderPerf(){{
  const showTask=document.getElementById('t_task').checked;
  const showPrep=document.getElementById('t_prep').checked;
  const layout=document.querySelector('input[name=lay]:checked').value;
  // legend (only the step types present, plus task)
  const usedSteps=[...new Set(A.flatMap(a=>a.prep_steps.map(s=>s.k)))];
  let leg='';
  if(showPrep) usedSteps.forEach(k=>{{leg+=`<span class="k"><span class="sw hatch" style="--c:${{SM[k].color}}"></span>${{SM[k].label}}</span>`}});
  if(showTask) leg+=`<span class="k"><span class="sw" style="background:#5b6571"></span>task time (SOLID, arm color)</span>`;
  document.getElementById('perf_legend').innerHTML=leg;
  // build per-arm segment lists (in draw order)
"""
