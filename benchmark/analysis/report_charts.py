# Chart builders for build_report.py — split out as a pure refactor;
# behavior unchanged.

from report_data import *

def svg_open(w, h): return f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" font-family="inherit" role="img">'

def paired_dot_chart():
    """Chart A: per-task median action round-trip, OCIC-fixed-chrome vs CinC (same browser)."""
    w, hrow, pad_l, pad_t = 660, 21, 128, 30
    hgt = pad_t + hrow * 12 + 34
    xmax = 0.42
    def X(v): return pad_l + (w - pad_l - 18) * min(v, xmax) / xmax
    out = [svg_open(w, hgt)]
    for gx in (0.1, 0.2, 0.3, 0.4):
        out.append(f'<line x1="{X(gx):.0f}" y1="{pad_t-8}" x2="{X(gx):.0f}" y2="{hgt-30}" stroke="#e7e6e1"/>'
                   f'<text x="{X(gx):.0f}" y="{hgt-16}" text-anchor="middle" font-size="10" fill="#8a929c">{gx}s</text>')
    for i, t in enumerate(ORDER):
        y = pad_t + i * hrow + 10
        a = H["exp1a-fixed-chrome"][t]["median_action_s"]; b = H["exp1b-cinc-cold"][t]["median_action_s"]
        out.append(f'<text x="{pad_l-10}" y="{y+4}" text-anchor="end" font-size="11" fill="#5b6571">{t}</text>')
        out.append(f'<line x1="{X(a):.1f}" y1="{y}" x2="{X(b):.1f}" y2="{y}" stroke="#e7e6e1" stroke-width="2"/>')
        out.append(f'<circle cx="{X(b):.1f}" cy="{y}" r="4.5" fill="#d97706"><title>{t} · CinC {b:.2f}s</title></circle>')
        out.append(f'<circle cx="{X(a):.1f}" cy="{y}" r="4.5" fill="#3b82f6"><title>{t} · OCIC-fixed {a:.2f}s</title></circle>')
    y0 = pad_t - 14
    out.append(f'<circle cx="{pad_l+6}" cy="{y0}" r="4.5" fill="#3b82f6"/><text x="{pad_l+15}" y="{y0+4}" font-size="11" fill="#5b6571">OCIC fixed (Chrome)</text>')
    out.append(f'<circle cx="{pad_l+166}" cy="{y0}" r="4.5" fill="#d97706"/><text x="{pad_l+175}" y="{y0+4}" font-size="11" fill="#5b6571">official CinC (Chrome)</text>')
    out.append("</svg>")
    return "".join(out)

def totals_chart():
    """Chart B (preserved): total time, preparation stacked onto runs."""
    arms = list(ARM_META)
    w, hrow, pad_l, pad_t = 660, 34, 208, 14
    hgt = pad_t + hrow * len(arms) + 36
    xmax = 76.0
    def X(v): return pad_l + (w - pad_l - 88) * min(v, xmax) / xmax
    out = [svg_open(w, hgt)]
    for gx in (15, 30, 45, 60, 75):
        out.append(f'<line x1="{X(gx):.0f}" y1="{pad_t-4}" x2="{X(gx):.0f}" y2="{hgt-30}" stroke="#e7e6e1"/>'
                   f'<text x="{X(gx):.0f}" y="{hgt-16}" text-anchor="middle" font-size="10" fill="#8a929c">{gx}m</text>')
    for i, a in enumerate(arms):
        lbl, col, prep = ARM_META[a]; st = A[a]
        y = pad_t + i * hrow + 4; bh = 17
        out.append(f'<text x="{pad_l-10}" y="{y+13}" text-anchor="end" font-size="11.5" fill="#1b1f24">{esc(lbl)}</text>')
        x = pad_l
        if prep > 0:
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{X(prep)-pad_l:.1f}" height="{bh}" rx="3" fill="#8a929c" opacity="0.45"><title>{esc(lbl)} · preparation {prep:.1f}m</title></rect>')
            x = X(prep) + 2
        rw = X(prep + st["run_min"]) - x
        style = (f'fill="#fbfbf9" stroke="{col}" stroke-width="2"' if a in RAW_ARMS
                 else f'fill="{col}"')
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(rw,2):.1f}" height="{bh}" rx="3" {style}><title>{esc(lbl)} · 12 runs {st["run_min"]:.1f}m</title></rect>')
        tot = prep + st["run_min"]
        out.append(f'<text x="{X(tot)+6:.1f}" y="{y+13}" font-size="11" fill="#5b6571" font-variant-numeric="tabular-nums">{tot:.0f}m · {st["passed"]}/12</text>')
    out.append(f'<rect x="{pad_l}" y="{hgt-12}" width="11" height="11" rx="2" fill="#8a929c" opacity="0.45"/>'
               f'<text x="{pad_l+16}" y="{hgt-3}" font-size="10.5" fill="#5b6571">one-time preparation (recording / generation + analysis authoring)</text>')
    out.append("</svg>")
    return "".join(out)

def amortization_chart():
    """Chart C (preserved): cumulative time vs number of tasks, prep offsets included."""
    arms = list(ARM_META)
    w, hgt, pad_l, pad_t, pad_b, pad_r = 660, 330, 52, 16, 30, 118
    ymax = 75.0
    def X(i): return pad_l + (w - pad_l - pad_r) * i / 12.0
    def Y(v): return hgt - pad_b - (hgt - pad_t - pad_b) * min(v, ymax) / ymax
    out = [svg_open(w, hgt)]
    for gy in (0, 25, 50, 75):
        out.append(f'<line x1="{pad_l}" y1="{Y(gy):.0f}" x2="{w-pad_r}" y2="{Y(gy):.0f}" stroke="#e7e6e1"/>'
                   f'<text x="{pad_l-6}" y="{Y(gy)+4:.0f}" text-anchor="end" font-size="10" fill="#8a929c">{gy}m</text>')
    for i in range(0, 13, 2):
        out.append(f'<text x="{X(i):.0f}" y="{hgt-12}" text-anchor="middle" font-size="10" fill="#8a929c">{i}</text>')
    out.append(f'<text x="{(pad_l+w-pad_r)/2:.0f}" y="{hgt-1}" text-anchor="middle" font-size="10.5" fill="#5b6571">tasks completed (test-split order)</text>')
    lab_ys = []
    for a in arms:
        lbl, col, prep = ARM_META[a]
        cum = 0.0; series = []
        for t in ORDER:
            cum += H[a][t]["run_min"]; series.append(cum)
        pts = [(0, prep)] + [(i + 1, prep + c) for i, c in enumerate(series)]
        d = " ".join(f"{X(x):.1f},{Y(v):.1f}" for x, v in pts)
        dash = ' stroke-dasharray="6 4"' if a in RAW_ARMS else ""
        out.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="2"{dash}><title>{esc(lbl)}</title></polyline>')
        if prep > 0:
            out.append(f'<circle cx="{X(0):.1f}" cy="{Y(prep):.1f}" r="3.5" fill="#fbfbf9" stroke="{col}" stroke-width="2"><title>{esc(lbl)} · prep {prep:.1f}m</title></circle>')
        ex, ey = X(12), Y(pts[-1][1])
        while any(abs(ey - o) < 12 for o in lab_ys): ey -= 12
        lab_ys.append(ey)
        out.append(f'<circle cx="{X(12):.1f}" cy="{Y(pts[-1][1]):.1f}" r="3.5" fill="{col}"/>')
        SHORT = {"exp1a-fixed-chrome": "1A-fx Chrome", "exp1a-fixed-brave": "1A-fx Brave",
                 "exp1b-cinc-cold": "1B CinC", "exp2a-fixed-brave": "2A-fx raw",
                 "exp2b-fixed-brave": "2B-fx raw", "exp3b-brave": "3B",
                 "exp3c-analysis": "3C", "exp3d-experiential-analysis": "3D"}
        short = SHORT.get(a, lbl.split("\u00b7")[0].strip())
        out.append(f'<text x="{ex+7:.1f}" y="{ey+4:.1f}" font-size="10.5" fill="{col}">{esc(short)} {pts[-1][1]:.0f}m</text>')
    out.append("</svg>")
    return "".join(out)

def bridge_chart():
    """Chart D: the fix absorbed the pre-training effect (accuracy + pace panels)."""
    groups = [
        ("cold", "pre-fix", "exp1a-ocic-cold"), ("expert raw", "pre-fix", "exp2b-expert"),
        ("cold", "post-fix", "exp1a-fixed-brave"), ("expert analysis", "post-fix", "exp3c-analysis"),
        ("experiential analysis", "post-fix", "exp3d-experiential-analysis"),
    ]
    w, hgt = 660, 278
    out = [svg_open(w, hgt)]
    def panel(x0, title, val, vmax, fmt):
        pw = 292; bw = 40; gap = 16
        out.append(f'<text x="{x0}" y="18" font-size="12" font-weight="600" fill="#1b1f24">{title}</text>')
        base_y = 218
        for i, (lbl, era, arm) in enumerate(groups):
            v = val(arm); bh = (base_y - 40) * v / vmax
            x = x0 + i * (bw + gap)
            col = ARM_META.get(arm, (None, None))[1] or {"exp1a-ocic-cold": "#9fb2c8", "exp2b-expert": "#c7b3ee"}[arm]
            op = "0.55" if era == "pre-fix" else "1"
            out.append(f'<rect x="{x}" y="{base_y-bh:.1f}" width="{bw}" height="{bh:.1f}" rx="4" fill="{col}" opacity="{op}"><title>{esc(lbl)} ({era}): {fmt(v)}</title></rect>')
            out.append(f'<text x="{x+bw/2:.0f}" y="{base_y-bh-6:.0f}" text-anchor="middle" font-size="11.5" font-weight="600" fill="#1b1f24">{fmt(v)}</text>')
            for j, word in enumerate(lbl.split(" ")):
                out.append(f'<text x="{x+bw/2:.0f}" y="{base_y+13+j*11}" text-anchor="middle" font-size="9.5" fill="#5b6571">{esc(word)}</text>')
    panel(20, "accuracy (tasks passed of 12)", lambda a: A[a]["passed"], 12, lambda v: f"{v}")
    panel(360, "pace (mean minutes per task)", lambda a: A[a]["run_min"] / 12, 4.5, lambda v: f"{v:.1f}m")
    out.append(f'<line x1="330" y1="10" x2="330" y2="244" stroke="#e7e6e1"/>')
    out.append(f'<text x="20" y="272" font-size="10.5" fill="#8a929c">faded bars = pre-fix harness (throttled inputs) · solid = post-fix · both cold arms are the same prompt on the same tasks</text>')
    out.append("</svg>")
    return "".join(out)

def accuracy_grid():
    """Preserved: pass/fail identity grid, post-fix arms + CinC, pre-fix arms appended muted."""
    arms = list(ARM_META) + PREFIX_ARMS
    heads = "".join(
        f'<th style="min-width:74px{";opacity:.55" if a in PREFIX_ARMS else ""}">{esc((ARM_META.get(a) or (PREFIX_LABEL[a],))[0])}</th>'
        for a in arms)
    rows = []
    for t in ORDER:
        cells = []
        for a in arms:
            r = H[a][t]
            mut = "opacity:.55;" if a in PREFIX_ARMS else ""
            if r["passed"]:
                cells.append(f'<td style="{mut}text-align:center;color:#0f8a5f" title="{esc(t)} · {r["run_min"]}min">●</td>')
            else:
                cells.append(f'<td style="{mut}text-align:center" title="{esc(t)} · {r["run_min"]}min"><span style="font-size:10px;font-weight:700;color:#c13a2e">FAIL</span></td>')
        rows.append(f'<tr><td class="mono" style="white-space:nowrap">{esc(t)}</td>{cells}</tr>'.replace("{cells}", "".join(cells)))
    body = "".join(f'<tr><td class="mono" style="white-space:nowrap">{esc(t)}</td>' + "".join(
        (lambda r, mut: f'<td style="{mut}text-align:center;color:#0f8a5f" title="{r["run_min"]}min">●</td>' if r["passed"]
         else f'<td style="{mut}text-align:center" title="{r["run_min"]}min"><span style="font-size:10px;font-weight:700;color:#c13a2e">FAIL</span></td>')
        (H[a][t], "opacity:.55;" if a in PREFIX_ARMS else "") for a in arms) + "</tr>" for t in ORDER)
    foot = "<tr><td style='font-weight:600'>passed</td>" + "".join(
        f'<td style="text-align:center;font-weight:700{";opacity:.55" if a in PREFIX_ARMS else ""}">{A[a]["passed"]}/12</td>' for a in arms) + "</tr>"
    return f'<div class="scroll"><table><thead><tr><th>task</th>{heads}</tr></thead><tbody>{body}{foot}</tbody></table></div>'

def stat_table(tests):
    rows = []
    for label, t in tests:
        r = t["time"]; al = r["all"]; pb = r["pass_both"]; acc = r["accuracy"]
        rows.append(
            f"<tr><td>{esc(label)}</td>"
            f"<td class='num'>{al['mean_a']:.2f} vs {al['mean_b']:.2f}</td>"
            f"<td class='num'>{al['mean_diff']:+.2f}</td><td class='num'>{fmt_p(al['p_perm'])}</td>"
            f"<td class='num'>{pb.get('mean_diff', float('nan')):+.2f} (n={pb['n']})</td>"
            f"<td class='num'>{fmt_p(pb['p_perm']) if 'p_perm' in pb else '·'}</td>"
            f"<td class='num'>{acc['pass_a']} vs {acc['pass_b']}</td><td class='num'>{fmt_p(acc['p_mcnemar'])}</td></tr>")
    return ("<div class='scroll'><table><thead><tr><th>comparison (A vs B)</th><th>mean min/task</th>"
            "<th>Δ all 12</th><th>p</th><th>Δ pass-both</th><th>p</th><th>accuracy</th><th>p</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def _pearson(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    dy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0

def _rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]: j += 1
        for k in range(i, j + 1): r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r

def _spearman(xs, ys): return _pearson(_rank(xs), _rank(ys))

def savings_chart():
    """Per-task time saved vs task length (cold-run duration), pre-fix and
    post-fix panels. Hue = experience source; hollow = raw, solid = analysis."""
    PINK, EMERALD = "#db2777", "#10b981"
    panels = [
        ("pre-fix pairs (cold = 1A Brave)", "exp1a-ocic-cold", [
            ("2A raw self traces", "exp2a-experiential", PINK, False),
            ("2B raw expert recordings", "exp2b-expert", EMERALD, False),
        ]),
        ("post-fix pairs (cold = 1A-fixed Brave)", "exp1a-fixed-brave", [
            ("2A-fixed experiential raw", "exp2a-fixed-brave", PINK, False),
            ("3D experiential analysis", "exp3d-experiential-analysis", PINK, True),
            ("2B-fixed expert raw", "exp2b-fixed-brave", EMERALD, False),
            ("3C expert analysis", "exp3c-analysis", EMERALD, True),
        ]),
    ]
    w, hgt = 660, 330
    pw = 296; pad_l = 46; pad_t = 34; pad_b = 46
    xmax, ymin, ymax = 11.0, -10.0, 7.0
    out = [svg_open(w, hgt)]
    stats_rows = []
    for pi, (title, cold, arms) in enumerate(panels):
        x0 = 10 + pi * (pw + 34)
        def X(v, x0=x0): return x0 + pad_l + (pw - pad_l - 8) * min(v, xmax) / xmax
        def Y(v): return pad_t + (hgt - pad_t - pad_b) * (ymax - max(min(v, ymax), ymin)) / (ymax - ymin)
        out.append(f'<text x="{x0+pad_l}" y="20" font-size="12" font-weight="600" fill="#1b1f24">{esc(title)}</text>')
        for gy in (-10, -5, 0, 5):
            wgt = 2 if gy == 0 else 1
            colr = "#c9c7c1" if gy == 0 else "#e7e6e1"
            out.append(f'<line x1="{x0+pad_l}" y1="{Y(gy):.0f}" x2="{x0+pw}" y2="{Y(gy):.0f}" stroke="{colr}" stroke-width="{wgt}"/>'
                       f'<text x="{x0+pad_l-5}" y="{Y(gy)+4:.0f}" text-anchor="end" font-size="10" fill="#8a929c">{gy:+d}m</text>')
        for gx in (3, 6, 9):
            out.append(f'<text x="{X(gx):.0f}" y="{hgt-28}" text-anchor="middle" font-size="10" fill="#8a929c">{gx}m</text>')
        out.append(f'<text x="{x0+pad_l+(pw-pad_l)/2:.0f}" y="{hgt-14}" text-anchor="middle" font-size="10.5" fill="#5b6571">task length: cold-run minutes on the task</text>')
        for lbl, arm, col, solid in arms:
            if arm not in H or len(H[arm]) < 12: continue
            xs = [H[cold][t]["run_min"] for t in ORDER]
            ys = [H[cold][t]["run_min"] - H[arm][t]["run_min"] for t in ORDER]
            rho = _spearman(xs, ys); r = _pearson(xs, ys)
            stats_rows.append((title.split(" (")[0], lbl, r, rho))
            fill = col if solid else "#fbfbf9"
            for t, xv, yv in zip(ORDER, xs, ys):
                clip = "" if ymin <= yv <= ymax else " (point clipped to border)"
                out.append(f'<circle cx="{X(xv):.1f}" cy="{Y(yv):.1f}" r="4.2" fill="{fill}" fill-opacity="0.9" stroke="{col}" stroke-width="1.8"><title>{esc(lbl)} · {esc(t)}: cold {xv:.1f}m, saved {yv:+.1f}m{clip}</title></circle>')
    out.append("</svg>")
    tab = "".join(f"<tr><td>{esc(p)}</td><td>{esc(l)}</td><td class=\"num\">{r:+.2f}</td><td class=\"num\">{rho:+.2f}</td></tr>"
                  for p, l, r, rho in stats_rows)
    table = ("<div class=\"scroll\"><table><thead><tr><th>era</th><th>pre-trained arm vs its cold baseline</th>"
             "<th>Pearson r</th><th>Spearman \u03c1</th></tr></thead><tbody>" + tab + "</tbody></table></div>")
    return "".join(out), table

# dashdish-8 exhibits ported verbatim from the archived report
SAV_SVG, SAV_TABLE = savings_chart()

