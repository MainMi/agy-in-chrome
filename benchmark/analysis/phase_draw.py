# Drawing geometry + helpers for build_phase_highlight.py — split out as
# a pure refactor; behavior unchanged.

import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "capstone.json")))

RENAME = {"CinC": "1a", "OCIC-Ch": "1b", "OCIC-Br": "1c", "2A": "2a", "2B": "2b",
          "3D": "3a", "3C": "3b", "4A": "4a", "4B": "4b", "5B": "5a", "5A": "5b",
          "5C": "6a", "5D": "6b"}
COLOR = {RENAME[k]: v for k, v in D["dist_byleg"]["color"].items()}
ARMS = [{"short": RENAME[a["short"]], "turns": a["turns"], "min": a["min"]}
        for a in D["rankcompare"]["arms"]]
BY = {a["short"]: a for a in ARMS}

P1 = ["1a", "1b", "1c"]
bx = sum(BY[s]["turns"] for s in P1) / len(P1)
by = sum(BY[s]["min"] for s in P1) / len(P1)

W, H = 1120, 690
PL, PR, PT, PB = 74, 150, 62, 66
XMIN, XMAX = 22, 42
YMIN, YMAX = 17, 60
def X(v): return PL + (W - PL - PR) * (v - XMIN) / (XMAX - XMIN)
def Y(v): return PT + (H - PT - PB) * (YMAX - v) / (YMAX - YMIN)

GOOD = "#0f8a5f"    # improving movement (left / down) - the deck's green
BAD = "#c13a2e"     # worsening movement (right / up) - the deck's muted red
NOTE = "#3a4148"    # commentary ink - neutral dark slate
SUB = "#5b6571"     # secondary commentary
GROUP_BLUE = "#3f6ea8"  # capstone rankScatter's neutral grouping blue
STAND = 13          # px standoff between an arrow end and the dot it serves

LBL = {
    "1a": (-11, -9, "end"), "1b": (10, -6, "start"), "1c": (10, 13, "start"),
    "2a": (0, 17, "middle"), "2b": (-11, 4, "end"), "3a": (11, 1, "start"),
    "3b": (11, 4, "start"), "4a": (12, 4, "start"), "4b": (12, 4, "start"),
    "5a": (-9, -9, "end"), "5b": (10, 13, "start"), "6a": (1, -12, "middle"),
    "6b": (-19, -8, "end"),
}

def star(cx, cy, ro, ri, n=5):
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = -math.pi / 2 + i * math.pi / n
        pts.append(f"{cx + r*math.cos(a):.2f},{cy + r*math.sin(a):.2f}")
    return "M" + "L".join(pts) + "Z"

def arrow(x0, y0, x1, y1, color, width=3.2):
    ang = math.atan2(y1 - y0, x1 - x0)
    ah = 9
    a1 = ang + math.radians(150); a2 = ang - math.radians(150)
    head = (f"M{x1:.1f} {y1:.1f} L{x1+ah*math.cos(a1):.1f} {y1+ah*math.sin(a1):.1f} "
            f"M{x1:.1f} {y1:.1f} L{x1+ah*math.cos(a2):.1f} {y1+ah*math.sin(a2):.1f}")
    return (f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'
            f'<path d="{head}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" fill="none"/>')

def axis_arrows(x0, y0, x1, y1, width=3.2, row_shift=0.0, src_standoff=True, dst_standoff=STAND):
    """One movement, decomposed: horizontal arrow (turns delta), then vertical
    arrow (latency delta), each coloured by its own direction. row_shift nudges
    the horizontal run vertically so two near-parallel movements can stack
    instead of overlapping. Both ends stand clear of the dots."""
    out = []
    yrow = y0 + row_shift
    hx0 = x0
    if abs(x1 - x0) >= 14:
        hcol = GOOD if x1 < x0 else BAD
        if src_standoff:
            hx0 = x0 + (STAND if x1 > x0 else -STAND)
        out.append(arrow(hx0, yrow, x1, yrow, hcol, width))
    else:
        yrow = y0 + (row_shift if abs(row_shift) > 0 else 0)
    if abs(y1 - y0) >= 14:
        vcol = GOOD if y1 > y0 else BAD  # screen-down = lower latency = good
        vy0 = yrow
        vy1 = y1 - (dst_standoff if y1 > y0 else -dst_standoff)
        if abs(x1 - x0) < 14 and src_standoff:
            vy0 = y0 + (STAND if y1 > y0 else -STAND)
        out.append(arrow(x1, vy0, x1, vy1, vcol, width))
    return "".join(out)

def group_ellipse(shorts, col, label, sub, lp="above", padx=30, pady=24, contain=False):
    """The capstone rankScatter grouping style: tinted dashed ellipse fitted to
    the member dots, bold coloured label + muted sublabel. contain=True scales
    the radii until every member is strictly inside - right for small compact
    groups; for wide flat packs the capstone's own loose fit (corner dots may
    kiss the boundary) reads better than a blown-up enclosure."""
    pts = [(X(BY[s]["turns"]), Y(BY[s]["min"])) for s in shorts]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2
    rx = (max(xs) - min(xs)) / 2 + padx; ry = (max(ys) - min(ys)) / 2 + pady
    if contain:
        kmax = max(math.hypot((px - cx) / rx, (py - cy) / ry) for px, py in pts)
        scale = max(1.0, kmax * 1.06)
        rx *= scale; ry *= scale
    ly = cy - ry - 21 if lp == "above" else cy + ry + 16
    out = [f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
           f'fill="{col}" fill-opacity="0.06" stroke="{col}" stroke-width="1.4" stroke-dasharray="6 4"/>']
    if label:
        out.append(f'<text x="{cx:.1f}" y="{ly:.1f}" text-anchor="middle" font-size="12.5" font-weight="700" fill="{col}">{label}</text>')
    if sub:
        out.append(f'<text x="{cx:.1f}" y="{ly+15:.1f}" text-anchor="middle" font-size="10.5" fill="{SUB}">{sub}</text>')
    return "".join(out)

def note(x, y, text, size=13.5, rot=-2, anchor="start", weight=800, color=NOTE):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" font-style="italic" fill="{color}" '
            f'transform="rotate({rot} {x:.1f} {y:.1f})">{text}</text>')

