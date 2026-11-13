# Split out of build_report_v2.py — pure refactor, behavior unchanged.

from report_v2_data import *

def slope_chart(a, b, w=330, hgt=300, title=""):
    """Paired per-task slope chart: every task a line from arm B (left) to arm A (right)."""
    la, lb = SUM[a], SUM[b]
    pad_t, pad_b, pad_l, pad_r = 26, 30, 46, 46
    vals = [(HARV[b][t]["run_min"], HARV[a][t]["run_min"], t) for t in ORDER]
    vmax = max(max(v[0], v[1]) for v in vals) * 1.06
    def Y(v): return pad_t + (hgt - pad_t - pad_b) * (1 - v / vmax)
    x0, x1 = pad_l, w - pad_r
    out = [f'<svg viewBox="0 0 {w} {hgt}" width="100%" style="max-width:{w}px" font-family="inherit" role="img">']
    out.append(f'<text x="{w/2:.0f}" y="14" text-anchor="middle" font-size="11.5" font-weight="600" fill="#1b1f24">{H.escape(title)}</text>')
    for gy in range(0, int(vmax) + 1, 3):
        out.append(f'<line x1="{x0}" y1="{Y(gy):.1f}" x2="{x1}" y2="{Y(gy):.1f}" stroke="#f3f2ee"/>')
        out.append(f'<text x="{x0-5}" y="{Y(gy)+3:.1f}" text-anchor="end" font-size="9" fill="#8a929c">{gy}m</text>')
    for vb, va, t in vals:
        worse = va > vb + 1e-9
        col = "#c13a2e" if worse else "#0f8a5f"
        out.append(f'<line x1="{x0}" y1="{Y(vb):.1f}" x2="{x1}" y2="{Y(va):.1f}" stroke="{col}" stroke-width="1.6" opacity="0.75"><title>{t}: {lb["short"]} {vb:.1f}m &#8594; {la["short"]} {va:.1f}m</title></line>')
        out.append(f'<circle cx="{x0}" cy="{Y(vb):.1f}" r="2.6" fill="#5b6571"/>')
        out.append(f'<circle cx="{x1}" cy="{Y(va):.1f}" r="2.6" fill="{col}"/>')
    out.append(f'<text x="{x0}" y="{hgt-8}" text-anchor="middle" font-size="10.5" fill="#5b6571">{H.escape(lb["short"])}</text>')
    out.append(f'<text x="{x1}" y="{hgt-8}" text-anchor="middle" font-size="10.5" fill="#5b6571">{H.escape(la["short"])}</text>')
    out.append('</svg>')
    return "".join(out)

def ladder_chart():
    """First-action latency ladder + per-turn pace: the mechanism panel."""
    rows = [("exp1a-fixed-brave",), ("exp3c-analysis",), ("exp2b-fixed-brave",),
            ("exp4b-expert-fork",), ("exp4a-experiential-fork",)]
    w, rh, pad_l, pad_t = 660, 30, 190, 26
    hgt = pad_t + rh * len(rows) * 2 + 46
    fmax = 26.0; pmax = 8.0
    half = (w - pad_l - 30) / 2
    def X1(v): return pad_l + half * min(v, fmax) / fmax
    def X2(v): return pad_l + half + 26 + (half - 26) * min(v, pmax) / pmax
    out = [f'<svg viewBox="0 0 {w} {hgt}" width="100%" style="max-width:{w}px" font-family="inherit">']
    out.append(f'<text x="{pad_l}" y="14" font-size="11.5" font-weight="600" fill="#1b1f24">median seconds to FIRST browser action</text>')
    out.append(f'<text x="{pad_l+half+26}" y="14" font-size="11.5" font-weight="600" fill="#1b1f24">seconds of run per model turn</text>')
    y = pad_t
    for (a,) in rows:
        s = SUM[a]
        out.append(f'<text x="{pad_l-8}" y="{y+13}" text-anchor="end" font-size="11.5" fill="#1b1f24">{H.escape(s["label"])}</text>')
        fa = s["first_action_s"] or 0
        out.append(f'<rect x="{pad_l}" y="{y}" width="{X1(fa)-pad_l:.1f}" height="16" rx="3" fill="{s["color"]}" opacity="0.85"><title>{H.escape(s["label"])}: {fa}s to first action</title></rect>')
        out.append(f'<text x="{X1(fa)+5:.1f}" y="{y+12}" font-size="10.5" fill="#5b6571">{fa:.0f}s</text>')
        pt = s["per_turn_s"]
        out.append(f'<rect x="{pad_l+half+26}" y="{y}" width="{X2(pt)-(pad_l+half+26):.1f}" height="16" rx="3" fill="{s["color"]}" opacity="0.85"><title>{H.escape(s["label"])}: {pt}s per turn</title></rect>')
        out.append(f'<text x="{X2(pt)+5:.1f}" y="{y+12}" font-size="10.5" fill="#5b6571">{pt:.1f}s</text>')
        y += rh + 8
    out.append(f'<text x="{pad_l}" y="{y+18}" font-size="10.5" fill="#8a929c">Forks pay before they move, then pay again on every turn. Cold and mounted arms stay light.</text>')
    out.append('</svg>')
    return "".join(out)

def scatter_turns_time():
    """One point per post-fix arm: mean turns vs mean min/task. The fork story in one look."""
    arms = list(ARMS)
    w, hgt, pl, pt, pb, pr = 660, 330, 56, 18, 42, 150
    xmax = max(SUM[a]["turns"] for a in arms) * 1.12
    ymax = max(SUM[a]["mean_task"] for a in arms) * 1.14
    def X(v): return pl + (w - pl - pr) * v / xmax
    def Y(v): return hgt - pb - (hgt - pt - pb) * v / ymax
    out = [f'<svg viewBox="0 0 {w} {hgt}" width="100%" style="max-width:{w}px" font-family="inherit">']
    for gx in range(0, int(xmax) + 1, 15):
        out.append(f'<line x1="{X(gx):.0f}" y1="{pt}" x2="{X(gx):.0f}" y2="{hgt-pb}" stroke="#f3f2ee"/><text x="{X(gx):.0f}" y="{hgt-pb+14}" text-anchor="middle" font-size="10" fill="#8a929c">{gx}</text>')
    for gy in range(0, int(ymax) + 1):
        out.append(f'<line x1="{pl}" y1="{Y(gy):.0f}" x2="{w-pr}" y2="{Y(gy):.0f}" stroke="#f3f2ee"/><text x="{pl-6}" y="{Y(gy)+3:.0f}" text-anchor="end" font-size="10" fill="#8a929c">{gy}m</text>')
    out.append(f'<text x="{(pl+w-pr)/2:.0f}" y="{hgt-8}" text-anchor="middle" font-size="11" fill="#5b6571">mean model turns per task</text>')
    out.append(f'<text x="14" y="{(pt+hgt-pb)/2:.0f}" font-size="11" fill="#5b6571" transform="rotate(-90 14 {(pt+hgt-pb)/2:.0f})" text-anchor="middle">mean minutes per task</text>')
    lab_used = []
    for a in arms:
        s = SUM[a]
        x, y = X(s["turns"]), Y(s["mean_task"])
        hollow = s["delivery"] == "raw"
        dash = s["delivery"] == "fork"
        fill = "#fbfbf9" if hollow else s["color"]
        extra = f' stroke-dasharray="3 2"' if dash else ""
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{fill}" stroke="{s["color"]}" stroke-width="2"{extra}><title>{H.escape(s["label"])}: {s["turns"]} turns, {s["mean_task"]}m/task, {s["passed"]}/12</title></circle>')
        ly = y
        while any(abs(ly - u) < 13 for u in lab_used): ly -= 13
        lab_used.append(ly)
        out.append(f'<text x="{x+10:.1f}" y="{ly+4:.1f}" font-size="10.5" fill="{s["color"]}">{H.escape(s["short"])} · {s["passed"]}/12</text>')
    out.append('</svg>')
    return "".join(out)

# ---- HTML assembly ------------------------------------------------------------

def focus_table():
    rows = []
    for r in FOCUS:
        rows.append(
            f"<tr><td>{H.escape(r['label'])}</td>"
            f"<td class='num'>{r['n']}</td><td class='num'>{r['flagged']}</td><td>{H.escape(r['top'])}</td>"
            f"<td class='num'>{r['raw_tool']:.2f} &rarr; {r['adj_tool']:.2f}</td>"
            f"<td class='num'>{r['med']:.3f} &rarr; {r['med_adj']:.3f}</td>"
            f"<td class='num'><b>{r['raw_total']:.1f} &rarr; {r['adj_total']:.1f}</b></td></tr>")
    return ("<div class='scroll'><table><thead><tr><th>arm</th><th>browser calls</th><th>flagged &gt;1.5s</th>"
            "<th>top flagged tool</th><th>tool min (as-run &rarr; adj)</th><th>median s (as-run &rarr; adj)</th>"
            "<th>12-task total min (as-run &rarr; adj)</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")

def ev_table(ids, note=""):
    rows = []
    for cid in ids:
        e = EV[cid]; t = e["time"]
        p = e.get("p_time"); ps = (" · p=" + (("%.4f" % p).rstrip("0").rstrip(".")) if p is not None else "")
        rows.append(
            f"<tr class='evrow'><td>{H.escape(e['label'])}</td>"
            f"<td class='num'>{e['pass_a']} vs {e['pass_b']}</td>"
            f"<td class='num'>{t['mean']:+.2f} <span class='ci'>[{t['lo']:+.2f}, {t['hi']:+.2f}]</span></td>"
            f"<td class='num'>{t['wl']}</td>"
            f"<td class='num'>{e['turns']['mean']:+.1f}</td>"
            f"<td class='ci'>{ps.lstrip(' ·')}</td></tr>")
    return ("<div class='scroll'><table><thead><tr><th>comparison (A vs B)</th><th>accuracy</th>"
            "<th>&Delta; min/task <span style='text-transform:none'>[95% bootstrap CI]</span></th>"
            "<th>A faster&ndash;slower</th><th>&Delta; turns</th><th>exact p (footnote)</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
            + (f"<p class='note'>{note}</p>" if note else ""))

