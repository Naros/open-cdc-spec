# Contributing to OpenCDC

Thank you for your interest in OpenCDC. This document explains how to participate in the working group, report issues, and submit changes.

## Before You Contribute

Read the [OpenCDC Specification](spec/OpenCDC-Specification.md) and the [Architecture Decision Record](spec/OpenCDC-ArchitectureDecisionRecord.md). The ADR explains *why* the specification is designed the way it is. Understanding the rationale will help you make proposals that fit the design principles and avoid re-opening settled decisions.

## How to Participate

**Discussion and questions** — Open a GitHub Issue. Use the issue to ask questions, flag potential spec ambiguities, or propose new requirements before writing any text. This avoids duplicated effort and lets the working group align on intent before implementation.

**Bug reports** — Open an Issue describing: the specific section, the exact text you believe is incorrect, what you believe it should say, and why. Attach a test case (a payload example or scenario) if possible.

**Substantive proposals** — Open an Issue first to gauge working-group interest. When ready, submit a Pull Request against `main` with your changes to the relevant documents.

## Making Changes

### What changes require a working-group decision

- Any change to a MUST, MUST NOT, or SHOULD requirement
- New fields, event types, or extension attributes
- Changes to the wire protocol version (`cdcspecversion`)
- Changes to the Type System canonical vocabulary
- New Architecture Decision Records (ADRs)

Open an Issue for any of the above before submitting a PR. The working group will discuss and record the decision.

### Editorial changes (can go straight to PR)

- Fixing typos or grammatical errors
- Clarifying existing text without changing normative meaning
- Adding or improving examples in `examples/`
- Updating `GLOSSARY.md` definitions that are already covered by existing normative text

### PR requirements

Every PR must pass the check suite before it can be merged:

```bash
pip install pyyaml jsonschema
./check.sh
```

The checks verify:
- Section 17 Normative Summary matches `registry/requirements.yaml`
- Section 19.1 Compliance Matrix matches the register matrix
- Tables of Contents are up to date in all spec documents
- All payload examples in `examples/OpenCDC-PayloadExamples.md` validate against the JSON Schemas
- All requirement IDs in the body are registered, and all register entries are anchored in the body

If your PR changes a normative requirement, you must also update `registry/requirements.yaml` — the register is the source of truth for §17 and §19.1. After editing the register, regenerate the derived sections:

```bash
python3 tools/generate_sec17.py spec/OpenCDC-Specification.md registry/requirements.yaml
python3 tools/generate_matrix.py spec/OpenCDC-Specification.md registry/requirements.yaml
```

### Version bumps

Patch versions (0.6.x → 0.6.y): editorial changes, clarifications, example fixes. No bump to the wire protocol version.

Minor versions (0.6.x → 0.7.0): new optional fields or event types, backward-compatible extensions. Wire protocol version MAY bump.

Major versions: breaking changes to the wire contract. Wire protocol version MUST bump. Requires working-group consensus.

The wire protocol version (`cdcspecversion` / `opencdc_version`) is distinct from the specification document version. See `versions.yaml` for the current values and the bump policy.

## Document Ownership

| Document | Governed by |
|---|---|
| `spec/OpenCDC-Specification.md` | Working group; all normative changes require consensus |
| `spec/OpenCDC-TypeSystem.md` | Working group; type system changes require consensus |
| `spec/OpenCDC-ArchitectureDecisionRecord.md` | Working group; new ADRs require consensus |
| `spec/OpenCDC-UserStories.md` | Working group; informative, lower bar for updates |
| `spec/GLOSSARY.md` | Working group; definitions must match normative text |
| `examples/` | Open for community improvement via PR |
| `schemas/` | Derived from the spec; updated when spec normative content changes |
| `registry/requirements.yaml` | Updated in lockstep with spec normative changes |
| `tools/` | Open for community improvement via PR |

## Code of Conduct

Participation in the OpenCDC working group is governed by the [CNCF Code of Conduct](https://github.com/cncf/foundation/blob/main/code-of-conduct.md). Be respectful, assume good intent, and focus feedback on technical substance.
