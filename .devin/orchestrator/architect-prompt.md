You are a Principal Software Architect orchestrating a safe, zero-regression refactoring of a Python/JS repository for AI coding agents. Execute these 3 phases in sequence without conversational filler:

### PHASE 1: PRE-FILTER (already executed — output committed at `.devin/orchestrator/phase1-prefilter.txt`)
The two commands were run in the project root to map the directory structure and extract files >150 lines with their signatures (including class methods).

### PHASE 2: SAFETY-GATED, SUB-AGENT REFACTORING PLAN
Using ONLY Phase 1 data, design a dependency-ordered refactoring plan so every source file is ≤250 lines and colocated by feature domain (`<feature>/router.py`, `service.py`, `repository.py`, `schemas.py` for Python; `<feature>/<Component>.jsx`, `use<Feature>.js`, `<feature>Api.js` for JS).

Follow these architectural rules:
1. **Stage 0 (Safety Baseline):** Add structured logging (`L`), write baseline characterization tests (`T`) for every target file, and configure max-line (250) + complexity (≤10) linter rules as **warnings** (`C`) before moving code.
2. **Stage 1 (Leaf Extraction):** Extract pure schemas, types, constants, and API clients (`X`).
3. **Stage 2 (Core Split):** Split monolithic routes, services, and UI components (`S`, `M`, `D`).
4. **Stage 3 (Final Diagnostics):** Promote max-line linter rules to **errors** (`C`), then run full test suite, dead/circular-import audit, and smoke tests (`V`).
5. **Zero File Contention:** Never assign two parallel `LANE` values in the same `STAGE` if they edit the same `SRC` file.

### PHASE 3: ULTRA-COMPACT OUTPUT
Output ONLY raw pipe-delimited rows (zero prose, zero headers, zero markdown fences):
`ID|STAGE|LANE|ACT|SRC|DST|SYMBOLS|DEPS|NOTE`
- `STAGE`: `0`=SafetyBaseline, `1`=LeafExtract, `2`=CoreSplit, `3`=Diagnostics
- `LANE`: Parallel worker group (e.g., `CORE`, `AUTH`, `BILLING`, `UI`)
- `ACT`: `C`=Config/Linter, `T`=WriteTests, `L`=AddLogging, `X`=Extract, `S`=Split, `M`=Move, `D`=Delete, `V`=VerifyDiagnostics
- `SRC`: Source path (`-` if new)
- `DST`: Comma-separated target path(s)
- `SYMBOLS`: Comma-separated functions/classes/components (`*` for whole file)
- `DEPS`: Comma-separated prerequisite IDs (`-` if none)
- `NOTE`: Max 8 words, telegraphic style, zero articles (a/an/the)

Write the output rows to `.refactor/plan.psv` — the Orchestrator Agent's INPUT MANIFEST reads that path.
