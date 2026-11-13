# Data loading + arm stats for build_report.py — split out as a pure
# refactor; behavior unchanged.

import json, os, re, statistics, html as htmlmod

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = json.load(open(os.path.join(BENCH, "analysis", "harvest.json")))
S = json.load(open(os.path.join(BENCH, "analysis", "stats.json")))
AM = json.load(open(os.path.join(BENCH, "analysis", "amortization.json")))
ORDER = json.load(open(os.path.join(BENCH, "tasks_manifest.json")))["test_order"]
OLD = open(os.path.join(BENCH, "archive", "benchmark_report_pre_fix.html")).read()

# ---- palette (validated: dataviz six checks, light surface #fbfbf9) ---------
ARM_META = {  # label, color, prep_min (source-material + analysis authoring)
    "exp1a-fixed-chrome":          ("1A-fixed · Chrome, cold",        "#3b82f6", 0.0),
    "exp1a-fixed-brave":           ("1A-fixed · Brave, cold",         "#0d9488", 0.0),
    "exp1b-cinc-cold":             ("1B · official CinC, cold",       "#d97706", 0.0),
    "exp2a-fixed-brave":           ("2A-fixed · experiential raw",    "#db2777", 26.1),
    "exp2b-fixed-brave":           ("2B-fixed · expert raw",          "#10b981", 17.0),
    "exp3b-brave":                 ("3B · expert analysis + code",    "#7c3aed", 20.5),
    "exp3c-analysis":              ("3C · expert analysis, silent",   "#10b981", 20.5),
    "exp3d-experiential-analysis": ("3D · experiential analysis",     "#db2777", 32.6),
}
# raw-trace arms share their source's hue (emerald = expert, pink = experiential)
# and are drawn hollow/dashed; compressed-analysis arms are solid.
RAW_ARMS = {"exp2a-fixed-brave", "exp2b-fixed-brave"}
# only fully-run arms enter the report (2B-fixed may still be mid-flight)
ARM_META = {a: v for a, v in ARM_META.items() if len(H.get(a, {})) == 12}
PREFIX_ARMS = ["exp1a-ocic-cold", "exp1a-chrome", "exp2a-experiential",
               "exp2b-expert", "exp3a-code", "exp3b-code-analysis"]
PREFIX_LABEL = {
    "exp1a-ocic-cold": "1A · OCIC Brave, cold", "exp1a-chrome": "1A · OCIC Chrome, cold",
    "exp2a-experiential": "2A · raw self traces", "exp2b-expert": "2B · raw expert recordings",
    "exp3a-code": "3A · expert raw + code", "exp3b-code-analysis": "3B · expert analysis + code",
}
PREFIX_PREP = {"exp2a-experiential": 26.1, "exp2b-expert": 17.0, "exp3a-code": 17.0,
               "exp3b-code-analysis": 20.5, "exp1a-ocic-cold": 0.0, "exp1a-chrome": 0.0}

def esc(s): return htmlmod.escape(str(s))

def arm_stats(a):
    rows = H[a]
    n = len(rows); p = sum(1 for r in rows.values() if r["passed"])
    run = sum(r["run_s"] for r in rows.values()) / 60.0
    med_act = statistics.mean([r["median_action_s"] for r in rows.values() if r.get("median_action_s")])
    tot_act = statistics.mean([r.get("total_action_s", 0) for r in rows.values()])
    turns = statistics.mean([r["turns"] for r in rows.values()])
    repl = sum(r.get("replays", 0) for r in rows.values())
    ec = sum(r.get("execute_code", r.get("execute_code_traj", 0)) for r in rows.values())
    return dict(n=n, passed=p, run_min=run, med_act=med_act, tot_act=tot_act,
                turns=turns, replays=repl, ec=ec)

A = {a: arm_stats(a) for a in list(ARM_META) + PREFIX_ARMS}

def get_test(frag):
    for t in S:
        if frag in t["time"]["comparison"]: return t
    raise KeyError(frag)

T_CHROME = get_test("fixed (Chrome) vs CinC")
T_BRAVE = get_test("fixed (Brave) vs CinC")
T_3C = get_test("expert-analysis (3c) vs cold baseline")
T_3D = get_test("experiential-analysis (3d) vs cold baseline")
T_3C3D = get_test("(3c) vs experiential-analysis (3d)")

def fmt_p(p): return ("%.4f" % p).rstrip("0").rstrip(".") if p >= 0.001 else "%.4f" % p

# ---- svg helpers -------------------------------------------------------------
