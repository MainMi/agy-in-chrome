# Capstone page assembly + output for build_capstone.py —
# pure refactor, behavior unchanged.

from capstone_data import *
from capstone_page_a import PAGE_A
from capstone_page_b import PAGE_B
from capstone_page_c import PAGE_C
from capstone_page_d import PAGE_D
from capstone_page_e import PAGE_E

page = PAGE_A + PAGE_B + PAGE_C + PAGE_D + PAGE_E

import re as _re
# anchor every section, then build a fixed sidebar: section nav + per-leg colour key
page = _re.sub(r'<h2>(\d+) &middot;', r'<h2 id="sec\1">\1 &middot;', page)
_secs = _re.findall(r'<h2 id="sec(\d+)">\d+ &middot; ([^<]+)</h2>', page)
_nav = "".join(f'<a class="navlink" href="#sec{n}"><span class="n">{n}</span>{t}</a>' for n, t in _secs)
def _legdesc(a):
    lab, sh = a["label"], a["short"]
    return lab[len(sh)+3:] if lab.startswith(sh + " · ") else lab
_legrows = "".join(
    f'<div class="legrow"><span class="sw" style="background:{a["color"]}"></span>'
    f'<b>{HH.escape(a["short"])}</b><span>{HH.escape(_legdesc(a))}</span></div>'
    for a in ARMS)
_sidebar = ('<nav class="sidebar"><div class="brand">OCIC capstone</div>'
            '<div class="brandsub">continual-learning ablations</div>'
            f'<h4>Sections</h4>{_nav}'
            f'<h4>Legs &middot; colour key</h4>{_legrows}</nav>'
            '<div class="navtoggle" title="show / hide sidebar">&#9776;</div>')
page = page.replace("<body>", "<body>" + _sidebar, 1)

out = os.path.join(BENCH, "benchmark_capstone.html")
open(out, "w").write(page)
print("wrote", out, f"({os.path.getsize(out)/1024:.0f} KB)")
