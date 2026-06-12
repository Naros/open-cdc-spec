# OpenCDC Governance

## Status

OpenCDC is a **working group draft** specification. The governance model described here reflects the project's current stage: a small, active working group producing an initial standard. It is expected to evolve as the project matures and broader vendor participation is established.

## Working Group

The OpenCDC Working Group is responsible for:

- Maintaining and evolving the OpenCDC Specification and companion documents
- Reviewing and deciding on proposals from contributors
- Managing the conformance testing framework
- Coordinating vendor participation and implementation feedback
- Deciding on version bumps and release milestones

## Decision Making

The working group operates by **consensus with a designated lead** for the current draft phase. Decisions follow this process:

1. **Proposal** — Any interested party may open a GitHub Issue proposing a change. Proposals must include the rationale, the specific text change, and the alternatives considered.
2. **Discussion** — The working group discusses the proposal in the Issue. A minimum of one week is allowed for comment before a decision is called.
3. **Decision** — The working group lead calls the decision. Consensus means no substantive unresolved objections. Dissents are recorded — see the Architecture Decision Record for examples of how dissents are documented and preserved.
4. **Record** — Accepted decisions that change normative behavior are recorded in the [Architecture Decision Record](spec/OpenCDC-ArchitectureDecisionRecord.md).

**What requires working-group consensus:**
- Any change to a MUST, MUST NOT, or SHOULD requirement
- New fields, event types, extension attributes, or type vocabulary entries
- Changes to the wire protocol version
- Promotion of informative artifacts to normative status (e.g., JSON Schemas)
- Addition of new normative reference documents

**What does not require consensus:**
- Editorial and typographic fixes
- Clarifications that do not change normative meaning
- New examples in `examples/`
- Tooling improvements in `tools/`

## Roles

**Working Group Lead** — Holds final decision authority during the current draft phase. Responsible for calling consensus, managing releases, and coordinating vendor outreach.

**Working Group Members** — Individuals or vendor representatives actively participating in specification development. Membership is open; participation in GitHub discussions and PRs constitutes membership.

**Contributors** — Anyone who submits an Issue or Pull Request. No formal membership required.

**Reviewers** — Working group members who review and approve PRs. At least one reviewer approval is required to merge any PR that touches normative content.

## Versioning and Releases

The specification uses a two-track versioning scheme:

**Wire protocol version** (`cdcspecversion` / `opencdc_version` in events) — Changes only when the on-wire event contract changes: new required fields, changed semantics, or backward-incompatible structural changes. All events carry this version. A bump here requires working-group consensus and advance notice to implementers.

**Document revision** (e.g., `v0.6.x`) — Tracks editorial and structural changes to the specification documents. Does not imply a wire contract change. Patch releases (x.y.Z) are editorial; minor releases (x.Y.0) are structural additions.

The current values are recorded in [`versions.yaml`](versions.yaml).

## Vendor Participation

OpenCDC is designed to be vendor-neutral and welcomes participation from database vendors, CDC tool vendors, streaming platform vendors, and end-user organizations. Vendor representatives participate as Working Group Members with the same rights and responsibilities as individual contributors.

If your organization is interested in formally joining the working group or becoming a reference implementation, open an Issue or contact the Working Group Lead.

## Relationship to Standards Bodies

OpenCDC is currently an independent working-group draft. The working group is evaluating potential submission to a standards body (CNCF, Apache, or similar) as the specification matures. Any such submission will be announced and discussed openly before proceeding.

## Amendments to this Document

This governance document may be amended by working-group consensus following the same process as normative specification changes.
