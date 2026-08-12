# AM-070-1 Execution Results

Executed against the live Project files (`/mnt/project`) as of this session. The core specification, `OpenCDC-Specification.md`, was **not modified** — confirmed byte-identical before and after execution. `OpenCDC-UserStories.md` and `CONTRIBUTING.md` / `GOVERNANCE.md` required no changes under this manifest and are not included here.

## Gate results (all against the real files, not a simulation)

| Gate | Result |
|---|---|
| P0 Preflight (spec v0.7.0, 4 binding-defined labels, 0 trailing-ws defects, register at 98/41) | PASS |
| G-1 (register → 95 requirements / 37 matrix rows) | PASS |
| G-2 (§17 / §19.1 drift-free against unmodified spec; register↔body audit 95/95, 0, 0) | PASS |
| G-3 (all 7 schemas parse) | PASS |
| G-4 (9/9 payload examples validate under closed-world schemas) | PASS |
| G-5 (ADR index 35 entries, 2 supersessions, TOC current) | PASS |
| G-6 (Glossary 52 terms, 0 dangling §2.2b refs, 0 stale wire-version claims) | PASS |
| **FG-1 — `bash check.sh`** | **6 passed, 0 failed** |
| FG-2 content assertions | all pass |
| FG-3 — spec byte-identity | **unchanged, confirmed** |

## Files in this archive (20)

**Registry**
- `requirements.yaml` — 98→95 requirements, 41→37 matrix rows (ops R-1..R-9)
- `versions.yaml` — date corrections (V-1)

**Tools**
- `audit_register.py` — Change Log position-independence fix + binding-defined allowlist (T-2, T-3)
- `generate_matrix.py` — header column fix (T-1)
- `validate_examples.py` — TRX_COMMIT schema mapping (T-6)
- `check_versions.py` — **new** version-manifest gate (T-5)
- `check.sh` — CRLF→LF, version-manifest check wired in (T-4)

**Schemas** (all now closed-world / `additionalProperties: false`, wire 0.3 pinned)
- `opencdc-envelope_schema.json` — `cdcschemauri`, `cdcsourceid`, TRX_COMMIT envelope rule (S-1)
- `opencdc-stream-metadata_schema.json` — full rebuild, all capability axes (S-2)
- `opencdc-ddl_schema.json` — mode-aware `ddl` shape (S-3)
- `opencdc-dml_schema.json` — `$id` collision resolved (S-4)
- `opencdc-heartbeat_schema.json`, `opencdc-object-metadata_schema.json` — closed-world (S-5)
- `opencdc-trx-commit_schema.json` — **new** (S-6)

**Examples**
- `OpenCDC-PayloadExamples.md` — wire 0.2→0.3, `opencdc_version` field corrected, stray `op` field removed, new Example 9 (TRX_COMMIT), TOC regenerated (E-1..E-6)

**Companion docs**
- `OpenCDC-ArchitectureDecisionRecord.md` — v0.1→v0.2, ADR-0026/0033 superseded, new ADR-0034/0035, index extended to 35, TOC regenerated (A-1..A-6)
- `GLOSSARY.md` — 7 corrections, 11 new v0.7.0 terms, 52 total (G-1..G-8)
- `OpenCDC-TypeSystem.md` — CDC-OIS→OpenCDC attribution, wire 1.0→0.3, "Confidential Draft"→"Draft for Discussion" (TS-1..TS-8)

**Top level**
- `README.md` — Document Family table realigned to v0.7.0 (RM-1..RM-8)
- `CHANGELOG.md` — new `[0.7.0]` entry, wire version line (C-1)

## Decisions on record (per manifest §"Decisions embedded")

- **D-1:** `P-TRX-7` register level retained as `MUST` (render flag only — §19.1's own row and the requirement text both correctly say SHOULD). Residual anomaly logged as **W-11** for the next spec-touching revision.
- **D-2:** ADR-0034/0035 shipped as `Accepted`, reflecting the ratification already recorded in the spec's own changelog and this session.
- **D-3:** `versions.yaml` specification date set to `2026-07` to match the spec header, since the spec itself was not editable this pass.

## Not resolved by this pass (flagged, not silently dropped)

- F-2: no binding work-item tracker exists yet for the R-POS-7 / P-RET-1 chartered-but-unenforced gap ADR-0034 references.
- F-4: spec-internal items (2 residual consumer MUSTs, `ddl_capture` omission from §10.4's field list, the unexecuted §4.5.3 instruction, stale Appendix A title references, "ADR v0.1" in Normative References) remain — out of scope under the no-spec-edits constraint.

## To apply

Copy each file over its counterpart in the repository (flat layout matches this Project's structure), then from the repo root:

```bash
bash check.sh
```

Expect `Results: 6 passed, 0 failed`.
