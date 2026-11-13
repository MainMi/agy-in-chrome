#!/usr/bin/env python3
"""Six annotated variants of "the same arms in scalar space", one per phase,
for the "Tying Them All Together" recap. Same base plot every time (all 13
arms, same axes, same baseline crosshair) so the reader always has the full
picture; per phase, only which arms are popped vs. faded plus a small set of
annotations changes.

Annotation system (deliberate, after a round of feedback):
- MOVEMENT is the only thing arrows are used for, and every movement is
  decomposed into its axis components, coordinate-space style: a horizontal
  arrow (the turns delta) then a vertical arrow (the latency delta). Each
  segment is coloured by its own direction: green = improving (left = fewer
  turns, down = faster), muted red = worsening (right, up). Arrows stand off
  from the dots (never touch them) - precision is secondary to legibility,
  so near-overlapping parallels are stacked a few px apart instead.
- POINTING is done by encircling, never by arrows: the capstone rankScatter's
  exact grouping style (tinted dashed ellipse behind the dots, bold coloured
  label + muted sublabel above/below).
- Commentary text is neutral dark slate, not alarm-coloured.

Chrome headless -> PNG. Run: python3 build_phase_highlight.py (builds all 6)."""
from phase_draw import *

def base_chart(title, subtitle, highlight, context=()):
    """highlight: fully popped arms. context: mid-emphasis arms (visible dots +
    small labels) so a claim about them has something to point at. The rest
    fade to background."""
    s = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Inter,sans-serif">')
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    s.append(f'<rect x="{PL}" y="{Y(by):.1f}" width="{X(bx)-PL:.1f}" height="{H-PB-Y(by):.1f}" fill="#0f8a5f" fill-opacity="0.05"/>')
    for g in range(25, XMAX + 1, 5):
        s.append(f'<line x1="{X(g):.1f}" y1="{PT}" x2="{X(g):.1f}" y2="{H-PB}" stroke="#f1f0ec"/>')
        s.append(f'<text x="{X(g):.1f}" y="{H-PB+18}" text-anchor="middle" font-size="11" fill="#8a929c">{g}</text>')
    for g in range(20, YMAX + 1, 10):
        s.append(f'<line x1="{PL}" y1="{Y(g):.1f}" x2="{W-PR}" y2="{Y(g):.1f}" stroke="#f6f5f1"/>')
        s.append(f'<text x="{PL-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#8a929c">{g}m</text>')
    s.append(f'<line x1="{X(bx):.1f}" y1="{PT}" x2="{X(bx):.1f}" y2="{H-PB}" stroke="#c9c7c1" stroke-width="1.2" stroke-dasharray="6 5" opacity="0.7"/>')
    s.append(f'<line x1="{PL}" y1="{Y(by):.1f}" x2="{W-PR}" y2="{Y(by):.1f}" stroke="#c9c7c1" stroke-width="1.2" stroke-dasharray="6 5" opacity="0.7"/>')
    s.append(f'<text x="{X(bx)+8:.1f}" y="{PT+13:.1f}" font-size="10.5" fill="#8a929c">Phase-1 baseline</text>')
    s.append(f'<text x="{(PL+W-PR)/2:.1f}" y="{H-24}" text-anchor="middle" font-size="13" fill="#5b6571">turns per task (path length) &#8594; more</text>')
    s.append(f'<text x="24" y="{(PT+H-PB)/2:.1f}" text-anchor="middle" font-size="13" fill="#5b6571" transform="rotate(-90 24 {(PT+H-PB)/2:.1f})">latency (minutes, suite) &#8594; slower</text>')
    s.append(f'<text x="{PL}" y="34" font-size="18" font-weight="700" fill="#1b1f24">{title}</text>')
    s.append(f'<text x="{PL}" y="52" font-size="12.5" fill="#8a929c">{subtitle}</text>')
    return s

def draw_arms(s, highlight, context=()):
    """Dots go on top of ellipses/arrows; call after annotations."""
    for a in ARMS:
        sh = a["short"]
        cx, cy = X(a["turns"]), Y(a["min"])
        col = COLOR[sh]
        dx, dy, anc = LBL[sh]
        if sh == "6b" and sh in highlight:
            s.append(f'<path d="{star(cx, cy, 12, 5)}" fill="{col}" stroke="#7a3a00" stroke-width="1.3"/>')
            s.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anc}" font-size="13" font-weight="800" fill="#1b1f24">{sh}</text>')
        elif sh in highlight:
            s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7.5" fill="{col}" stroke="#fff" stroke-width="1.6"/>')
            s.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anc}" font-size="13" font-weight="800" fill="#1b1f24">{sh}</text>')
        elif sh in context:
            s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{col}" opacity="0.6" stroke="#fff" stroke-width="1"/>')
            s.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anc}" font-size="9.5" font-weight="600" fill="{SUB}" opacity="0.85">{sh}</text>')
        else:
            s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="{col}" opacity="0.28"/>')

def finish(s, name):
    s.append('</svg>')
    svg = "\n".join(s)
    open(os.path.join(HERE, f"{name}.html"), "w").write(
        f'<!doctype html><meta charset="utf-8"><style>*{{margin:0}}body{{background:#fff}}</style>{svg}')
    print("wrote", name)

# ---------- Phase 1: each harness's top performer, encircled ----------
# 1a (official CinC) vs 1c (open harness, primary baseline): comparable turns
# and 1c is actually faster. 1b (the open harness on Chrome) sits outside the
# ring at context emphasis with a note, so it reads as a variant, not a
# counterexample.
s = base_chart("Phase 1 · the control group",
               "each harness's best cold run: official (1a) vs. open (1c) - comparable turns, and 1c is faster", ["1a", "1c"], context=["1b"])
s.append(group_ellipse(["1a", "1c"], GROUP_BLUE, "practically the same performance",
                       "official harness (1a) vs. the open one (1c) - and 1c has the better latency",
                       lp="below", padx=18, pady=16, contain=True))
bx1, by1 = X(BY["1b"]["turns"]), Y(BY["1b"]["min"])
s.append(note(bx1 + 14, by1 + 18, "1b is the open harness too, just on Chrome", size=10.5, weight=600, rot=-1))
draw_arms(s, ["1a", "1c"], context=["1b"])
finish(s, "phase1_highlight")

# ---------- Phase 2: baseline -> 2a / 2b; the two rightward runs stack ----------
s = base_chart("Phase 2 · mounting raw experience",
               "2a saves latency, not turns; 2b saves neither - but both get more accurate", ["2a", "2b"])
s.append(axis_arrows(X(bx), Y(by), X(BY["2a"]["turns"]), Y(BY["2a"]["min"]), row_shift=+7, src_standoff=False))
s.append(axis_arrows(X(bx), Y(by), X(BY["2b"]["turns"]), Y(BY["2b"]["min"]), row_shift=-7, src_standoff=False))
cx, cy = X(BY["2b"]["turns"]), Y(BY["2b"]["min"])
shaft_y = Y(by)
s.append(note(cx - 20, shaft_y - 31, "2b got MORE ACCURATE", size=13, anchor="end", rot=2))
s.append(note(cx - 20, shaft_y - 14, "you just can't see it on this chart", size=11, weight=600, anchor="end", rot=1))
draw_arms(s, ["2a", "2b"])
finish(s, "phase2_highlight")

# ---------- Phase 3: 2a->3a, 2b->3b; the 3a latency surprise ----------
s = base_chart("Phase 3 · compressing the search tax",
               "turns drop for both - but 3a's latency doesn't beat 2a. plot twist.", ["2a", "2b", "3a", "3b"])
s.append(axis_arrows(X(BY["2a"]["turns"]), Y(BY["2a"]["min"]), X(BY["3a"]["turns"]), Y(BY["3a"]["min"])))
s.append(axis_arrows(X(BY["2b"]["turns"]), Y(BY["2b"]["min"]), X(BY["3b"]["turns"]), Y(BY["3b"]["min"])))
cx, cy = X(BY["3a"]["turns"]), Y(BY["3a"]["min"])
s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="13" fill="none" stroke="{BAD}" stroke-width="1.6" stroke-dasharray="4 3"/>')
s.append(note(cx - 24, cy + 48, "??? still worse than 2a on latency", size=13, anchor="end"))
s.append(note(cx - 24, cy + 65, "fewer turns didn't buy back the time", size=11, weight=600, rot=-1, anchor="end"))
draw_arms(s, ["2a", "2b", "3a", "3b"])
finish(s, "phase3_highlight")

# ---------- Phase 4: 3a->4a, 3b->4b; the context tax, in red ----------
s = base_chart("Phase 4 · forking the whole session in",
               "context explodes, latency follows - turns barely move to compensate", ["3a", "3b", "4a", "4b"])
s.append(axis_arrows(X(BY["3a"]["turns"]), Y(BY["3a"]["min"]), X(BY["4a"]["turns"]), Y(BY["4a"]["min"]), width=4))
s.append(axis_arrows(X(BY["3b"]["turns"]), Y(BY["3b"]["min"]), X(BY["4b"]["turns"]), Y(BY["4b"]["min"]), width=4))
cx, cy = X(BY["4a"]["turns"]), Y(BY["4a"]["min"])
s.append(note(cx - 6, cy - 20, "latency goes THROUGH THE ROOF", size=16, anchor="middle", rot=-2))
s.append(note(cx - 22, cy + 36, "turns: only a little better.", size=11.5, weight=600, anchor="end", rot=1))
s.append(note(cx - 22, cy + 51, "not worth it.", size=11.5, weight=600, anchor="end", rot=1))
draw_arms(s, ["3a", "3b", "4a", "4b"])
finish(s, "phase4_highlight")

# ---------- Phase 5: recipes vs the entire prior field ----------
# The prior field is enclosed as the capstone's own two natural groups (one
# bbox ellipse over this L-shaped spread would either clip its corners or
# swallow the recipes): the compact phases-1-3 pack, and the two phase-4
# forks stranded above it.
PACK = ["1a", "1b", "1c", "2a", "2b", "3a", "3b"]
FORKS = ["4a", "4b"]
s = base_chart("Phase 5 · ditch the workspace, prompt a recipe",
               "biggest jump yet - and single vs. per-site recipe barely matters", ["5a", "5b"], context=PACK + FORKS)
s.append(group_ellipse(PACK, GROUP_BLUE, "everything from phases 1-3",
                       "the whole pack sits up and to the right", lp="below", padx=26, pady=20))
s.append(group_ellipse(FORKS, BAD, "the phase-4 forks", "stranded by the context tax", lp="below", padx=26, pady=20, contain=True))
s.append(group_ellipse(["5a", "5b"], GOOD, "", "", padx=16, pady=14, contain=True))
gx = (X(BY["5a"]["turns"]) + X(BY["5b"]["turns"])) / 2
gy = (Y(BY["5a"]["min"]) + Y(BY["5b"]["min"])) / 2
s.append(note(gx - 44, gy - 4, "same dot, basically", size=13, anchor="end"))
s.append(note(gx - 44, gy + 13, "and it beats all of them", size=11, weight=600, rot=-1, anchor="end"))
draw_arms(s, ["5a", "5b"], context=PACK + FORKS)
finish(s, "phase5_highlight")

# ---------- Phase 6: 4a -> 6a (the shocker), then 6a -> 6b (the winner) ----------
s = base_chart("Phase 6 · does warming up alone pay off?",
               "6a alone matches 4a's turn savings for a THIRD of the latency tax. then 6b stacks the recipe on top.", ["4a", "6a", "6b"])
s.append(axis_arrows(X(BY["4a"]["turns"]), Y(BY["4a"]["min"]), X(BY["6a"]["turns"]), Y(BY["6a"]["min"]), width=4))
cx, cy = X(BY["6a"]["turns"]), Y(BY["6a"]["min"])
midy = (Y(BY["4a"]["min"]) + cy) / 2
s.append(note(cx + 26, midy - 8, "wait, WHAT", size=15))
s.append(note(cx + 26, midy + 9, "1 warm-up example &#8776; the whole fork's turn savings", size=11, weight=600, rot=-1))
s.append(axis_arrows(cx, cy, X(BY["6b"]["turns"]), Y(BY["6b"]["min"]), width=3.4, dst_standoff=17))
s.append(note(PL + 16, cy - 18, "and 6b just wins outright", size=12.5, rot=-2))
draw_arms(s, ["4a", "6a", "6b"])
finish(s, "phase6_highlight")

print("all 6 written")

