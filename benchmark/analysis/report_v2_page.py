# Page assembly for build_report_v2.py — pure refactor, behavior unchanged.

from report_v2_data import *
from report_v2_charts import *
from report_v2_page_a import *

PAGE_B = f"""<h2>8 &middot; Methods &amp; integrity</h2>
<div class="card"><ul>
<li><strong>Pipeline.</strong> Fresh tab &rarr; clear &rarr; /config seed &rarr; clean /finish assert &rarr; detached
<span class="mono">claude -p</span> (sonnet, medium) &rarr; gate &rarr; byte-exact /finish + trajectory capture &rarr; tab closed &rarr;
REAL evaluator (jmespath + sonnet-judged rubric). Fork rollouts additionally restore the study workdir snapshot at the
study's own absolute path and run <span class="mono">--resume &lt;sid&gt; --fork-session</span>.</li>
<li><strong>Small-n stance.</strong> 12 paired tasks per arm. Primary evidence: paired effect sizes with 10k-resample
bootstrap CIs, task-level win/loss records, full-pair slope charts, and replication across independent contrasts.
Exact sign-flip permutation and McNemar p-values are retained as footnotes (they agree with the CIs everywhere).</li>
<li><strong>Fork accounting.</strong> Forked transcripts embed the study prefix; all fork metrics are sliced from the
rollout's own run-start timestamp. num_turns is fork-local. Study prep: experiential 37.0 min (its six train segments);
expert 17 min operator demos + 27.1 min max-effort study (the one effort deviation, study only).</li>
<li><strong>Controls (2026-07-16).</strong> The June CinC baseline was re-run twice under suspicion of drift: an
identical control (11/12, 32.8 min; three judged flips vs the original, none reversed) and a setup-parity arm whose
header scripts the mandatory tab-bootstrap preamble (9/12 with two judge-phrasing fails, 24.5 min; whole-task dead heat
with OCIC, p=.44). Setup-prefix accounting: time to the first completed navigate, reported separately (CinC arms ~10s per
rollout; OCIC ~0 by construction). Focus-adjustment heuristic: browser calls &gt;1.5s replaced by that tool's clean median,
both systems; it shifts CinC by 0.66 min total and flags only find-search calls, ruling out background-tab throttling.
A persistent-tab parity design failed twice with "tab not in this session's group": official tab control is
session-scoped, so orchestrator-prepared tabs are impossible by design.</li>
<li><strong>Rate limits.</strong> One session-limit event during the expert fork's final rollout: two attempts
quarantined (never scored, evidence files kept), third attempt ran post-reset and is the scored one. One judge-side
throttle during the fork smoke, absorbed by a 15-min retry.</li>
<li><strong>External interruptions.</strong> Three background-chain kills during phase 4 (cause external to the runner);
recovery via completed-artifact skip logic, final leg run in a detached session. No scored rollout spans an interruption.</li>
<li><strong>Reproduce.</strong> <span class="mono">python3 analysis/harvest.py &amp;&amp; python3 analysis/stats.py &amp;&amp;
python3 analysis/build_report_v2.py</span> · archived editions: <a href="archive/benchmark_report_pre_fix.html">pre-fix</a> ·
<a href="archive/benchmark_report_postfix_v1.html">post-fix v1</a>.</li>
</ul></div>

<div id="detail"><span class="x" onclick="closeDetail()">&times;</span><div id="detailbody"></div></div>

<script>
const DATA = {json.dumps(DATA)};
const CELLS = {matrix_js_cells};
const fmt = (x, d=1) => x == null ? "·" : x.toFixed(d);

// ---- matrix ----
function renderMatrix() {{
  const m = document.getElementById("matrix");
  let h = '<div class="mhead"></div><div class="mhead">experiential (self)</div><div class="mhead">expert (operator)</div>';
  const names = {{raw: "raw mount", analysis: "analysis mount", fork: "forked session"}};
  for (const dlv of ["raw", "analysis", "fork"]) {{
    h += `<div class="mhead">${{names[dlv]}}</div>`;
    for (const fam of ["experiential", "expert"]) {{
      const a = CELLS[dlv][fam], s = DATA.arms[a];
      h += `<div class="mcell" onclick="showArm('${{a}}')" style="border-top:3px solid ${{s.color}}">
        <div class="big">${{s.passed}}/12</div>
        <div class="s">${{s.mean_task.toFixed(2)}} m/task · prep ${{s.prep.toFixed(0)}}m</div>
        <div class="s">${{s.label}}</div></div>`;
    }}
  }}
  m.innerHTML = h;
}}

// ---- toggles + task grid ----
let ON = new Set(DATA.defaultOn);
function renderToggles() {{
  const bar = document.getElementById("togglebar");
  bar.innerHTML = Object.keys(DATA.arms).map(a => {{
    const s = DATA.arms[a];
    return `<label class="tg"><input type="checkbox" ${{ON.has(a) ? "checked" : ""}} onchange="tgArm('${{a}}',this.checked)">
      <span class="sw" style="background:${{s.color}}"></span>${{s.short}}</label>`;
  }}).join("");
}}
function tgArm(a, on) {{ on ? ON.add(a) : ON.delete(a); renderGrid(); }}
function renderGrid() {{
  const arms = Object.keys(DATA.arms).filter(a => ON.has(a));
  let h = "<thead><tr><th>task</th><th>difficulty</th>" +
    arms.map(a => `<th style="color:${{DATA.arms[a].color}}">${{DATA.arms[a].short}}</th>`).join("") + "</tr></thead><tbody>";
  for (const t of DATA.order) {{
    const row = DATA.tasks[t];
    h += `<tr class="clickable" onclick="showTask('${{t}}')"><td class="mono">${{t}}</td><td>${{row.difficulty}}</td>`;
    for (const a of arms) {{
      const c = row.arms[a];
      h += `<td class="num" title="${{c.turns}} turns">${{c.passed ? "" : "<span class='badge b-fail'>F</span> "}}${{fmt(c.min)}}m</td>`;
    }}
    h += "</tr>";
  }}
  h += "</tbody>";
  document.getElementById("taskgrid").innerHTML = h;
}}

// ---- census (sortable) ----
let sortKey = "passed", sortDir = -1;
const CENSUS_COLS = [["label","arm",0],["passed","pass",1],["run_min","12-run min",1],["mean_task","m/task",1],
  ["turns","turns",1],["per_turn_s","per-turn s",1],["med_action_s","action s",1],["first_action_s","first-action s",1],
  ["ec","ec",1],["exp_reads","reads",1],["prep","prep m",1]];
function renderCensus() {{
  const arms = Object.values(DATA.arms).slice().sort((x,y) => {{
    const a = x[sortKey], b = y[sortKey];
    if (a == null) return 1; if (b == null) return -1;
    return (a < b ? -1 : a > b ? 1 : 0) * sortDir;
  }});
  let h = "<thead><tr>" + CENSUS_COLS.map(([k, lbl]) =>
    `<th class="sortable" onclick="sortBy('${{k}}')">${{lbl}}${{sortKey===k ? (sortDir<0?" ▾":" ▴") : ""}}</th>`).join("") + "</tr></thead><tbody>";
  for (const s of arms) {{
    h += `<tr><td><span class="sw" style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${{s.color}};margin-right:6px"></span>${{s.label}}</td>
      <td class="num">${{s.passed}}/12</td><td class="num">${{s.run_min.toFixed(1)}}</td><td class="num">${{s.mean_task.toFixed(2)}}</td>
      <td class="num">${{s.turns.toFixed(1)}}</td><td class="num">${{s.per_turn_s.toFixed(2)}}</td><td class="num">${{s.med_action_s.toFixed(3)}}</td>
      <td class="num">${{s.first_action_s==null?"·":s.first_action_s.toFixed(0)}}</td><td class="num">${{s.ec}}</td><td class="num">${{s.exp_reads}}</td><td class="num">${{s.prep.toFixed(0)}}</td></tr>`;
  }}
  document.getElementById("census").innerHTML = h + "</tbody>";
}}
function sortBy(k) {{ if (sortKey === k) sortDir *= -1; else {{ sortKey = k; sortDir = -1; }} renderCensus(); }}

// ---- detail panel ----
function openDetail(html) {{
  document.getElementById("detailbody").innerHTML = html;
  document.getElementById("detail").classList.add("open");
}}
function closeDetail() {{ document.getElementById("detail").classList.remove("open"); }}
function showTask(t) {{
  const row = DATA.tasks[t];
  let h = `<h3 style="margin:2px 0 2px">${{t}} <span class="note">(${{row.difficulty}})</span></h3>
    <p class="note" style="margin:2px 0 8px">${{row.goal}}</p><div class="scroll"><table><thead>
    <tr><th>arm</th><th>verdict</th><th>min</th><th>turns</th><th>ec</th><th>first-action</th><th>failing answer</th></tr></thead><tbody>`;
  for (const a of Object.keys(DATA.arms)) {{
    const c = row.arms[a], s = DATA.arms[a];
    h += `<tr><td>${{s.label}}</td><td>${{c.passed ? '<span class="badge b-pass">PASS</span>' : '<span class="badge b-fail">FAIL</span>'}}</td>
      <td class="num">${{fmt(c.min)}}</td><td class="num">${{c.turns}}</td><td class="num">${{c.ec}}</td>
      <td class="num">${{c.fa==null?"·":c.fa+"s"}}</td><td class="note">${{c.fail || ""}}</td></tr>`;
  }}
  openDetail(h + "</tbody></table></div>");
}}
function showArm(a) {{
  const s = DATA.arms[a];
  let h = `<h3 style="margin:2px 0 6px"><span class="sw" style="display:inline-block;width:11px;height:11px;background:${{s.color}};border-radius:3px;margin-right:7px"></span>${{s.label}}
    <span class="note">· ${{s.passed}}/12 · ${{s.run_min.toFixed(1)}} min total · prep ${{s.prep.toFixed(0)}} min</span></h3>
    <div class="scroll"><table><thead><tr><th>task</th><th>verdict</th><th>min</th><th>turns</th><th>failing answer</th></tr></thead><tbody>`;
  for (const t of DATA.order) {{
    const c = DATA.tasks[t].arms[a];
    h += `<tr class="clickable" onclick="showTask('${{t}}')"><td class="mono">${{t}}</td>
      <td>${{c.passed ? '<span class="badge b-pass">PASS</span>' : '<span class="badge b-fail">FAIL</span>'}}</td>
      <td class="num">${{fmt(c.min)}}</td><td class="num">${{c.turns}}</td><td class="note">${{c.fail || ""}}</td></tr>`;
  }}
  openDetail(h + "</tbody></table></div>");
}}

renderMatrix(); renderToggles(); renderGrid(); renderCensus();
</script>
</div></body></html>"""


page = PAGE_A + PAGE_B

out = os.path.join(BENCH, "benchmark_report.html")
open(out, "w").write(page)
print("wrote", out, f"({os.path.getsize(out)/1024:.0f} KB)")
