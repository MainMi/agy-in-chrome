#!/usr/bin/env python3
"""benchmark_report.html v2: phases 1-4 post-fix, interactive, small-n-honest.

Statistical stance: n=12 paired tasks. Evidence is presented as (1) all raw
pairs shown, (2) paired effect sizes with 10k-resample bootstrap CIs,
(3) task-level win/loss/tie records, (4) replication across independent
comparisons, (5) mechanism decomposition. Exact permutation p-values are kept
as footnotes, not headlines.

Reproduce: harvest.py -> stats.py -> build_report_v2.py
"""
from report_v2_data import *
from report_v2_charts import *


import report_v2_page  # noqa: F401  (page assembly + write)
