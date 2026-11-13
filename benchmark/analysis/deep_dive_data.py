# Split out of build_deep_dive.py — pure refactor, behavior unchanged.

import json, os, statistics, html as HH

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = json.load(open(os.path.join(BENCH, "analysis", "harvest.json")))
DEEP = json.load(open(os.path.join(BENCH, "analysis", "deep.json")))
DIFFDATA = json.load(open(os.path.join(BENCH, "analysis", "difficulty.json")))
CTX = json.load(open(os.path.join(BENCH, "analysis", "ctxcurve.json")))
FAILS = json.load(open(os.path.join(BENCH, "analysis", "fail_answers.json")))
ORDER = DEEP["order"]; CATS = DEEP["cats"]; GAPS = DEEP["gaps"]; USAGE = DEEP["usage"]

ARMS = {  # id: (label, short, color)
    "exp1a-fixed-brave":           ("Cold baseline (OCIC Brave)", "cold",     "#0d9488"),
    "exp1a-fixed-chrome":          ("Cold (OCIC Chrome)",         "cold-ch",  "#3b82f6"),
    "exp1b-cinc-rerun":            ("CinC control",               "cinc-ctl", "#b45309"),
    "exp1b-cinc-parity":           ("CinC parity",                "cinc-par", "#f59e0b"),
    "exp2a-fixed-brave":           ("Experiential raw mount",     "2A",       "#db2777"),
    "exp2b-fixed-brave":           ("Expert raw mount",           "2B",       "#10b981"),
    "exp3d-experiential-analysis": ("Experiential analysis",      "3D",       "#e360a3"),
    "exp3c-analysis":              ("Expert analysis",            "3C",       "#34d399"),
    "exp3b-brave":                 ("Expert analysis + code",     "3B",       "#7c3aed"),
    "exp4a-experiential-fork":     ("Experiential FORK",          "4A",       "#9d174d"),
    "exp4b-expert-fork":           ("Expert FORK",                "4B",       "#047857"),
}
DEFAULT_ON = ["exp1a-fixed-brave", "exp3c-analysis", "exp2b-fixed-brave",
              "exp4a-experiential-fork", "exp4b-expert-fork"]

def q(v, p):
    s = sorted(v); i = (len(s) - 1) * p
    lo = int(i); return s[lo] + (s[min(lo + 1, len(s) - 1)] - s[lo]) * (i - lo)

PAYLOAD = {"order": ORDER, "cats": CATS, "goals": DEEP["goals"],
           "difficulty": DEEP["difficulty"], "defaultOn": DEFAULT_ON, "arms": {}, "tasks": {}}
for a, (lbl, short, col) in ARMS.items():
    rows = H[a]
    allg = [g for t in ORDER for g in GAPS[a][t]["gaps"]]
    firsts = [GAPS[a][t]["first"] for t in ORDER if GAPS[a][t]["first"] is not None]
    u = USAGE.get(a)
    ktok = round((u["cr"] + u["cc"] + u["inp"]) / max(1, u["turns"]) / 1000) if u else None
    outk = round(u["out"] / 12 / 1000, 1) if u else None
    PAYLOAD["arms"][a] = dict(
        label=lbl, short=short, color=col,
        passed=sum(1 for r in rows.values() if r["passed"]),
        total_min=round(sum(r["run_s"] for r in rows.values()) / 60, 1),
        turns=sum(r["turns"] for r in rows.values()),
        gap_med=round(statistics.median(allg), 2), gap_p90=round(q(allg, .9), 2),
        gap_box=[round(min(allg), 2), round(q(allg, .25), 2), round(statistics.median(allg), 2),
                 round(q(allg, .75), 2), round(q(allg, .9), 2)],
        gap_outliers=[g for g in allg if g > q(allg, .75) + 1.5 * (q(allg, .75) - q(allg, .25))][:40],
        first_med=round(statistics.median(firsts), 1),
        ktok_turn=ktok, out_ktask=outk,
        run_by_task=[round(H[a][t]["run_min"], 2) for t in ORDER],
        pass_by_task=[bool(H[a][t]["passed"]) for t in ORDER],
        turns_by_task=[H[a][t]["turns"] for t in ORDER],
        gapmed_by_task=[round(statistics.median(GAPS[a][t]["gaps"]), 2) if GAPS[a][t]["gaps"] else None for t in ORDER],
        first_by_task=[GAPS[a][t]["first"] for t in ORDER],
        gap_series=[round(statistics.median([GAPS[a][t]["gaps"][i] for t in ORDER
                    if len(GAPS[a][t]["gaps"]) > i]), 2)
                    for i in range(0, 40)],
    )
for t in ORDER:
    PAYLOAD["tasks"][t] = {a: {"fail": FAILS.get(a, {}).get(t, "")} for a in ARMS}

# category aggregates
CATAGG = {}
for cname, tids in CATS.items():
    CATAGG[cname] = {}
    for a in ARMS:
        idx = [ORDER.index(t) for t in tids]
        r = PAYLOAD["arms"][a]
        CATAGG[cname][a] = dict(
            mean_min=round(statistics.mean([r["run_by_task"][i] for i in idx]), 2),
            passed=sum(1 for i in idx if r["pass_by_task"][i]), n=len(idx))
PAYLOAD["catagg"] = CATAGG
PAYLOAD["diff"] = DIFFDATA
PAYLOAD["ctx"] = CTX
# waterfall decomposition: deficit = per-turn tax + extra-work, vs cold
COLDA="exp1a-fixed-brave"
def _decomp(arm):
    tax=extra=0.0
    for t in ORDER:
        c,f=H[COLDA][t],H[arm][t]
        cp=c["run_s"]/max(1,c["turns"]); fp=f["run_s"]/max(1,f["turns"])
        tax+=f["turns"]*(fp-cp)/60.0
        extra+=(f["turns"]-c["turns"])*cp/60.0
    return dict(cold=round(sum(H[COLDA][t]["run_s"] for t in ORDER)/60,1),
                fork=round(sum(H[arm][t]["run_s"] for t in ORDER)/60,1),
                tax=round(tax,1), extra=round(extra,1))
PAYLOAD["waterfall"]={"exp4a-experiential-fork":_decomp("exp4a-experiential-fork"),
                      "exp4b-expert-fork":_decomp("exp4b-expert-fork")}

