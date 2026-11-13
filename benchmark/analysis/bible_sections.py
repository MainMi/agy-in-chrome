# HTML section builders for build_style_bible.py — pure refactor.

from bible_glyphs import *
from bible_scene import *

CSS = """
:root{--bg:#f4f1ea;--ink:#2b2a27;--muted:#6b675e;--dim:#948f84;--line:#d8d3c7;--card:#fffdf6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:44px 30px 100px}
h1{font-size:28px;letter-spacing:-.01em;margin:2px 0 6px}
h2{font-size:19px;margin:48px 0 4px;padding-bottom:7px;border-bottom:1px solid var(--line)}
h3{font-size:14px;margin:20px 0 8px;font-weight:700}
.eyebrow{font:600 11px/1 ui-monospace,Menlo,monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--dim)}
.lede{font-size:16px;color:var(--muted);max-width:74ch}
p{margin:8px 0;max-width:74ch}
.zones{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:16px 0}
.zone{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:11px 13px}
.zone b{font-size:13px}.zone span{font-size:12.5px;color:var(--muted)}
.renders{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:16px 0 4px}
.render{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.render img{display:block;width:100%;height:auto;background:#fdfbf5}
.render figcaption{display:flex;justify-content:space-between;align-items:baseline;padding:8px 11px;
  font:600 12px ui-monospace,Menlo,monospace;border-top:1px solid var(--line)}
.render figcaption span{font-weight:400;color:var(--muted)}
@media(max-width:680px){.renders{grid-template-columns:1fr}}
.matrix{display:grid;grid-template-columns:minmax(120px,0.7fr) 1fr 1fr 1fr;gap:10px;align-items:center;margin:16px 0 4px}
.mx-corner{}
.mx-head{font:600 12px ui-monospace,Menlo,monospace;color:var(--muted);text-align:center;padding-bottom:2px}
.mx-row{padding-right:6px}
.mx-row b{display:block;font-size:13px}.mx-row span{font-size:11.5px;color:var(--muted)}
.mx-cell{background:var(--card);border:1px solid var(--line);border-radius:9px;overflow:hidden;line-height:0}
.mx-cell img{width:100%;height:auto;display:block;background:#fdfbf5}
@media(max-width:680px){.matrix{grid-template-columns:1fr 1fr}.mx-corner,.mx-head{display:none}.mx-row{grid-column:1/-1}}
.hero{margin:16px 0 4px;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;max-width:560px}
.hero img{width:100%;height:auto;display:block;background:#fdfbf5}
.hero figcaption{padding:10px 13px;border-top:1px solid var(--line)}
.hero figcaption b{display:block;font:600 13px ui-monospace,Menlo,monospace}
.hero figcaption span{font-size:11.5px;color:var(--muted)}
.props{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin:16px 0 4px}
.prop{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.prop img{width:100%;height:auto;display:block;background:#fdfbf5}
.prop figcaption{padding:9px 12px;border-top:1px solid var(--line)}
.prop figcaption b{display:block;font:600 13px ui-monospace,Menlo,monospace}
.prop figcaption span{font-size:11.5px;color:var(--muted)}
.phaseband{font:600 11px/1 ui-monospace,Menlo,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);margin:22px 0 8px}
.hq{font:600 9px/1 ui-monospace,Menlo,monospace;letter-spacing:.06em;color:#fff;background:var(--ink);border-radius:3px;padding:2px 4px;vertical-align:middle;margin-left:4px}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}
.gcell{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.gcell img{width:100%;height:auto;display:block;background:#fdfbf5}
.gcell figcaption{padding:8px 11px;border-top:1px solid var(--line)}
.gcell figcaption b{display:block;font:600 12.5px ui-monospace,Menlo,monospace}
.gcell figcaption span{font-size:11.5px;color:var(--muted)}
.levels{display:flex;flex-wrap:wrap;gap:14px;margin:6px 0 4px}
.lv{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:8px;text-align:center;width:132px}
.lv svg{display:block;margin:0 auto}
.lv .cap{font:600 11.5px ui-monospace,Menlo,monospace;margin-top:5px}
.lv .sub{font-size:11px;color:var(--muted);line-height:1.3;margin-top:2px}
.note{font-size:12.5px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin:14px 0}
.cell{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:8px 8px 12px}
.cell svg{display:block}
.cell .t{font:700 12px ui-monospace,Menlo,monospace;margin-top:4px}
.cell .p{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.05em}
.phaseband{font:700 11px ui-monospace,Menlo,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--dim);grid-column:1/-1;margin:10px 0 -4px}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin:10px 0}
th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line)}
th{font:600 10.5px ui-monospace,Menlo,monospace;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:11.5px}
"""

def lv(inner, cap, sub):
    return f'<div class="lv">{swatch(inner)}<div class="cap">{cap}</div><div class="sub">{sub}</div></div>'

# variable level swatches
faces_html = "".join(lv(face(60, 66, *TIRED[k]),
                        {"fresh":"FRESH","lightly":"LIGHTLY","baggy":"BAGGY","wrecked":"WRECKED"}[k],
                        {"fresh":"~58k · neat, no shadow","lightly":"~99k · one cowlick",
                         "baggy":"~270k · cowlick + faint shadow","wrecked":"~488k · full mess + shadow"}[k])
                     for k in ("fresh","lightly","baggy","wrecked"))
harness_html = (lv(torso(60,50)+face(60,44,"neat","none",crest="ocic"),"OCIC","open-source spark on the brow")
              + lv(torso(60,50)+face(60,44,"neat","none",crest="official"),"OFFICIAL","filled shield on the brow"))
browser_html = (lv('<g transform="translate(-40,-96)">'+desk("brave",120)+'</g>',"BRAVE","lion emblem on desk")
              + lv('<g transform="translate(-40,-96)">'+desk("chrome",120)+'</g>',"CHROME","pinwheel emblem"))
def mini_prop(fn): return f'<g transform="translate(-120,-96)">{fn}</g>'
knowledge_html = (
    lv('', "NONE", "empty desk (cold)")
  + lv(mini_prop(binder("expert")), "RAW MOUNT", "closed binder on the desk")
  + lv(mini_prop(binder("expert", sheet=True)), "ANALYSIS", "clean sheet on the binder (must reach)")
  + lv(f'<g transform="translate(-56,-104)">{exam(recipe=1,distilled=True)}</g>', "RECIPE", "same sheet, clipped to the EXAM (in hand)"))
source_html = (
    lv(graded_sheet(60, 60, 1.45), "EXPERIENTIAL", "a graded, filled-in task sheet (a past rollout)")
  + lv(book_glyph(60, 60, 1.45), "EXPERT", "a textbook (an expert session)")
  + lv(f'<g transform="translate(-56,-104)">{exam(recipe=1,distilled=True)}</g>', "DISTILLED", "crisp recipe, funnel mark (fused)"))
prior_depth_html = (
    lv(graded_sheet(60, 60, 1.3), "ONE ROLLOUT", "a single graded task sheet")
  + lv(prior_stack("experiential", 3, 53, 67), "MANY ROLLOUTS", "a stack of graded task sheets")
  + lv(book_glyph(60, 60, 1.3), "ONE EXPERT SESSION", "a single textbook")
  + lv(prior_stack("expert", 3, 53, 67), "MANY EXPERT SESSIONS", "a stack of books"))
bubble_html = (
    lv(f'<g transform="translate(-116,4)">{bubble("own","big")}</g>', "OWN · big", "read its own notebooks (4A)")
  + lv(f'<g transform="translate(-116,4)">{bubble("expert","big")}</g>', "EXPERT · big", "read the textbooks (4B)")
  + lv(f'<g transform="translate(-116,10)">{bubble("warmup","small")}</g>', "WARM-UP · small", "did one practice task (5C/5D)"))
recipe_html = (
    lv(f'<g transform="translate(-56,-104)">{exam(recipe=1,distilled=True)}</g>', "SINGLE", "one combined sheet, both sites (5B)")
  + lv(f'<g transform="translate(-56,-104)">{exam(recipe=2,distilled=True)}</g>', "PER-SITE", "one sheet per site (5A)"))

# first AI renders: the aggregate prompt, same prompt, quality sweep (gpt-image-2, 1024)
RENDERS = [("low", "~$0.006", "22s"), ("medium", "~$0.05", "55s"), ("high", "~$0.21", "140s")]
render_html = "".join(
    f'<figure class="render"><img src="{img_src(f"img/aggregate_{q}.png")}" alt="aggregate render, {q} quality"/>'
    f'<figcaption><b>{q.upper()}</b><span>{cost} · {t}</span></figcaption></figure>'
    for q, cost, t in RENDERS)

# style exploration matrix: 2 aggregates (rows) x 3 art styles (cols)
MX_STYLES = [("pencil", "Pencil stickman"), ("flat", "Flat vector"), ("ink", "Fine ink")]
MX_ROWS = [("a", "A · OCIC · Brave · expert", "book on desk + in mind, fresh"),
           ("b", "B · CinC · Chrome · experiential", "completed practice exams, tired")]
def matrix_html():
    cells = ['<div class="mx-corner"></div>']
    cells += [f'<div class="mx-head">{name}</div>' for _, name in MX_STYLES]
    for cfg, rlab, rsub in MX_ROWS:
        cells.append(f'<div class="mx-row"><b>{rlab}</b><span>{rsub}</span></div>')
        for sk, _ in MX_STYLES:
            uri = img_src(f"img/style_{sk}_{cfg}.png")
            cells.append(f'<div class="mx-cell"><img src="{uri}" alt="{sk} {cfg}"/></div>')
    return '<div class="matrix">' + "".join(cells) + '</div>'

# pencil sub-variants (same scene, config B) for the final style pick
PVARIANTS = [("clean", "Clean", "thin outline, no shading"),
             ("loose", "Loose", "gestural sketchbook"),
             ("soft", "Soft", "smooth graphite shading")]
def pvariants_html():
    return '<div class="renders">' + "".join(
        f'<figure class="render"><img src="{img_src(f"img/pv_{k}_b.png")}" alt="pencil {k}"/>'
        f'<figcaption><b>{name}</b><span>{sub}</span></figcaption></figure>'
        for k, name, sub in PVARIANTS) + '</div>'

# per-arm soft-pencil renders, grouped by phase (one image per leg)
# sub = props on the scene · context load going into the task (drives the tiredness)
ARM_GALLERY = [
    ("Cold baselines", [
        ("1a-brave", "OCIC · Brave", "bare desk · fresh (no prior context)"),
        ("1a-chrome", "OCIC · Chrome", "bare desk · fresh (no prior context)"),
        ("1b-cinc", "CinC · Chrome", "bare desk · fresh (no prior context)")]),
    ("Phase 2 · raw mount", [
        ("2a", "2A experiential", "stack of graded sheets on desk · fresh (knowledge on disk, not in context)"),
        ("2b", "2B expert", "stack of books on desk · fresh (knowledge on disk, not in context)")]),
    ("Phase 3 · analysis mount", [
        ("3d", "3D experiential", "stack + analysis sheet · fresh (knowledge on disk, not in context)"),
        ("3c", "3C expert", "books + analysis sheet · fresh (knowledge on disk, not in context)")]),
    ("Phase 4 · fork", [
        ("4a", "4A experiential fork", "stack in mind · wrecked (~499k tokens in, 476k-534k)"),
        ("4b", "4B expert fork", "stack of books in mind · baggy (~288k tokens in, 251k-325k)")]),
    ("Phase 5 · recipe & warm-up", [
        ("5a", "5A recipe per-site", "two panels on the task · fresh (small recipe in prompt)"),
        ("5b", "5B recipe single", "one panel on the task · fresh (small recipe in prompt)"),
        ("5c", "5C atomic warm-up", "one sheet in mind · lightly (~99k tokens in)"),
        ("5d", "5D warm-up + recipe", "panel on task + sheet in mind · lightly (~99k tokens in)")]),
]
def leg_best(key):
    """Best available render for a leg: medium is the working standard, then high, then low.
    Returns (src, quality_tag)."""
    for q, tag in (("medium", "MQ"), ("high", "HQ"), ("low", "")):
        s = img_src(f"img/leg_{key}_{q}.png")
        if s:
            return s, tag
    return "", ""

def gallery_html():
    out = []
    for band, arms in ARM_GALLERY:
        out.append(f'<div class="phaseband">{band}</div><div class="gallery">')
        for key, name, sub in arms:
            src, tag = leg_best(key)
            badge = f' <span class="hq">{tag}</span>' if tag else ''
            out.append(f'<figure class="gcell"><img src="{src}" alt="{name}"/>'
                       f'<figcaption><b>{name}{badge}</b><span>{sub}</span></figcaption></figure>')
        out.append('</div>')
    return "".join(out)

# prop sheets: one grid image per variable, drawn in a single pass for continuity
PROP_SHEETS = [
    ("v1-character", "V1 · The character (context load × harness)",
     "columns L→R: fresh · lightly · baggy · wrecked. rows: OCIC (top) · CinC (bottom)"),
    ("v2-position", "V2 · Knowledge form (how it reaches the task)",
     "the four delivery forms. NONE: nothing supplied (cold, bare desk). RAW: a graded source dropped on the desk, there but you must reach for it. ANALYSIS: a distinct structured, formatted write-up laid over the source, small and offset so the source underneath stays visible. RECIPE: knowledge printed straight onto the task paper, in hand and unavoidable."),
    ("task-paper", "The task paper",
     "L→R: plain task (legible TASK heading + illegible brief + answer lines) · recipe printed on top · recipe split into two sections. Only the heading is legible."),
    ("v3-source", "V3 · Source (whose material, single or stacked)",
     "top: one experiential (own graded task sheet) · one expert (textbook). bottom: a stack of each (multiple rollouts / expert sessions), which is what the internalized prior holds."),
    ("v4-prior", "V4 · Internalized prior (the bubble)",
     "a thought-bubble container; it holds any source prop, a single sheet or a stack (rollouts / books). shown holding one graded task paper."),
    ("v6-browser", "V6 · Browser (embedded on the desk)",
     "the desk with the browser logo embedded on its front face. left: Brave · right: Chrome."),
]
def props_html():
    return '<div class="props">' + "".join(
        f'<figure class="prop"><img src="{img_src(f"img/prop_{k}_labeled.png")}" alt="{title}"/>'
        f'<figcaption><b>{title}</b><span>{legend}</span></figcaption></figure>'
        for k, title, legend in PROP_SHEETS) + '</div>'

# composition exploration: how to show face + desk together (first-person feel)
COMPS = [
    ("across", "Across the desk", "baseline; face over the far edge, desk head-on"),
    ("corner", "Three-quarter corner", "seated at the corner; face + angled desk, most natural single scene"),
    ("leaning", "Leaning over", "bent over the far edge; reads a little awkward"),
    ("reflection", "Reflection", "true first-person over-the-shoulder; face in a propped mirror"),
    ("inset", "Corner inset", "pure first-person desk; face as a cameo medallion"),
]
def comps_html():
    return '<div class="gallery">' + "".join(
        f'<figure class="gcell"><img src="{img_src(f"img/comp_{k}.png")}" alt="{name}"/>'
        f'<figcaption><b>{name}</b><span>{sub}</span></figcaption></figure>'
        for k, name, sub in COMPS) + '</div>'

# first-person variants: desk in true first-person, face surfaced by a desk object
FP_COMPS = [
    ("mirror", "Mirror", "propped desk mirror; warm and natural"),
    ("monitor", "Monitor self-view", "face on a screen, on-theme with the browser world"),
    ("phone", "Phone selfie", "propped phone, front-camera self-view"),
    ("photo", "Framed photo", "a desk portrait; understated"),
    ("badge", "ID badge", "lanyard badge photo; ties to identity"),
    ("cameo", "Cameo overlay", "graphic medallion; least in-world"),
]
def fp_html():
    return '<div class="gallery">' + "".join(
        f'<figure class="gcell"><img src="{img_src(f"img/fp_{k}.png")}" alt="{name}"/>'
        f'<figcaption><b>{name}</b><span>{sub}</span></figcaption></figure>'
        for k, name, sub in FP_COMPS) + '</div>'

# arm -> channel table
def cell_summary(cfg):
    b = cfg.get("bubble"); return {
      "harness":cfg["harness"],"browser":cfg["browser"],
      "knowledge":("recipe" if cfg.get("recipe") else cfg.get("prop","none")),
      "source":cfg.get("source", "distilled" if cfg.get("recipe") else ("-" if not b else b[0])),
      "tired":cfg["tired"],"bubble":(f"{b[0]}/{b[1]}" if b else "-")}
rows = "".join(
  f'<tr><td class="mono">{s}</td><td>{c["harness"]}</td><td>{c["browser"]}</td><td>{c["knowledge"]}</td>'
  f'<td>{c["source"]}</td><td>{c["tired"]}</td><td>{c["bubble"]}</td></tr>'
  for (_,s,_,cfg) in ARMS for c in [cell_summary(cfg)])

