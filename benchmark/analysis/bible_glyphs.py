# SVG glyph primitives for build_style_bible.py — pure refactor,
# behavior unchanged.

import os, base64
BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))

def img_src(rel):  # reference the PNG by relative URL (HTML sits one dir above analysis/img/)
    p = os.path.join(HERE, rel)
    if not os.path.isfile(p):
        return ""
    return f"analysis/{rel}"

INK = "#2b2a27"; CREAM = "#f4f1ea"; PAPER = "#fdfbf5"; DESKC = "#efe9db"; GD = "#8f8c85"
G_FAINT = "#c9c6bf"; G_DARK = "#8f8c85"; HAIR = "#3a3833"

# ---------- glyphs ----------
# NOTE: the app under test (food-delivery vs real-estate) is NOT a tracked
# benchmark variable, so sheets carry a neutral title bar, never an app glyph.
def sheet_head(x, y, w=22):  # generic "this sheet has content" heading
    return f'<rect x="{x}" y="{y}" width="{w}" height="4" fill="{INK}"/>'

def title_bar(x, y):
    return sheet_head(x, y + 4, 22)

def distill_mark(x, y):  # tiny funnel = distilled recipe
    return (f'<g transform="translate({x},{y})" stroke="{INK}" stroke-width="1.4" fill="none">'
            f'<path d="M-4 -3 L4 -3 L1 1 L1 5 L-1 5 L-1 1 Z" fill="{PAPER}"/></g>')

# ---------- face (tiredness) ----------
HAIR_SETS = {
    "neat":  '<path d="M-25 -6 Q0 -34 25 -6 Q12 -20 0 -20 Q-12 -20 -25 -6 Z" fill="%s"/>' % HAIR,
    "cowlick":('<path d="M-25 -6 Q0 -34 25 -6 Q12 -20 0 -20 Q-12 -20 -25 -6 Z" fill="%s"/>' % HAIR
              + '<path d="M2 -26 Q6 -40 12 -30 Q7 -30 4 -24 Z" fill="%s"/>' % HAIR),
    "mess":  ('<path d="M-25 -6 Q0 -34 25 -6 Q12 -20 0 -20 Q-12 -20 -25 -6 Z" fill="%s"/>' % HAIR
              + '<path d="M2 -26 Q6 -42 12 -30 Z" fill="%s"/>' % HAIR
              + '<path d="M-14 -22 Q-20 -36 -8 -30 Z" fill="%s"/>' % HAIR
              + '<path d="M14 -20 Q26 -30 18 -18 Z" fill="%s"/>' % HAIR
              + '<path d="M-2 -28 Q0 -44 6 -32 Z" fill="%s"/>' % HAIR),
}
UNDEREYE = {"none": "", "faint": G_FAINT, "dark": G_DARK}

def crest_glyph(ex, ey, harness, sw=1.6, sc=1.0):
    p = lambda v: v * sc
    if harness == "ocic":  # open-source spark (4-point outline star)
        return (f'<path d="M{ex} {ey-p(5)} L{ex+p(1.8)} {ey-p(1.8)} L{ex+p(5)} {ey} L{ex+p(1.8)} {ey+p(1.8)} '
                f'L{ex} {ey+p(5)} L{ex-p(1.8)} {ey+p(1.8)} L{ex-p(5)} {ey} L{ex-p(1.8)} {ey-p(1.8)} Z" '
                f'fill="none" stroke="{INK}" stroke-width="{sw}"/>')
    # official = filled shield
    return (f'<path d="M{ex-p(4)} {ey-p(4)} L{ex+p(4)} {ey-p(4)} L{ex+p(4)} {ey+p(1)} '
            f'Q{ex+p(4)} {ey+p(5)} {ex} {ey+p(6)} Q{ex-p(4)} {ey+p(5)} {ex-p(4)} {ey+p(1)} Z" fill="{INK}"/>')

def face(cx, cy, hair, ue, crest=None):
    s = [f'<g transform="translate({cx},{cy})">']
    s.append(f'<circle r="24" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
    s.append(HAIR_SETS[hair])
    if crest:  # harness logo stamped on the brow (the "do not develop my app" mark)
        s.append(crest_glyph(0, -11, crest, sw=1.5))
    # eyes
    s.append(f'<circle cx="-8" cy="0" r="2.2" fill="{INK}"/><circle cx="8" cy="0" r="2.2" fill="{INK}"/>')
    # under-eye shadow
    col = UNDEREYE[ue]
    if col:
        s.append(f'<path d="M-12 6 Q-8 9 -4 6" stroke="{col}" stroke-width="2" fill="none" stroke-linecap="round"/>')
        s.append(f'<path d="M4 6 Q8 9 12 6" stroke="{col}" stroke-width="2" fill="none" stroke-linecap="round"/>')
    # mouth: flat for tired, tiny neutral line always
    s.append(f'<line x1="-5" y1="13" x2="5" y2="13" stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>')
    s.append('</g>')
    return "".join(s)

# ---------- torso + harness crest ----------
def torso(cx, cy, harness=None):  # body only; the harness logo now lives on the brow
    return (f'<path d="M{cx-26} {cy+34} Q{cx} {cy+14} {cx+26} {cy+34} L{cx+26} {cy+46} L{cx-26} {cy+46} Z" '
            f'fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')

# ---------- desk + browser emblem ----------
def desk(browser, W=220):
    y = 150
    s = [f'<rect x="6" y="{y}" width="{W-12}" height="6" fill="{INK}"/>',
         f'<rect x="6" y="{y+6}" width="{W-12}" height="58" fill="{CREAM}" stroke="{INK}" stroke-width="2.2"/>']
    ex, ey = W/2, y + 34
    if browser == "brave":  # lion / flame head, abstract
        s.append(f'<path d="M{ex} {ey-11} Q{ex+11} {ey-6} {ex+8} {ey+6} Q{ex} {ey+11} {ex-8} {ey+6} '
                 f'Q{ex-11} {ey-6} {ex} {ey-11} Z" fill="none" stroke="{INK}" stroke-width="1.8"/>'
                 f'<path d="M{ex-5} {ey-9} L{ex-8} {ey-14} M{ex+5} {ey-9} L{ex+8} {ey-14}" '
                 f'stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>')
    else:  # chrome = pinwheel
        s.append(f'<circle cx="{ex}" cy="{ey}" r="10" fill="none" stroke="{INK}" stroke-width="1.8"/>'
                 f'<circle cx="{ex}" cy="{ey}" r="3.4" fill="{INK}"/>'
                 f'<path d="M{ex} {ey} L{ex} {ey-10} M{ex} {ey} L{ex+9} {ey+5} M{ex} {ey} L{ex-9} {ey+5}" '
                 f'stroke="{INK}" stroke-width="1.8"/>')
    return "".join(s)

# ---------- exam paper (task) + optional clipped recipe ----------
def exam(recipe=0, distilled=False):
    # foreshortened sheet lying on the desk in front
    s = [f'<path d="M62 150 L158 150 L150 138 L70 138 Z" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>']
    s.append(title_bar(78, 141))
    s.append(f'<line x1="104" y1="144" x2="146" y2="144" stroke="{INK}" stroke-width="1" opacity=".5"/>')
    if recipe:  # recipe clipped ONTO the exam (in-task, unavoidable)
        # 1 combined sheet (5B) or 2 per-site sheets (5A); app is not a variable
        if recipe == 1:
            s.append(f'<g transform="translate(96,116)"><rect x="0" y="0" width="46" height="30" rx="1.5" '
                     f'fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
                     + sheet_head(8, 8, 30)
                     + f'<line x1="6" y1="20" x2="40" y2="20" stroke="{INK}" stroke-width="1.1"/>'
                     + f'<line x1="6" y1="24" x2="34" y2="24" stroke="{INK}" stroke-width="1.1"/>'
                     + (distill_mark(40, 5) if distilled else "")
                     + f'<rect x="20" y="-4" width="6" height="8" rx="2" fill="none" stroke="{INK}" stroke-width="1.6"/></g>')
        else:
            for i in range(2):
                xo = 84 + i * 30
                s.append(f'<g transform="translate({xo},116)"><rect x="0" y="0" width="26" height="30" rx="1.5" '
                         f'fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
                         + sheet_head(5, 8, 16)
                         + f'<line x1="5" y1="20" x2="21" y2="20" stroke="{INK}" stroke-width="1.1"/>'
                         + f'<line x1="5" y1="24" x2="17" y2="24" stroke="{INK}" stroke-width="1.1"/>'
                         + f'<rect x="10" y="-4" width="6" height="8" rx="2" fill="none" stroke="{INK}" stroke-width="1.6"/></g>')
    return "".join(s)

# ---------- binder (raw) + analysis sheet ----------
def binder(source, sheet=False):
    x, y = 158, 116  # right side of desk surface
    s = [f'<g transform="translate({x},{y})">']
    # closed thick book
    s.append(f'<rect x="0" y="6" width="44" height="30" rx="1.5" fill="{PAPER}" stroke="{INK}" stroke-width="2.2"/>')
    s.append(f'<rect x="0" y="6" width="8" height="30" fill="{CREAM}" stroke="{INK}" stroke-width="2.2"/>')
    if source == "own":  # scrappy: spiral rings on spine + rough scribble
        for k in range(4):
            s.append(f'<circle cx="4" cy="{11+k*7}" r="1.6" fill="none" stroke="{INK}" stroke-width="1.3"/>')
        s.append(f'<path d="M14 16 q6 -3 12 0 t12 0" stroke="{INK}" stroke-width="1.2" fill="none" opacity=".6"/>')
    else:  # expert: printed title bar
        s.append(f'<rect x="14" y="12" width="24" height="4" fill="{INK}"/>')
        s.append(f'<line x1="14" y1="22" x2="38" y2="22" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
        s.append(f'<line x1="14" y1="27" x2="34" y2="27" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
    if sheet:  # analysis: a clean sheet resting ON TOP, headers, source-styled
        rot = -6 if source == "own" else 0
        s.append(f'<g transform="translate(3,-8) rotate({rot})"><rect x="0" y="0" width="40" height="20" rx="1.5" '
                 f'fill="{PAPER}" stroke="{INK}" stroke-width="2"/>' + sheet_head(6, 6, 26))
        if source == "own":
            s.append(f'<path d="M5 14 q6 -2 10 0 t10 0" stroke="{INK}" stroke-width="1.1" fill="none" opacity=".6"/>')
        else:
            s.append(f'<line x1="5" y1="14" x2="35" y2="14" stroke="{INK}" stroke-width="1.1" opacity=".55"/>')
        s.append('</g>')
    s.append('</g>')
    return "".join(s)

# ---------- thought bubble (internalized) ----------
def bubble(content, size):
    cx, cy = 158, 40
    r = 30 if size == "big" else 19
    s = [f'<circle cx="{cx-r-6}" cy="{cy+r-2}" r="3" fill="{PAPER}" stroke="{INK}" stroke-width="1.6"/>',
         f'<circle cx="{cx-r-1}" cy="{cy+r+4}" r="2" fill="{PAPER}" stroke="{INK}" stroke-width="1.4"/>',
         f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{PAPER}" stroke="{INK}" stroke-width="2.2"/>']
    sc = 1.0 if size == "big" else 0.7
    g = [f'<g transform="translate({cx},{cy}) scale({sc})">']
    if content == "own":  # a past task it did: a graded, filled-in task sheet
        g.append(graded_sheet(0, 0, 1.0))
    elif content == "expert":  # clean closed book
        g.append(f'<rect x="-13" y="-15" width="26" height="30" rx="1.5" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>')
        g.append(f'<rect x="-13" y="-15" width="6" height="30" fill="{CREAM}" stroke="{INK}" stroke-width="2"/>')
        g.append(f'<rect x="-3" y="-9" width="14" height="4" fill="{INK}"/>')
        g.append(f'<line x1="-3" y1="1" x2="11" y2="1" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
    else:  # warmup: a completed practice sheet with a check
        g.append(f'<rect x="-12" y="-14" width="24" height="28" rx="1.5" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>')
        g.append(title_bar(-8, -10))
        g.append(f'<path d="M-7 6 l4 4 l8 -9" stroke="{INK}" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    g.append('</g>')
    return "".join(s) + "".join(g)


# ---------- experiential vs expert prior glyphs (source + stacking) ----------
# Experiential reads as a PAST TASK: same shape as the task/exam paper, but filled
# in and graded (a check). Expert reads as a book. A stack = multiple rollouts /
# multiple expert sessions, which is what the internalized prior can hold.
def graded_sheet(cx=0, cy=0, sc=1.0):
    return (f'<g transform="translate({cx},{cy}) scale({sc})">'
            f'<rect x="-13" y="-17" width="26" height="34" rx="1.5" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
            + sheet_head(-8, -13, 16)
            + f'<line x1="-8" y1="-3" x2="8" y2="-3" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
            + f'<line x1="-8" y1="1" x2="3" y2="1" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
            + f'<path d="M-7 8 l3.5 4 l7.5 -9" stroke="{INK}" stroke-width="2.3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            + '</g>')

def book_glyph(cx=0, cy=0, sc=1.0):
    return (f'<g transform="translate({cx},{cy}) scale({sc})">'
            f'<rect x="-13" y="-17" width="26" height="34" rx="1.5" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
            f'<rect x="-13" y="-17" width="6" height="34" fill="{CREAM}" stroke="{INK}" stroke-width="2"/>'
            f'<rect x="-3" y="-11" width="14" height="4" fill="{INK}"/>'
            f'<line x1="-3" y1="-1" x2="11" y2="-1" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
            f'<line x1="-3" y1="4" x2="7" y2="4" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
            + '</g>')

def prior_stack(kind, n=3, cx=0, cy=0):
    unit = graded_sheet if kind == "experiential" else book_glyph
    return "".join(unit(cx + i*7, cy - i*7, 1.0) for i in range(n-1, -1, -1))  # back-to-front

# ---------- aggregate composite (the amalgam) ----------
def _quad(cx, cy, w, h, pf):
    tw = w * (1 - pf)
    return (f"{cx-tw/2:.1f},{cy-h/2:.1f} {cx+tw/2:.1f},{cy-h/2:.1f} "
            f"{cx+w/2:.1f},{cy+h/2:.1f} {cx-w/2:.1f},{cy+h/2:.1f}")

def _label(tx, ty, x2, y2, text, anchor="start", em=False):
    dot = f'<circle cx="{x2}" cy="{y2}" r="2.4" fill="{INK}"/>'
    ln = f'<path d="M{tx} {ty} L{x2} {y2}" stroke="{GD}" stroke-width="1" fill="none" opacity=".8"/>'
    wt = "700" if em else "500"; fill = INK if em else GD
    tsp = "".join(f'<tspan x="{tx}" dy="{0 if i==0 else 12}">{l}</tspan>' for i, l in enumerate(text.split("\n")))
    return ln + dot + (f'<text x="{tx}" y="{ty}" text-anchor="{anchor}" font-family="ui-monospace,Menlo,monospace" '
                       f'font-size="10.5" font-weight="{wt}" fill="{fill}">{tsp}</text>')

