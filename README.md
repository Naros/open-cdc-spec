# OpenCDC

**An open, vendor-neutral standard for the structure and semantics of database change events.** Any conformant producer — CDC tool or database — can interoperate with any conformant consumer — CDC tool, pipeline, lakehouse, or AI application — without custom translation.

Built on [CloudEvents v1.1](https://cloudevents.io/) for envelopes, and targeting support from all major CDC tools, Databases, AI/Agentic and Lakehouse technologies.

## Document Family

| Document | Role | Current |
|---|---|---|
| [spec/OpenCDC-Specification.md](spec/OpenCDC-Specification.md) | **Normative.** Event structure, ordering, producer contract, capability axes, lifecycle, replay, conformance | Draft v0.7.0 |
| [spec/OpenCDC-TypeSystem.md](spec/OpenCDC-TypeSystem.md) | **Normative.** Two-layer type system, canonical vocabulary, wire encoding rules | Draft v0.2 |
| [spec/OpenCDC-ArchitectureDecisionRecord.md](spec/OpenCDC-ArchitectureDecisionRecord.md) | Informative. The "why" behind every spec decision (ADR-0001..0035) | v0.2 |
| [spec/OpenCDC-UserStories.md](spec/OpenCDC-UserStories.md) | Informative. Six motivating use cases with priorities | Fifth Draft |
| [spec/GLOSSARY.md](spec/GLOSSARY.md) | Informative. Definitions of all terms used in the specification family | v1.1 |
| [examples/OpenCDC-PayloadExamples.md](examples/OpenCDC-PayloadExamples.md) | Informative. Annotated reference stream (9 events incl. TRX_COMMIT) | wire 0.3 |
| [schemas/](schemas/) | Informative tooling. JSON Schemas for envelope + payloads (closed-world) | wire 0.3 |
| [registry/requirements.yaml](registry/requirements.yaml) | Working-group data. Requirements register + compliance matrix source | spec 0.7.0 |

Authority rules (who wins on conflict) are defined in the Specification's *Document Authority and Scope* section. Versions across the family are tracked in [registry/versions.yaml](registry/versions.yaml).

## Reading Paths

- **Producer implementer:** Spec §1 Quick Start → §3 Envelope → §4 Schema Delivery → §5 DML → §6 Producer Contract → §8 Replay → Type System §4–6 → Payload Examples.
- **Consumer implementer:** Spec §1 → §3–5 → §8 → Appendix A (service-level guidance) → Payload Examples.
- **Evaluator / architect:** Spec §1 → §2 Design Principles → User Stories → ADR Decision Index.
- **Conformance tester:** Spec §17 Normative Summary → §19 Conformance → registry/requirements.yaml → schemas/.

## Working-Group Tooling

The Specification's §17 Normative Summary and §19.1 Compliance Matrix are **generated** from `registry/requirements.yaml`. The body prose remains the source of truth for requirement semantics; the register is the source of truth for the derived sections. After any edit:

```bash
./check.sh          # run all drift and validation checks
```

Individual tools (all support `--check`):

| Tool | Purpose |
|---|---|
| `tools/generate_sec17.py` | Regenerate/verify Spec §17 from the register |
| `tools/generate_matrix.py` | Regenerate/verify Spec §19.1 from the register |
| `tools/generate_toc.py` | Regenerate/verify Tables of Contents |
| `tools/audit_register.py` | Two-way audit: register IDs ↔ body anchors |
| `tools/validate_examples.py` | Validate every Payload Example against the JSON Schemas |

CI runs `check.sh` on every pull request (`.github/workflows/ci.yml`).

## Status

OpenCDC is a **draft for discussion** by the OpenCDC Working Group. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to participate and [GOVERNANCE.md](GOVERNANCE.md) for working-group structure and decision-making. The specification governs producer behavior; consumer behavior is non-normative service-level guidance (see ADR-0025). Wire protocol version: **0.3**.
