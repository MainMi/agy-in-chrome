# Scene composition + arm table for build_style_bible.py — pure refactor.

from bible_glyphs import *
from bible_glyphs import _quad, _label

def composite_scene():
    W, H = 1000, 660
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px">', '<g transform="translate(120,0)">']
    # thought bubble: BOTH kinds of prior side by side
    bx, by = 452, 118
    for dx, dy, r in [(-54, 68, 4), (-46, 78, 3), (-40, 86, 2.2)]:
        s.append(f'<circle cx="{bx+dx}" cy="{by+dy}" r="{r}" fill="{PAPER}" stroke="{INK}" stroke-width="1.6"/>')
    s.append(f'<ellipse cx="{bx}" cy="{by}" rx="78" ry="54" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
    # LEFT: material it READ (book + scrappy notebook)
    s.append(f'<g transform="translate({bx-30},{by-2})">'
             f'<rect x="-6" y="-20" width="30" height="38" rx="2" fill="{CREAM}" stroke="{INK}" stroke-width="2"/>'
             f'<rect x="-6" y="-20" width="7" height="38" fill="{DESKC}" stroke="{INK}" stroke-width="2"/>'
             f'<rect x="5" y="-13" width="15" height="4.5" fill="{INK}"/></g>')
    s.append(f'<g transform="translate({bx-48},{by-4}) rotate(-8)">'
             f'<rect x="0" y="0" width="26" height="36" rx="2" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
             + "".join(f'<circle cx="0" cy="{7+k*7}" r="1.6" fill="none" stroke="{INK}" stroke-width="1.3"/>' for k in range(4))
             + f'<path d="M6 11 q5 -3 9 0 t9 0 M6 18 q5 -3 9 0 t9 0 M6 25 q5 -3 9 0" stroke="{INK}" stroke-width="1.2" fill="none" opacity=".6"/></g>')
    # RIGHT: a practice task it DID (completed exam with a check)
    s.append(f'<g transform="translate({bx+30},{by-2})">'
             f'<rect x="-14" y="-19" width="30" height="38" rx="2" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
             f'<rect x="-9" y="-13" width="16" height="4" fill="{INK}"/>'
             f'<line x1="-9" y1="-4" x2="9" y2="-4" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
             f'<line x1="-9" y1="1" x2="4" y2="1" stroke="{INK}" stroke-width="1.1" opacity=".5"/>'
             f'<path d="M-7 9 l4 4 l9 -10" stroke="{INK}" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>')
    # torso (the harness logo now sits on the brow, not the chest)
    s.append(f'<path d="M230 300 Q285 235 340 300 L360 320 L210 320 Z" fill="{PAPER}" stroke="{INK}" stroke-width="2.6"/>')
    # head + face (cost)
    hx, hy = 285, 210
    s.append(f'<circle cx="{hx}" cy="{hy}" r="50" fill="{PAPER}" stroke="{INK}" stroke-width="2.8"/>')
    s.append(f'<path d="M{hx-50} {hy-8} Q{hx} {hy-70} {hx+50} {hy-8} Q{hx+24} {hy-42} {hx} {hy-42} Q{hx-24} {hy-42} {hx-50} {hy-8} Z" fill="{HAIR}"/>')
    s.append(f'<path d="M{hx+6} {hy-52} Q{hx+14} {hy-78} {hx+24} {hy-58} Q{hx+15} {hy-58} {hx+9} {hy-48} Z" fill="{HAIR}"/>')
    # harness crest stamped on the forehead (Rick-and-Morty brow mark)
    s.append(crest_glyph(hx, hy-16, "ocic", sw=2, sc=1.9))
    s.append(f'<circle cx="{hx-16}" cy="{hy+2}" r="3" fill="{INK}"/><circle cx="{hx+16}" cy="{hy+2}" r="3" fill="{INK}"/>')
    s.append(f'<path d="M{hx-24} {hy+13} Q{hx-16} {hy+18} {hx-8} {hy+13}" stroke="{G_FAINT}" stroke-width="2.4" fill="none" stroke-linecap="round"/>')
    s.append(f'<path d="M{hx+8} {hy+13} Q{hx+16} {hy+18} {hx+24} {hy+13}" stroke="{G_FAINT}" stroke-width="2.4" fill="none" stroke-linecap="round"/>')
    s.append(f'<line x1="{hx-10}" y1="{hy+27}" x2="{hx+10}" y2="{hy+27}" stroke="{INK}" stroke-width="2.2" stroke-linecap="round"/>')
    # desk (perspective)
    s.append(f'<polygon points="150,300 470,300 560,548 60,548" fill="{DESKC}" stroke="{INK}" stroke-width="2.8"/>')
    s.append(f'<polygon points="60,548 560,548 560,592 60,592" fill="{CREAM}" stroke="{INK}" stroke-width="2.6"/>')
    ex, ey = 310, 570
    s.append(f'<path d="M{ex} {ey-11} Q{ex+11} {ey-6} {ex+8} {ey+6} Q{ex} {ey+11} {ex-8} {ey+6} Q{ex-11} {ey-6} {ex} {ey-11} Z" fill="none" stroke="{INK}" stroke-width="1.8"/>'
             f'<path d="M{ex-5} {ey-9} L{ex-8} {ey-14} M{ex+5} {ey-9} L{ex+8} {ey-14}" stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>')
    # exam (task) — content turned to face the student (heading/lines read toward the back)
    s.append(f'<polygon points="{_quad(232,452,168,128,.16)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
    s.append(f'<g transform="rotate(180 232 452)">')
    for i in range(3):
        yy = 432 + i*12
        s.append(f'<line x1="164" y1="{yy}" x2="296" y2="{yy}" stroke="{INK}" stroke-width="1.1" opacity=".45"/>')
    s.append('</g>')
    # recipe clipped to exam — turned to face the student
    s.append(f'<polygon points="{_quad(232,398,132,66,.13)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.4"/>')
    s.append(f'<g transform="rotate(180 232 398)">')
    s.append(f'<rect x="222" y="360" width="8" height="12" rx="3" fill="none" stroke="{INK}" stroke-width="2"/>')
    s.append(f'<rect x="180" y="382" width="48" height="5" fill="{INK}"/>')
    s.append(f'<line x1="180" y1="405" x2="284" y2="405" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
    s.append(f'<line x1="180" y1="412" x2="264" y2="412" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
    s.append(f'<path d="M280 372 L292 372 L288 378 L288 384 L284 384 L284 378 Z" fill="{PAPER}" stroke="{INK}" stroke-width="1.5"/>')
    s.append('</g>')
    # binder (raw) + analysis sheet — analysis sheet turned to face the student
    s.append(f'<polygon points="{_quad(430,470,130,92,.12)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.6"/>')
    s.append(f'<polygon points="{_quad(378,470,26,92,.12)}" fill="{DESKC}" stroke="{INK}" stroke-width="2.4"/>')
    for k in range(4):
        s.append(f'<circle cx="376" cy="{444+k*16}" r="2" fill="none" stroke="{INK}" stroke-width="1.4"/>')
    s.append(f'<path d="M398 462 q10 -4 20 0 t20 0" stroke="{INK}" stroke-width="1.3" fill="none" opacity=".55"/>')
    s.append(f'<polygon points="{_quad(432,418,110,50,.1)}" fill="{PAPER}" stroke="{INK}" stroke-width="2.2"/>')
    s.append(f'<g transform="rotate(180 432 418)">')
    s.append(f'<rect x="392" y="404" width="40" height="4.5" fill="{INK}"/>')
    s.append(f'<line x1="392" y1="424" x2="470" y2="424" stroke="{INK}" stroke-width="1.1" opacity=".5"/>')
    s.append('</g>')
    # callouts
    s.append(_label(566, 40, 400, 70, "THOUGHT BUBBLE = prior in the head:", "start", em=True))
    s.append(_label(566, 96, 424, 118, "material it READ (fork)\n+  a practice task it DID (warm-up)", "start"))
    s.append(_label(40, 175, 258, 212, "FACE = tiredness\n= context load\nthe COST · emphasize", "start", em=True))
    s.append(_label(500, 200, 300, 194, "brow mark\n= harness (minor)", "start"))
    s.append(_label(496, 610, 320, 572, "desk brand\n= browser (minor)", "start"))
    s.append(_label(58, 470, 200, 452, "EXAM\n= the task", "end", em=True))
    s.append(_label(58, 405, 224, 398, "RECIPE\nclipped to the exam\n(in the task, forced)", "end", em=True))
    s.append(_label(586, 500, 452, 478, "BINDER\n= raw material\non the desk (optional)", "start", em=True))
    s.append(_label(586, 410, 456, 418, "ANALYSIS SHEET\nclean, on the binder", "start", em=True))
    s.append('</g></svg>')
    return "".join(s)

# ---------- full scene ----------
TIRED = {"fresh": ("neat", "none"), "lightly": ("cowlick", "none"),
         "baggy": ("cowlick", "faint"), "wrecked": ("mess", "dark")}

def scene(cfg, w=220, h=224):
    hair, ue = TIRED[cfg["tired"]]
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" font-family="inherit">']
    if cfg.get("bubble"):
        parts.append(bubble(*cfg["bubble"]))
    parts.append(torso(100, 92, cfg["harness"]))
    parts.append(face(100, 84, hair, ue, crest=cfg["harness"]))
    parts.append(desk(cfg["browser"], w))
    parts.append(exam(recipe=cfg.get("recipe", 0), distilled=cfg.get("distilled", False)))
    if cfg.get("prop") == "binder":
        parts.append(binder(cfg["source"]))
    elif cfg.get("prop") == "analysis":
        parts.append(binder(cfg["source"], sheet=True))
    parts.append('</svg>')
    return "".join(parts)

def swatch(inner, w=120, h=120):
    return f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="inherit">{inner}</svg>'

# ---------- the 13 arms ----------
ARMS = [
 ("Cold · OCIC · Brave","OCIC-Br","cold", dict(harness="ocic",browser="brave",tired="fresh")),
 ("Cold · OCIC · Chrome","OCIC-Ch","cold", dict(harness="ocic",browser="chrome",tired="fresh")),
 ("Cold · Official CinC · Chrome","CinC","cold", dict(harness="official",browser="chrome",tired="fresh")),
 ("2A · experiential raw mount","2A","p2", dict(harness="ocic",browser="brave",tired="fresh",prop="binder",source="own")),
 ("2B · expert raw mount","2B","p2", dict(harness="ocic",browser="brave",tired="fresh",prop="binder",source="expert")),
 ("3D · experiential analysis","3D","p3", dict(harness="ocic",browser="brave",tired="fresh",prop="analysis",source="own")),
 ("3C · expert analysis","3C","p3", dict(harness="ocic",browser="brave",tired="fresh",prop="analysis",source="expert")),
 ("4A · experiential fork","4A","p4", dict(harness="ocic",browser="brave",tired="wrecked",bubble=("own","big"))),
 ("4B · expert fork","4B","p4", dict(harness="ocic",browser="brave",tired="baggy",bubble=("expert","big"))),
 ("5A · recipe · per-site","5A","p5", dict(harness="ocic",browser="brave",tired="fresh",recipe=2,distilled=True)),
 ("5B · recipe · single","5B","p5", dict(harness="ocic",browser="brave",tired="fresh",recipe=1,distilled=True)),
 ("5C · atomic warm-up fork","5C","p5", dict(harness="ocic",browser="brave",tired="lightly",bubble=("warmup","small"))),
 ("5D · warm-up + recipe","5D","p5", dict(harness="ocic",browser="brave",tired="lightly",recipe=1,distilled=True,bubble=("warmup","small"))),
]

