# Split out of build_report_v2.py — pure refactor, behavior unchanged.

import json, os, random, statistics, html as H

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARV = json.load(open(os.path.join(BENCH, "analysis", "harvest.json")))
STATS = json.load(open(os.path.join(BENCH, "analysis", "stats.json")))
FAILS = json.load(open(os.path.join(BENCH, "analysis", "fail_answers.json")))
FOCUS = json.load(open(os.path.join(BENCH, "analysis", "focus_adjusted.json")))
MAN = json.load(open(os.path.join(BENCH, "tasks_manifest.json")))
ORDER = MAN["test_order"]; TASKS = MAN["tasks"]

# ---- arm registry ------------------------------------------------------------
# (label, short, color, family, delivery, prep_min)
ARMS = {
    "exp1a-fixed-brave":           ("Cold · Brave",             "cold",     "#0d9488", "cold",         "none",     0.0),
    "exp1a-fixed-chrome":          ("Cold · Chrome",            "cold-ch",  "#3b82f6", "cold",         "none",     0.0),
    "exp1b-cinc-cold":             ("CinC original (June)",     "cinc-old", "#d97706", "cold",         "none",     0.0),
    "exp1b-cinc-rerun":            ("CinC control (Jul 16)",    "cinc-ctl", "#b45309", "cold",         "none",     0.0),
    "exp1b-cinc-parity":           ("CinC parity (scripted)",   "cinc-par", "#f59e0b", "cold",         "none",     0.0),
    "exp2a-fixed-brave":           ("Experiential raw mount",   "2A",       "#db2777", "experiential", "raw",      26.1),
    "exp2b-fixed-brave":           ("Expert raw mount",         "2B",       "#10b981", "expert",       "raw",      17.0),
    "exp3d-experiential-analysis": ("Experiential analysis",    "3D",       "#db2777", "experiential", "analysis", 32.6),
    "exp3c-analysis":              ("Expert analysis",          "3C",       "#10b981", "expert",       "analysis", 20.5),
    "exp3b-brave":                 ("Expert analysis + code",   "3B",       "#7c3aed", "expert",       "analysis", 20.5),
    "exp4a-experiential-fork":     ("Experiential fork",        "4A",       "#9d174d", "experiential", "fork",     37.0),
    "exp4b-expert-fork":           ("Expert fork",              "4B",       "#047857", "expert",       "fork",     44.1),
}
DEFAULT_ON = ["exp1a-fixed-brave", "exp1b-cinc-rerun", "exp1b-cinc-parity",
              "exp3c-analysis", "exp4b-expert-fork"]

def arm_summary(a):
    rows = HARV[a]
    run = sum(r["run_s"] for r in rows.values()) / 60.0
    passed = sum(1 for r in rows.values() if r["passed"])
    turns = statistics.mean(r["turns"] for r in rows.values())
    per_turn = sum(r["run_s"] for r in rows.values()) / max(1, sum(r["turns"] for r in rows.values()))
    act = statistics.mean(r["median_action_s"] for r in rows.values() if r.get("median_action_s"))
    ec = sum(r.get("execute_code", r.get("execute_code_traj", 0)) for r in rows.values())
    fa = [r.get("first_action_s") for r in rows.values() if r.get("first_action_s") is not None]
    er = sum(r.get("experience_reads", 0) for r in rows.values())
    lbl, short, col, fam, dlv, prep = ARMS[a]
    return dict(arm=a, label=lbl, short=short, color=col, family=fam, delivery=dlv,
                prep=prep, passed=passed, run_min=round(run, 1),
                mean_task=round(run / 12, 2), turns=round(turns, 1),
                per_turn_s=round(per_turn, 2), med_action_s=round(act, 3),
                ec=ec, first_action_s=round(statistics.median(fa), 1) if fa else None,
                exp_reads=er)

SUM = {a: arm_summary(a) for a in ARMS}

# ---- paired evidence: effect size + bootstrap CI + win/loss ------------------
random.seed(1789)
def paired_evidence(a, b, metric="run_s", scale=1/60.0):
    diffs = [(HARV[a][t][metric] - HARV[b][t][metric]) * scale for t in ORDER]
    mean = statistics.mean(diffs)
    bs = []
    for _ in range(10000):
        s = [random.choice(diffs) for _ in diffs]
        bs.append(statistics.mean(s))
    bs.sort()
    lo, hi = bs[249], bs[9749]
    wins = sum(1 for d in diffs if d < -1e-9)   # a faster
    loss = sum(1 for d in diffs if d > 1e-9)
    ties = len(diffs) - wins - loss
    return dict(mean=round(mean, 2), lo=round(lo, 2), hi=round(hi, 2),
                wl=f"{wins}-{loss}" + (f"-{ties}" if ties else ""),
                diffs=[round(d, 2) for d in diffs])

def stat_p(frag):
    for t in STATS:
        if frag in t["time"]["comparison"]:
            return t["time"]["all"]["p_perm"], t["accuracy"] if "accuracy" in t["time"] else t["time"]["accuracy"]
    return None, None

COMPARISONS = [  # (id, label, a, b, study)
    ("s1chrome", "OCIC fixed Chrome vs CinC original (same browser)", "exp1a-fixed-chrome", "exp1b-cinc-cold", "S1"),
    ("s1brave",  "OCIC fixed Brave vs CinC original", "exp1a-fixed-brave",  "exp1b-cinc-cold", "S1"),
    ("s1control", "OCIC fixed vs CinC CONTROL (fresh rerun)", "exp1a-fixed-brave", "exp1b-cinc-rerun", "S1"),
    ("s1parity",  "OCIC fixed vs CinC PARITY (scripted preamble)", "exp1a-fixed-brave", "exp1b-cinc-parity", "S1"),
    ("s1pc",      "CinC parity vs CinC control", "exp1b-cinc-parity", "exp1b-cinc-rerun", "S1"),
    ("s2_2a", "Experiential raw vs cold",  "exp2a-fixed-brave", "exp1a-fixed-brave", "S2"),
    ("s2_2b", "Expert raw vs cold",        "exp2b-fixed-brave", "exp1a-fixed-brave", "S2"),
    ("s2_3d", "Experiential analysis vs cold", "exp3d-experiential-analysis", "exp1a-fixed-brave", "S2"),
    ("s2_3c", "Expert analysis vs cold",   "exp3c-analysis", "exp1a-fixed-brave", "S2"),
    ("s3_4a", "Experiential fork vs cold", "exp4a-experiential-fork", "exp1a-fixed-brave", "S3"),
    ("s3_4b", "Expert fork vs cold",       "exp4b-expert-fork", "exp1a-fixed-brave", "S3"),
    ("s3_4b3c", "Expert fork vs expert analysis", "exp4b-expert-fork", "exp3c-analysis", "S3"),
    ("s3_4b2b", "Expert fork vs expert raw", "exp4b-expert-fork", "exp2b-fixed-brave", "S3"),
    ("s3_4a3d", "Exp. fork vs exp. analysis", "exp4a-experiential-fork", "exp3d-experiential-analysis", "S3"),
    ("s3_4a2a", "Exp. fork vs exp. raw", "exp4a-experiential-fork", "exp2a-fixed-brave", "S3"),
    ("s3_4b4a", "Expert fork vs experiential fork", "exp4b-expert-fork", "exp4a-experiential-fork", "S3"),
]
EV = {}
for cid, lbl, a, b, study in COMPARISONS:
    e = paired_evidence(a, b)
    e_turns = paired_evidence(a, b, metric="turns", scale=1.0)
    p, acc = stat_p(SUM[a]["label"].split(" ·")[0][:10]) if False else (None, None)
    EV[cid] = dict(label=lbl, a=a, b=b, study=study, time=e, turns=e_turns,
                   pass_a=SUM[a]["passed"], pass_b=SUM[b]["passed"])
# attach exact p from stats.json by matching arm ids
for t in STATS:
    ta, tb = t["time"]["a"], t["time"]["b"]
    for cid, e in EV.items():
        if e["a"] == ta and e["b"] == tb:
            e["p_time"] = t["time"]["all"]["p_perm"]
            e["p_acc"] = t["time"]["accuracy"]["p_mcnemar"]

# ---- per-task payload for interactivity --------------------------------------
TASK_PAYLOAD = {}
for t in ORDER:
    row = {"goal": TASKS[t]["goal"], "difficulty": TASKS[t]["difficulty"], "arms": {}}
    for a in ARMS:
        r = HARV[a][t]
        row["arms"][a] = {
            "passed": r["passed"], "min": round(r["run_min"], 2), "turns": r["turns"],
            "ec": r.get("execute_code", r.get("execute_code_traj", 0)),
            "fa": r.get("first_action_s"),
            "fail": FAILS.get(a, {}).get(t, "") if not r["passed"] else "",
        }
    TASK_PAYLOAD[t] = row

DATA = {
    "order": ORDER, "arms": {a: SUM[a] for a in ARMS}, "defaultOn": DEFAULT_ON,
    "tasks": TASK_PAYLOAD, "ev": EV,
}


CSS = """
:root{--bg:#fbfbf9;--surface:#fff;--ink:#1b1f24;--muted:#5b6571;--dim:#8a929c;--line:#e7e6e1;--soft:#f3f2ee;--red:#c13a2e;--green:#0f8a5f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:40px 28px 110px}
h1{font-size:29px;line-height:1.16;letter-spacing:-.02em;margin:4px 0 8px}
h2{font-size:21px;letter-spacing:-.01em;margin:54px 0 6px;padding-bottom:7px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:26px 0 6px}
p{margin:8px 0}
.eyebrow{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);font-weight:600}
.lede{font-size:16.5px;color:var(--muted)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}
.scroll{overflow-x:auto;padding-bottom:6px}
table{border-collapse:collapse;font-size:13px;width:100%}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);white-space:nowrap}
th.sortable{cursor:pointer}th.sortable:hover{color:var(--ink)}
td.num{font-variant-numeric:tabular-nums;text-align:right}
.mono{font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .n{font-size:22px;font-weight:700;letter-spacing:-.02em}
.kpi .l{font-size:11.5px;color:var(--muted)}
.note{font-size:12.5px;color:var(--muted)}
ul{margin:8px 0;padding-left:20px}li{margin:4px 0}
.callout{background:var(--surface);border:1px solid var(--line);border-left:3px solid #3b82f6;border-radius:8px;padding:12px 16px;margin:14px 0;font-size:13.5px}
.verdict{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.04em;padding:2px 9px;border-radius:12px;margin-right:8px}
.v-conf{background:#0f8a5f1a;color:var(--green)}.v-deb{background:#c13a2e14;color:var(--red)}.v-part{background:#d977061a;color:#9a5a06}
.togglebar{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.tg{display:inline-flex;align-items:center;gap:6px;font-size:12px;border:1px solid var(--line);border-radius:14px;padding:3px 10px;cursor:pointer;user-select:none;background:var(--surface)}
.tg input{margin:0}
.tg .sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.matrix{display:grid;grid-template-columns:130px 1fr 1fr;gap:8px;margin:12px 0}
.mcell{border:1px solid var(--line);border-radius:9px;padding:10px 12px;background:var(--surface);cursor:pointer}
.mcell:hover{border-color:var(--dim)}
.mcell .big{font-size:19px;font-weight:700}
.mcell .s{font-size:11px;color:var(--muted)}
.mhead{align-self:center;font-size:12px;color:var(--muted);font-weight:600}
#detail{position:sticky;bottom:0;background:var(--surface);border:1px solid var(--line);border-radius:10px 10px 0 0;box-shadow:0 -4px 18px rgba(0,0,0,.06);padding:12px 18px;display:none;max-height:44vh;overflow:auto}
#detail.open{display:block}
#detail .x{float:right;cursor:pointer;color:var(--dim);font-size:18px;line-height:1}
.badge{display:inline-block;font-size:10px;font-weight:700;border-radius:4px;padding:1px 6px}
.b-pass{background:#0f8a5f14;color:var(--green)}.b-fail{background:#c13a2e14;color:var(--red)}
.evrow td{font-size:12.5px}
.ci{color:var(--muted);font-size:11.5px}
tr.clickable{cursor:pointer}tr.clickable:hover{background:var(--soft)}
"""

# ---- static SVG helpers (python-rendered) ------------------------------------
