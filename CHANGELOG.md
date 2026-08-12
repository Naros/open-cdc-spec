# OpenCDC Changelog

All notable changes to the OpenCDC specification family are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions listed in reverse chronological order.

**Two versioning tracks** (see [versions.yaml](registry/versions.yaml) and [GOVERNANCE.md](GOVERNANCE.md)):
- **Wire protocol version** — `cdcspecversion` carried in every event. Changes only when the on-wire contract changes. Currently `0.3`.
- **Document revision** — tracks editorial and structural changes. Patch (x.y.Z) = editorial; minor (x.Y.0) = structural additions.

---

## [0.7.0] — July 2026

**Capability-axis release.** Wire protocol **0.2 → 0.3**. Clean regeneration from the v0.6.9 baseline per the working-group Rebase Decision Manifest; supersedes the prior v0.7.0 PR draft. Full detail in the specification Change Log (relocated to the back of the document in this revision).

- `channel_model` removed; replaced by two mandatory guarantee axes: `ordering_scope` ("stream" | "channel") and `transaction_interleaving` ("none" | "possible"). New axes: `bidirectional`, `ddl_capture`, `transaction_visibility` (reserved, fail-closed).
- New normative **Terms and Definitions** section; §2.2a rebuilt as Capability Axes, Authority, and Legal Combinations with a Defaults-and-Silence rule (silence is never coverage).
- **TRX_COMMIT** (§10.5) defined normatively: mandatory under `transaction_interleaving: "possible"` (P-TRX-1); `event_count` counts distinct DML+DDL ordinals; new `meta.TRX_COMMIT` type; `dml.*`/`ddl.*` vocabularies declared closed.
- `dataschema` dual-format contradiction resolved: it always carries the OBJECT_METADATA id; new OPTIONAL `cdcschemauri` extension attribute for registry URIs, mandatory under `schema_by_reference` (P-SCHEMA-6).
- Loop suppression re-keyed to the **ingress counterpart** (P-LOOP-1, BD qualifier); `bidirectional` scoped pairwise.
- Ordering doctrine corrected to **source commit order**; emission-schema-change trigger for OBJECT_METADATA re-emission; incarnation rule for re-created subjects.
- **Attestation unwind (ADR-0034):** §2.2b removed; Delivery Layer conformance party withdrawn; C-COMP-1 demoted to SHOULD (Appendix A.1); R-POS-7 and P-RET-1 relabelled "Delivery-layer obligation (binding-defined)", deliberately unregistered, chartered in §12. Process guard adopted (ADR-0035): deferred options require a signed working-group row before promotion; registered-requirement removal likewise.
- Security restructure ratified: transport-security MUSTs (former S-TLS-1/S-AUTH-1) moved to deployment/binding scope; producer security rules (S-AUTH-2, S-AUTHZ-1/2) retained. P-ORD-6 partition alignment demoted to SHOULD/advisory.
- Appendix A rebuilt as a consumer parse pipeline (SHOULD-ceiling); Appendix B.4 Kafka consumption guidance added; conformance scenarios extended T-15..T-21b.
- Register: 95 requirements, 37 matrix rows; §17 and §19.1 regenerated. Companion updates: ADR v0.2 (ADR-0026..0035, two supersessions), Glossary v1.1, schemas hardened to closed-world at wire 0.3, new `opencdc-trx-commit` schema, examples extended to 9 events.

---

## [0.6.9] — June 2026

**Consumer scope correction.** No change to the wire contract, field semantics, or normative rules.

- Removed `C-HB-1` from the normative spec body. Monitoring HEARTBEAT for liveness is consumer operational guidance, not a producer-observable conformance obligation; mandating it as a body MUST violated the producer-focused scope established in ADR-0025.
- `C-HB-1` demoted to SHOULD-level and relocated to Appendix A.8 (HEARTBEAT lag monitoring), consistent with all other consumer-side `C-*` guidance.
- §19.1 matrix row updated: Consumer MUST → Consumer SHOULD, section 10.1 → Appendix A.8.
- §17 no longer lists `C-HB-1` (SHOULD-level entries are register-only).

---

## [0.6.8] — June 2026

**Requirements register and compliance matrix completion.** No change to the wire contract, field semantics, or normative rules.

- Assigned requirement IDs to four matrix rows that previously had none, anchored each in the spec body:
  - `C-TYPE-1` — `logical_type` is the authoritative basis for consumer decoding (§4.3)
  - `P-DML-1` — DML before/after payloads carry values only; type metadata MUST NOT appear per row (§4.1, §5)
  - `C-DML-1` — absent column in partial image MUST be interpreted as unchanged, not null (§5.4)
  - `C-HB-1` — consumer MUST monitor HEARTBEAT to distinguish idle stream from broken stream (§10.1)
- All 30 compliance matrix rows now carry at least one requirement ID.
- Register grows to 75 requirements (71 MUST-level rendering into §17, 4 SHOULD-level register-only).
- Added `spec/GLOSSARY.md` (31 terms, each with normative section references).
- Added `CONTRIBUTING.md` and `GOVERNANCE.md`.
- `versions.yaml` moved to `registry/`.

---

## [0.6.7] — June 2026

**§19.2 decoupled from User Story numbering.** No change to the wire contract, field semantics, or normative rules.

- Replaced `User Story: Story N` tags in all 14 conformance test scenarios with `Use Case: <capability tag>` (e.g., `Interoperability; Cross-vendor DML exchange`). Spec conformance section no longer breaks when the companion User Stories document is renumbered.
- Updated §19.2 intro to match.

---

## [0.6.6] — June 2026

**User Stories alignment pass.** No change to the wire contract, field semantics, or normative rules.

- Corrected three §19.2 story tags for the Fifth Draft renumbering: T-08 Story 5→6, T-09 Story 1,5→1,6, T-10 Story 3,4→3,5.
- Updated §19.2 intro to note that Acceptance Criteria were removed from User Stories (Fifth Draft) by working-group decision.
- `OpenCDC-UserStories.md`: repaired residual Word-export bold-split artifacts in table cells and inline text; no content changes.

---

## [0.6.5] — June 2026

**Normative clarifications to three envelope field definitions.** No change to the wire contract for conformant producers already following the spec's intent. 6/6 payload examples now fully conformant.

- `§3.1 id` — UUID v4 MUST for DML/DDL (load-bearing deduplication key); lifecycle events MUST carry a stream-unique, replay-stable id but MAY use a structured descriptive form.
- `§3.1 subject` — MUST for table-scoped events (DML, DDL, OBJECT_METADATA, snapshot); omitted for stream-scoped events (STREAM_METADATA, HEARTBEAT).
- `§3.3 cdcpos` — MUST for DML/DDL/HEARTBEAT and durable-stream OBJECT_METADATA; omitted for session-scoped re-emissions and STREAM_METADATA.
- `§9.1 DDL example` — added missing `cdctxorder: 0` (already MUST per §3.3; omission was an example error).
- Envelope JSON Schema (`opencdc-envelope.schema.json`) updated to match: UUID pattern and required fields now enforced conditionally by event type.

---

## [0.6.4] — June 2026

**Navigation and document conversion release.** No change to any normative content.

- Generated Tables of Contents added to all five family markdown documents (H1/H2 headings; fenced code blocks excluded). Regenerable via `tools/generate_toc.py`.
- `OpenCDC-UserStories.md` converted from a mislabeled `.docx` container (the file was UTF-8 markdown text) with Word-export run-split artifacts repaired.

---

## [0.6.3] — June 2026

**Conformance tooling release.** No change to the producer wire contract, field semantics, ordering guarantees, or type rules.

- §19.1 Compliance Matrix converted from bullet-list format to a generated Markdown table, sourced from `registry/requirements.yaml` matrix section. Rows now carry requirement IDs where assigned.
- Six companion JSON Schemas published (`schemas/opencdc-*.schema.json`) for the CloudEvents envelope, OBJECT_METADATA, DML/TRUNCATE, DDL, HEARTBEAT, and STREAM_METADATA payloads. Informative tooling artifacts; not normative references.
- PayloadExamples validation harness (`tools/validate_examples.py`) added.

---

## [0.6.2] — June 2026

**Requirements traceability release.** No change to the producer wire contract, field semantics, ordering guarantees, or type rules.

- Requirement IDs placed inline in body text for 24 requirements previously identified only in §17 (P-SCHEMA-1..5, C-SCHEMA-4, P-SEQ-1..6, C-SEQ-1..4, P-TRUNC-1..4, P-CONN-1, P-LOOP-1, P-IDEM-1, T-HEARTBEAT); no rule wording changed.
- §17 Normative Summary now generated from `registry/requirements.yaml`; gains eight previously missing MUST-level entries: P-ORD-7, R-POS-0, R-POS-3, R-POS-5, S-TLS-2, S-TLS-3, S-AUTH-2, C-TRUNC-4.
- P-TRUNC-2 section-field cleaned up (P-ORD-7 cross-reference moved to `see_also`).

---

## [0.6.1] — June 2026

**Patch release.** No change to the producer wire contract, field semantics, ordering guarantees, or type rules.

- Added Appendix A.9 (Operational Mode Selection Guidance, non-normative).
- Restored the `§4.4 Schema Delivery Modes` heading lost in the v0.6 refactor; all "Section 4.4" cross-references now resolve.
- Fixed §4.1 stream-ordering code block: cross-reference paragraph moved outside the fence; duplicated VIOLATION line removed.
- Updated User Stories references from v4 to Fifth Draft.
- Type System headline corrected to v0.2.

---

## [0.6.0] — June 2026

**Producer-focused refactor.** No change to the producer wire contract, field semantics, ordering guarantees, or type rules.

- Design-decision narrative extracted to the new companion Architecture Decision Record (ADR v0.1); former §2.9, §18, and Appendix A removed from the spec.
- Consumer behavior reframed as non-normative service-level guidance: former §7, §11.3, and §16 relocated to new Appendix A.
- Superficial vendor-tool mentions removed; vendor references retained only where source-engine behavior defines a concept.
- Broken cross-references corrected: §7→§8 (replay), §15→§17 (Normative Summary).

---

## [0.5.0] — May 2026

**TRUNCATE specification.** Wire contract extended with TRUNCATE semantics.

- §10.2 fully reworked: transactional vs. non-transactional TRUNCATE classification; multi-table TRUNCATE (P-ORD-7); synthetic cdcxid for Oracle/MySQL.
- New `truncate_details` object with four-value flag semantics (`true | false | "not_applicable" | "unknown"`).
- `propagated_tables` (CASCADE-affected table list) explicitly deferred.
- New rules: P-TRUNC-1..4, C-TRUNC-1..4, T-11..T-14.

---

## [0.4.0] — May 2026

**Schema delivery modes and sequence redesign.**

- §4 restructured: four named schema delivery modes (Schema on Change, Schema on Reconnect, Schema on Each Event, Schema by Reference) with Reconnect Coverage constraint.
- `pos.sequence` renamed to `pos.lsn_offset`.
- CloudEvents `sequence` defined as producer-synthetic, session-scoped, gaps permitted.
- New §8.4 Sequence Discontinuity with five canonical scenarios.
- HEARTBEAT gains `lsn_reset` and `sequence_reset`.
- New rules: P-SCHEMA-1..5, P-SEQ-1..6, C-SEQ-1..4.

---

## [0.2.0] — May 2026 *(includes patch 0.3)*

**OpenCDC rename and major feature addition.**

- Renamed CDC-OIS → OpenCDC throughout.
- Adopted schema-before-first-use as sole mandatory baseline.
- Type metadata moved to OBJECT_METADATA; DML payloads carry values only.
- Added: Producer Contract, Consumer Contract, Idempotency & Deduplication, Loop Prevention, Replay Semantics, Partial UPDATE (`changed_columns`), Observability fields, Security section, Quick Start.
- Hardened MUST/SHOULD/MAY language throughout.

---

## [0.1.0] — March 2026

**Initial draft.**

- CloudEvents envelope, new payload structure, per-row typed column descriptors, schema delivery options, lifecycle events.

---

*The complete normative change log is also maintained inside `spec/OpenCDC-Specification.md` under the Change Log section.*
