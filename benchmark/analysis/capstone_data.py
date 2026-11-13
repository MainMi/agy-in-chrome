#!/usr/bin/env python3
"""benchmark_capstone.html: the full post-fix story, cold baselines through
phase 5. Per-arm descriptions, accuracy + performance comparisons, and
hypothesis-verdict graphics. Self-contained, interactive (vanilla JS SVG)."""
import json, os, statistics, html as HH

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(BENCH, "analysis", "capstone.json")))

# --- canonical arm renaming to the writeup's 6-phase scheme (1a-6b) ---
# Rename-only: upstream ids stay put. We relabel EVERY occurrence of an arm short
# across the whole data blob (dict keys, list elements, and any {"short": ...}
# field, at any depth) so nested structures like turns.scale.fits and *.tasks[].sv
# stay consistent with the charts. Recipe swap preserved: 5A (per-site) -> 5b,
# 5B (single) -> 5a.
RENAME = {"CinC": "1a", "OCIC-Ch": "1b", "OCIC-Br": "1c", "2A": "2a", "2B": "2b",
          "3D": "3a", "3C": "3b", "4A": "4a", "4B": "4b", "5B": "5a", "5A": "5b",
          "5C": "6a", "5D": "6b"}
NEWORDER = ["1a", "1b", "1c", "2a", "2b", "3a", "3b", "4a", "4b", "5a", "5b", "6a", "6b"]
_OLD = set(RENAME)  # domain and range are disjoint, so remap is idempotent-safe
# The scalar-space scatter read a stale theme palette; snap rankcompare to the
# canonical per-leg palette (keyed by OLD short, before the recursive rename).
_canon = D["dist_byleg"]["color"]
for _a in D["rankcompare"]["arms"]:
    _a["color"] = _canon.get(_a["short"], _a.get("color"))
def _remap(o):
    if isinstance(o, dict):
        return {RENAME.get(k, k): (RENAME[v] if k == "short" and v in _OLD else _remap(v))
                for k, v in o.items()}
    if isinstance(o, list):
        return [RENAME[x] if isinstance(x, str) and x in _OLD else _remap(x) for x in o]
    return o
D = _remap(D)
# display-order lists -> scheme order (left-to-right reads 1a..6b)
D["dist_byleg"]["order"] = NEWORDER[:]
_rank = {s: i for i, s in enumerate(NEWORDER)}
D["arms"].sort(key=lambda a: _rank.get(a["short"], 99))

ARMS = D["arms"]; ORDER = D["order"]; DIFF = D["diff"]
BY = {a["id"]: a for a in ARMS}
COLD = BY["exp1a-fixed-brave"]

# --- deterministic accuracy correction (see accuracy_regrade.py) ---
# capstone.json's accuracy came straight from REAL's llm_boolean judge, which
# disagreed with itself on identical answers (verified by reading every run's
# evaluation.json). Only 3 of 12 held-out tasks vary across arms at all; the
# other 9 pass/fail identically everywhere and dashdish-8 fails everywhere
# regardless of grading, so this only touches those 3 tasks' pass/fail + the
# rollups that are computed from them (per-arm .passed, dist_byleg.acc, the
# per-theme accuracy column).
_ACC = json.load(open(os.path.join(BENCH, "analysis", "accuracy_corrected.json")))
for _a in ARMS:
    _sh = _a["short"]
    _a["passed"] = _ACC["passed"][_sh]
    for _c in _a["per_task"]:
        if _c["t"] in _ACC["swing"]:
            _c["passed"] = _ACC["matrix"][_sh][_c["t"]]
            _c["fail"] = "" if _c["passed"] else _ACC["answer_text"][_c["t"]][_sh]
D["dist_byleg"]["acc"] = dict(_ACC["passed"])
for _t in D["themes"]:
    _members = [a for a in _t["arms"] if a in _ACC["passed"]]
    if _members:
        _t["acc"] = round(sum(_ACC["passed"][a] for a in _members) / len(_members), 1)

# within-arm "slow but passed": a passed task whose run time is an upper outlier
# RELATIVE TO THIS ARM's own task times. Robust modified z-score (MAD-based,
# handles the right-skew): flag if 0.6745*(t - median)/MAD > 1.5. This is per
# arm, not per task: it says "this task underperformed for THIS arm."
for _a in ARMS:
    _ts = [c["min"] for c in _a["per_task"] if c["passed"]]
    if len(_ts) >= 4:
        _med = statistics.median(_ts)
        _mad = statistics.median([abs(m - _med) for m in _ts]) or 0.01
        for c in _a["per_task"]:
            c["slow"] = bool(c["passed"] and 0.6745 * (c["min"] - _med) / _mad > 1.5)
    else:
        for c in _a["per_task"]:
            c["slow"] = False

PHASES = {
    "cold": ("Cold baselines", "No prior experience. What the agent does knowing only the task."),
    "p2":   ("Phase 2 · mounted raw", "Raw traces / recordings placed on disk at ./experience/."),
    "p3":   ("Phase 3 · mounted analysis", "Compressed per-site analysis docs on disk."),
    "p4":   ("Phase 4 · forked session", "A full study session checkpointed and forked into context."),
    "p5":   ("Phase 5 · recipe & atomic warm-up", "Leakage-free recipe in the prompt, and a single-task warm-up forked."),
}
PHASE_ORDER = ["cold", "p2", "p3", "p4", "p5"]

CSS = """
:root{--bg:#fbfbf9;--surface:#fff;--ink:#1b1f24;--muted:#5b6571;--dim:#8a929c;--line:#e7e6e1;--soft:#f3f2ee;--red:#c13a2e;--green:#0f8a5f;--amber:#b45309}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:40px 28px 120px}
h1{font-size:30px;line-height:1.14;letter-spacing:-.02em;margin:4px 0 8px}
h2{font-size:22px;margin:56px 0 8px;padding-bottom:8px;border-bottom:1px solid var(--line)}
h3{font-size:16.5px;margin:26px 0 6px}
p{margin:8px 0}
.eyebrow{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);font-weight:600}
.lede{font-size:17px;color:var(--muted)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:11px;padding:16px 18px;margin:14px 0}
.scroll{overflow-x:auto;padding-bottom:6px}
table{border-collapse:collapse;font-size:13px;width:100%}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);white-space:nowrap}
th.sortable{cursor:pointer}th.sortable:hover{color:var(--ink)}
td.num{font-variant-numeric:tabular-nums;text-align:right}
.mono{font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:13px 15px}
.kpi .n{font-size:22px;font-weight:700;letter-spacing:-.02em}
.kpi .l{font-size:11.5px;color:var(--muted);margin-top:3px}
.note{font-size:12.5px;color:var(--muted)}
.callout{background:var(--surface);border:1px solid var(--line);border-left:3px solid #2563eb;border-radius:8px;padding:12px 16px;margin:14px 0;font-size:13.5px}
.verdict{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.04em;padding:2px 9px;border-radius:12px;margin-right:8px}
.v-yes{background:#0f8a5f1a;color:var(--green)}.v-no{background:#c13a2e14;color:var(--red)}.v-part{background:#b453091a;color:var(--amber)}
.armrow{display:flex;gap:12px;align-items:flex-start;padding:9px 0;border-bottom:1px solid var(--line2,var(--soft))}
.sw{width:12px;height:12px;border-radius:3px;flex:0 0 12px;margin-top:5px}
.armrow .nm{font-weight:600;font-size:13.5px}
.armrow .meta{font-size:11.5px;color:var(--dim);font-family:"SF Mono",monospace}
.armrow .d{font-size:12.5px;color:var(--muted)}
.phasehdr{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);margin:16px 0 4px}
tr.clickable{cursor:pointer}tr.clickable:hover{background:var(--soft)}
.badge{display:inline-block;font-size:10px;font-weight:700;border-radius:4px;padding:1px 6px}
.b-pass{background:#0f8a5f14;color:var(--green)}.b-fail{background:#c13a2e14;color:var(--red)}
#detail{position:sticky;bottom:0;background:var(--surface);border:1px solid var(--line);border-radius:10px 10px 0 0;box-shadow:0 -4px 18px rgba(0,0,0,.07);padding:12px 18px;display:none;max-height:46vh;overflow:auto}
#detail.open{display:block}#detail .x{float:right;cursor:pointer;color:var(--dim);font-size:18px}
.ctl{display:flex;flex-wrap:wrap;align-items:center;gap:16px;margin:2px 0 12px;font-size:13px}
.ctl label{display:inline-flex;align-items:center;gap:6px;cursor:pointer;user-select:none}
.ctl .sep{width:1px;height:16px;background:var(--line)}
.plegend{display:flex;flex-wrap:wrap;gap:12px;margin:8px 0 2px;font-size:11.5px;color:var(--muted)}
.plegend .k{display:inline-flex;align-items:center;gap:6px}
.plegend .sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.plegend .sw.hatch{background:repeating-linear-gradient(45deg,#fbfbf9 0 2px,var(--c) 2px 4.2px);border:1px solid var(--line)}
svg text{font-family:inherit}
.sidebar{position:fixed;left:0;top:0;bottom:0;width:212px;overflow-y:auto;background:var(--surface);border-right:1px solid var(--line);padding:14px 12px 40px;z-index:60;font-size:12px;transition:transform .2s}
.sidebar .brand{font-weight:700;font-size:12.5px;letter-spacing:-.01em;color:var(--ink)}
.sidebar .brandsub{font-size:10px;color:var(--dim);margin-bottom:6px}
.sidebar h4{font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--dim);margin:15px 0 5px;font-weight:700}
.sidebar a.navlink{display:block;color:var(--muted);text-decoration:none;padding:2px 5px;border-radius:4px;line-height:1.3}
.sidebar a.navlink:hover{background:var(--soft);color:var(--ink)}
.sidebar a.navlink .n{color:var(--dim);font-family:"SF Mono",monospace;font-size:10px;margin-right:5px}
.legrow{display:flex;align-items:baseline;gap:6px;padding:2px 5px;font-size:11px;color:var(--muted);line-height:1.3}
.legrow .sw{width:11px;height:11px;border-radius:3px;flex:0 0 11px;position:relative;top:1px}
.legrow b{color:var(--ink);font-family:"SF Mono",monospace;font-size:10px;flex:0 0 46px}
body{padding-left:234px;transition:padding-left .2s}
.navtoggle{position:fixed;top:10px;left:220px;z-index:70;background:var(--surface);border:1px solid var(--line);border-radius:6px;width:26px;height:26px;line-height:23px;text-align:center;cursor:pointer;font-size:13px;color:var(--muted);transition:left .2s;user-select:none}
body.navhidden .sidebar{transform:translateX(-100%)}
body.navhidden{padding-left:0}
body.navhidden .navtoggle{left:8px}
.charttitle{font-size:13.5px;font-weight:700;color:var(--ink);letter-spacing:-.01em;margin:14px 0 2px}
.charttitle .sub{font-weight:400;color:var(--dim);font-size:11.5px;letter-spacing:0}
"""

def arm_registry_html():
    out = []
    for ph in PHASE_ORDER:
        title, sub = PHASES[ph]
        out.append(f'<div class="phasehdr">{HH.escape(title)} &middot; <span style="text-transform:none;font-weight:400;letter-spacing:0">{HH.escape(sub)}</span></div>')
        for a in [x for x in ARMS if x["phase"] == ph]:
            prep = f"{a['prep_full']:.0f}m prep" if a.get('prep_full') else "0 prep"
            out.append(
                f'<div class="armrow"><span class="sw" style="background:{a["color"]}"></span>'
                f'<div><div class="nm">{HH.escape(a["label"])} '
                f'<span class="meta">&middot; {a["passed"]}/12 &middot; {a["total"]:.1f}m &middot; {prep} &middot; {a["ktok"]:.0f}k tok/turn</span></div>'
                f'<div class="d">{HH.escape(a["desc"])}</div></div></div>')
    return "".join(out)

# ---- headline KPIs ----
best_time = min(ARMS, key=lambda a: a["total"])
kpis = f"""<div class="kpis">
<div class="kpi"><div class="n">13 arms &middot; 60 tasks-eq</div><div class="l">post-fix configurations over the same 12 held-out tasks</div></div>
<div class="kpi"><div class="n">8/12 &middot; 23.4m</div><div class="l">the cold OCIC baseline every method has to beat</div></div>
<div class="kpi"><div class="n">5D &middot; 20.9m</div><div class="l">only arm faster than cold (warm-up + recipe), on the hard tasks</div></div>
<div class="kpi"><div class="n">8 to 11 of 12</div><div class="l">accuracy is narrow but not flat; 7 of 39 borderline grader verdicts were overturned against ground truth (&sect;2)</div></div>
<div class="kpi"><div class="n">480k &rarr; 92k</div><div class="l">shrinking the fork's context (P4&rarr;P5) flipped it from worst to a tie</div></div>
</div>"""
