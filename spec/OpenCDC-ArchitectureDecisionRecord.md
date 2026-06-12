# OpenCDC Architecture Decision Record (ADR)

Draft v0.1 -- June 2026

Status: Draft for Discussion

OpenCDC Working Group

**Abstract**
This document records the architecture and design decisions behind the OpenCDC Specification. It is the companion "why" document to the specification's "what." The specification states the rules a conformant producer must follow; this record explains the reasoning behind those rules -- the forces in tension, the option that was adopted, the consequences accepted, and the alternatives that were rejected and why. It exists so that an implementer (or a future editor of the specification) can understand the intent behind a constraint without that intent cluttering the normative text. Decisions recorded here were extracted from the specification at v0.6 (former Section 2.9, Section 18, and Appendix A, plus comparative asides in Sections 9 and 10.2). This document is an informative reference to the OpenCDC Specification; nothing here overrides normative text in that document.

---

## How to Read This Record

Each entry below is a single Architecture Decision Record (ADR) following a lightly adapted MADR / Nygard structure:

- **Status** -- Proposed, Accepted, Superseded, or Deferred. An Accepted decision is reflected in the current specification text.
- **Context** -- the problem, constraint, or force that required a decision.
- **Decision** -- what was chosen, stated plainly.
- **Consequences** -- what becomes easier, harder, or constrained as a result, including obligations the decision imposes.
- **Alternatives Considered** -- the options that were weighed and rejected, with the reason for rejection.

Where a decision is anchored in a specification principle (for example, Infrastructure Independence or Source Agnosticism) or a normative section, the entry cites it. Citations of the form "Section X" and rule identifiers (P-*, C-*, T-*) refer to the OpenCDC Specification.

---

## Decision Index

- ADR-0001 -- Base architecture: a self-describing, inline-schema stream
- ADR-0002 -- Schema-before-first-use as the sole mandatory schema baseline
- ADR-0003 -- Four named schema-delivery modes instead of a free-form option set
- ADR-0004 -- Schema by Reference cannot satisfy reconnect coverage alone
- ADR-0005 -- Removal of the "Schema on Batch Envelope" mode
- ADR-0006 -- `_schema` embedding lives in the DML `data` object, not the envelope
- ADR-0007 -- Type metadata in OBJECT_METADATA; values-only DML payloads
- ADR-0008 -- Full English operation names in the CloudEvents `type` field
- ADR-0009 -- Transaction identity at the envelope layer plus structured position in the payload
- ADR-0010 -- ISO 8601 / RFC 3339 string encoding for all timestamps
- ADR-0011 -- DDL as first-class events in the same ordered stream
- ADR-0012 -- Closed-world schema enforcement (`additionalProperties: false`)
- ADR-0013 -- Opt-in partial UPDATE images via `changed_columns`
- ADR-0014 -- Producer-side loop prevention for bidirectional sync
- ADR-0015 -- Project naming: OpenCDC (formerly CDC-OIS)
- ADR-0016 -- The CloudEvents `sequence` counter is producer-synthetic, not source-derived
- ADR-0017 -- `pos.lsn_offset` and CloudEvents `sequence` are kept as separate fields
- ADR-0018 -- CloudEvents `sequence` permits gaps; `cdctxorder` does not
- ADR-0019 -- `sequence_continuity` is a session-level declaration, not a per-event flag
- ADR-0020 -- The specification defines the output contract, not engine-specific implementation paths
- ADR-0021 -- TRUNCATE is classified as a `dml.TRUNCATE` event
- ADR-0022 -- `truncate_details` uses a four-value flag set
- ADR-0023 -- `propagated_tables` (CASCADE-affected table list) is deferred
- ADR-0024 -- `truncate_details.sequence_reset` reuses the existing "reset" vocabulary
- ADR-0025 -- Specification scope: govern producer behavior; consumer behavior is non-normative service-level guidance

---

## ADR-0001 -- Base architecture: a self-describing, inline-schema stream

**Status:** Accepted

**Context**
A CDC interoperability standard has to start from an architectural stance on how schema reaches the consumer. Two mature, production-proven CDC architectures were available as starting points and were evaluated against the project's portability goals:

- One architecture delivers schema as self-describing, first-class records that travel inline ahead of the data they describe, treats DDL as a first-class event transactionally ordered with DML, expresses schema in a standards-compliant, independently validatable form with closed-world enforcement, and uses full operation names with an explicit upsert.
- The other architecture delivers schema either repeated per message or offloaded to an external registry, routes DDL to a channel separate from the data (so schema changes cannot be correlated with the data changes that depend on them), expresses schema in a proprietary, non-standard form that standard validators cannot check, is descriptive-only (consumers must tolerate unknown fields), and uses single-character operation codes with no native upsert. Its design is optimized for one specific transport ecosystem rather than for general portability.

**Decision**
Adopt the self-describing, inline-schema architecture as the structural baseline for OpenCDC. Build on its strengths (schema-in-stream, DDL as a first-class ordered event, standards-based schema, closed-world enforcement, readable operation vocabulary) while correcting its weaknesses: remove source-engine-specific assumptions, replace non-standard schema constructs with JSON Schema, eliminate per-row type-annotation verbosity by moving type metadata to the schema event, and add the missing lifecycle event types.

**Consequences**
- A conformant stream is interpretable from the stream alone, satisfying Infrastructure Independence (Section 2.1) and Self-Describing Streams (Section 2.2).
- The result is a portable standard that no existing tool implements verbatim; vendors must map their native output onto it.
- Subsequent decisions (ADR-0002, ADR-0007, ADR-0011, ADR-0012) are refinements of this stance.

**Alternatives Considered**
- *Adopt the registry/per-message, Kafka-Connect-optimized architecture as the baseline.* Rejected: its design choices optimize for a single transport ecosystem rather than general portability, its proprietary schema form is not independently validatable, and its separation of DDL from data breaks transactional correlation.

---

## ADR-0002 -- Schema-before-first-use as the sole mandatory schema baseline

**Status:** Accepted

**Context**
Schema delivery is the most consequential design decision in a CDC standard. If schema delivery is optional or under-specified, two independently "conformant" producers can be mutually unintelligible to the same consumer. A consumer that receives a DML event with no prior schema cannot resolve `logical_type`, cannot apply wire-encoding rules, and cannot validate the payload.

**Decision**
Make Schema on Change -- an OBJECT_METADATA event emitted before the first DML for a table and re-emitted after any structural DDL -- the single unconditional mandatory baseline. No other delivery mode may substitute for it (Section 4.1).

**Consequences**
- Schema-before-first-use is the weakest guarantee that still yields an independently consumable stream, so it is the right floor.
- Every producer carries the obligation to track current schema per table and order it ahead of data.
- Optional modes layer on top of this baseline rather than replacing it.

**Alternatives Considered**
- *Schema per row.* Rejected: O(rows x columns) overhead repeating type metadata on every event.
- *Schema per transaction.* Rejected: adds producer complexity for little gain on single-table high-volume workloads.
- *External registry only.* Rejected: violates Infrastructure Independence (Section 2.1) -- the stream is no longer self-contained.
- *Make schema delivery entirely optional.* Rejected: produces a conformance landscape in which two conformant producers can be mutually incompatible.

---

## ADR-0003 -- Four named schema-delivery modes instead of a free-form option set

**Status:** Accepted

**Context**
An earlier draft offered three loosely defined schema options with no declared, machine-readable indication of which were active. A consumer could only discover a producer's behavior by reading documentation or probing empirically.

**Decision**
Define exactly four named modes -- Schema on Change (baseline), Schema on Reconnect (connection-time), Schema on Each Event (event-time inline), Schema by Reference (registry) -- each with an explicit flag declared in the STREAM_METADATA `schema_delivery` object (Section 4.4).

**Consequences**
- Schema acquisition becomes a protocol question answered at connection time, not a documentation question; the consumer adapts automatically.
- The four modes cover the complete set of legitimate acquisition paths without overlap: change-time, connection-time, event-time, registry-based.

**Alternatives Considered**
- *Keep a free-form options set without flags.* Rejected: forces out-of-band coordination and empirical probing; no interoperable way for a consumer to know what a producer does.

---

## ADR-0004 -- Schema by Reference cannot satisfy reconnect coverage alone

**Status:** Accepted

**Context**
Schema by Reference points `dataschema` at an external registry. If that were a producer's only schema path, a network-isolated consumer or a registry outage would make DML events undecodable -- a direct violation of Infrastructure Independence (Section 2.1).

**Decision**
Require that at least one stream-embedded mode (Schema on Reconnect or Schema on Each Event) be active in addition to Schema on Change. Schema by Reference may supplement but never be the sole acquisition path (Section 4.4, Reconnect Coverage rule).

**Consequences**
- Any conformant consumer can always acquire schema from the stream itself, regardless of registry availability.
- Registry-backed deployments still gain the registry's benefits without sacrificing self-containment.

**Alternatives Considered**
- *Allow registry-only schema delivery.* Rejected: reintroduces the external infrastructure dependency the standard is designed to avoid.

---

## ADR-0005 -- Removal of the "Schema on Batch Envelope" mode

**Status:** Accepted (supersedes an earlier draft mode)

**Context**
An earlier draft included a "Schema on Batch Envelope" mode that carried the schema once per batch of N events. Once Schema on Each Event and Schema on Change existed, this mode occupied an underspecified middle ground, and its use cases overlapped entirely with the encoding layer.

**Decision**
Remove Schema on Batch Envelope. When events are serialized as Arrow IPC frames, Avro container files, or Parquet row groups, the encoding format already carries schema metadata natively, governed by Payload Encoding Agnosticism (Section 2.7).

**Consequences**
- One fewer mode to specify and test; the remaining four are cleanly distinct.
- Batch-level schema efficiency is achieved through the chosen wire encoding rather than a bespoke OpenCDC mode.

**Alternatives Considered**
- *Retain and fully specify the batch envelope.* Rejected: it was the least-specified original option (a single sentence, no field definitions) and duplicated capabilities the encoding layer already provides.

---

## ADR-0006 -- `_schema` embedding lives in the DML `data` object, not the envelope

**Status:** Accepted

**Context**
Schema on Each Event embeds a full OBJECT_METADATA payload in every DML event. The question was where: in the CloudEvents envelope (as an extension attribute) or inside the `data` object.

**Decision**
Embed `_schema` as a top-level key inside the DML `data` object, alongside `before`, `after`, `pos`, `_null_columns`, and `_lob_overflow` (Section 4.5.3).

**Consequences**
- Consistent with the CloudEvents intent that envelope extension attributes be small scalar values suitable for header-level filtering; a full schema payload does not belong there.
- Consumers that do not need inline schema can skip parsing `_schema` with no envelope-level impact.

**Alternatives Considered**
- *Place the embedded schema in a CloudEvents extension attribute.* Rejected: violates the CloudEvents specification's intent for extension attributes and burdens infrastructure that inspects headers.

---

## ADR-0007 -- Type metadata in OBJECT_METADATA; values-only DML payloads

**Status:** Accepted

**Context**
Type information (source type, logical type, parameters, nullability) has to live somewhere. The inherited architecture placed typed descriptors inside each row's value payload, repeating type metadata on every event.

**Decision**
Carry type metadata exclusively in the OBJECT_METADATA column descriptors; DML `before`/`after` objects carry values only (Section 4.1, Section 5). This aligns with the OpenCDC Type System Proposal.

**Consequences**
- DML payloads are compact; type resolution is a cache lookup keyed by `dataschema`.
- Correctness depends on the schema-before-first-use guarantee (ADR-0002): without the schema, values are uninterpretable.

**Alternatives Considered**
- *Per-row typed descriptors `{value, source_type, is_null}`.* Rejected: repeats type information on every event. The principle of carrying type fidelity is correct, but the placement (value payload rather than schema) is wrong.

---

## ADR-0008 -- Full English operation names in the CloudEvents `type` field

**Status:** Accepted

**Context**
Operations must be encoded so that infrastructure can route and filter on them. The inherited alternative used single-character op codes (c/u/d/r) carried in the payload.

**Decision**
Use full English operation names (INSERT, UPDATE, DELETE, UPSERT, TRUNCATE, etc.) encoded in the CloudEvents `type` field (Section 3.2). Single-character codes are non-conformant.

**Consequences**
- Routers and filters can act on the operation without deserializing the payload.
- Logs and routing rules are human-readable.

**Alternatives Considered**
- *Single-character op codes.* Rejected: no meaningful optimization and unreadable in logs and routing rules.
- *Encode the operation only in the payload.* Rejected: forces deserialization to route.

---

## ADR-0009 -- Transaction identity at the envelope layer plus structured position in the payload

**Status:** Accepted

**Context**
Consumers and infrastructure both need transaction identity, but for different reasons: routers need to group events by transaction without deserializing, while consumers need structured replay context. A single placement cannot serve both.

**Decision**
Carry `cdcxid` and `cdctxorder` as CloudEvents envelope fields, and carry the structured `pos` object in the payload (Section 3.3, Section 8). The two layers are complementary and must not be conflated.

**Consequences**
- Infrastructure can group and order by transaction purely from the envelope.
- Consumers retain full structured position context for replay and gap detection in the payload.

**Alternatives Considered**
- *Position only in the payload.* Rejected: forces deserialization merely to group events by transaction.
- *Position only in the envelope.* Rejected: loses structured replay context for consumers.

---

## ADR-0010 -- ISO 8601 / RFC 3339 string encoding for all timestamps

**Status:** Accepted

**Context**
Timestamps must be unambiguous across heterogeneous systems and time zones.

**Decision**
Encode all timestamp and duration values as ISO 8601 / RFC 3339 strings (Normative References; Section 5.3).

**Consequences**
- Time zone and precision are explicit on the wire; no shared convention must be assumed.

**Alternatives Considered**
- *Epoch milliseconds.* Rejected: requires the consumer to know the epoch convention and time zone, which is ambiguous across systems.

---

## ADR-0011 -- DDL as first-class events in the same ordered stream

**Status:** Accepted

**Context**
Schema changes and the data changes that depend on them must remain correlated. An architecture that routes DDL to a channel separate from the data stream cannot tell a consumer which data events followed which schema change.

**Decision**
Emit DDL as first-class CloudEvents, transactionally ordered with DML in the same stream, with a new OBJECT_METADATA emitted after structural DDL and before the next DML for that table (Section 9, Section 4.1).

**Consequences**
- A consumer can detect and handle schema evolution by reading only the stream (Section 2.5).
- Producers must serialize DDL into the same ordered channel as data.

**Alternatives Considered**
- *Route DDL to a separate channel/topic.* Rejected: breaks the transactional correlation between schema changes and dependent data changes; the consumer cannot determine which data followed which DDL.

---

## ADR-0012 -- Closed-world schema enforcement (`additionalProperties: false`)

**Status:** Accepted

**Context**
A standard must define a precise contract for what may appear in a payload. Descriptive-only schemas that tolerate unknown fields let silent interoperability failures pass undetected.

**Decision**
Require every OBJECT_METADATA `json_schema` block to enforce `additionalProperties: false`; unrecognized fields in a DML value payload are a validation failure, not a warning (Section 2.4, Section 4.2).

**Consequences**
- Consumers get a precise contract: a field present in a payload was declared in the schema.
- Producers cannot quietly add fields; doing so makes them non-conformant.

**Alternatives Considered**
- *Open schemas that accept unknown fields silently.* Rejected: a standard must define precise contracts; silent acceptance creates silent interoperability failures.

---

## ADR-0013 -- Opt-in partial UPDATE images via `changed_columns`

**Status:** Accepted

**Context**
Full before/after images are expensive for wide tables, particularly those with LOB columns, but always-partial images prevent consumer-side full-row reconstruction without state.

**Decision**
Support partial UPDATE images as an opt-in: when `changed_columns` is present, `before`/`after` carry only those columns (plus the primary key); when absent, they carry all columns (Section 5.4). An absent column in a partial image means "unchanged," never null.

**Consequences**
- Producers that can identify changed columns reduce payload size for wide tables.
- The absent-column rule must be applied carefully by anything reconstructing rows (stated as consumer guidance in Appendix A).

**Alternatives Considered**
- *Always full images.* Rejected: too expensive for wide / LOB-bearing tables.
- *Always partial images.* Rejected: prevents full-row reconstruction without consumer-side state management.

---

## ADR-0014 -- Producer-side loop prevention for bidirectional sync

**Status:** Accepted

**Context**
Bidirectional database-to-database sync risks infinite loops: a change from System A is applied by System B, then recaptured and emitted back to A. Only one party can reliably break the loop.

**Decision**
Make loop suppression a producer obligation based on `source`-field matching, with an optional `cdcsourceid` extension for cases where URI comparison is insufficient. The producer that applies a remote event tags the resulting local transaction with the original `cdcxid`; the capture layer recognizes the tag and suppresses re-emission (Section 3.4, rule P-LOOP-1).

**Consequences**
- The loop is broken at the only layer with reliable visibility into transaction origin: the producer reading the transaction log.
- Consumer-side filtering is at best a defensive secondary measure, never the primary mechanism.

**Alternatives Considered**
- *Consumer-side filtering as the primary mechanism.* Rejected: a consumer cannot reliably determine an event's origin; a system relying on it appears to work but corrupts data if producer-side filtering ever fails.

---

## ADR-0015 -- Project naming: OpenCDC (formerly CDC-OIS)

**Status:** Accepted

**Context**
The project was originally named CDC-OIS. The working group settled on a clearer, consistent name.

**Decision**
Use "OpenCDC" throughout. All "CDC-OIS" references were retired.

**Consequences**
- Consistent naming across the specification, type system, and user-stories documents.

**Alternatives Considered**
- *Retain CDC-OIS.* Rejected for consistency with the working group's naming convention.

---

## ADR-0016 -- The CloudEvents `sequence` counter is producer-synthetic, not source-derived

**Status:** Accepted

**Context**
A total-ordering counter is needed across all events a producer emits in a session. Source log positions (SCNs, WAL LSNs, binlog offsets/GTIDs, and other engine-specific formats) are heterogeneous, not comparable across engines, and not trivially encodable as a monotonic decimal string without engine-specific logic.

**Decision**
Define the CloudEvents `sequence` field as a producer-assigned, session-scoped counter that reflects emission order, not source position (Section 3.3). Source position remains available separately in `pos.lsn`, `pos.native_position`, and `cdcpos`.

**Consequences**
- `sequence` stays engine-neutral, consistent with Source Agnosticism (Section 2.6).
- It is an emission-process concern, decoupled from how any particular engine numbers its log.

**Alternatives Considered**
- *Derive `sequence` from source log position.* Rejected: makes the field engine-specific and contradicts Source Agnosticism; source position is already represented by other fields.

---

## ADR-0017 -- `pos.lsn_offset` and CloudEvents `sequence` are kept as separate fields

**Status:** Accepted

**Context**
Two genuinely different ordering questions exist: "which of the events generated from this one log record is this?" and "what is the total emission order across the whole session?"

**Decision**
Keep two fields. `pos.lsn_offset` is source-derived and LSN-scoped (a small integer that resets at each new LSN, used for replay positioning). CloudEvents `sequence` is producer-assigned and session-scoped (never resets within a session). See Section 8.1 and Section 3.3.

**Consequences**
- The apparent redundancy of two sequence-like fields correctly reflects two distinct ordering concerns.

**Alternatives Considered**
- *A single unified ordering field.* Rejected: it cannot answer both the per-LSN disambiguation question and the session-wide total-order question.

---

## ADR-0018 -- CloudEvents `sequence` permits gaps; `cdctxorder` does not

**Status:** Accepted

**Context**
Whether a gap in an ordering counter indicates data loss depends on how the counter is assigned.

**Decision**
`cdctxorder` is assigned within a transaction whose event count is known at capture time, so it must be gapless and monotonic -- a gap is a data-integrity violation (rule T-ORDER). The CloudEvents `sequence` is assigned across the whole stream and may be filtered per consumer or shared across subscriptions, so gaps are permitted and MUST NOT be read as dropped events (Section 3.3, rule C-SEQ-1; rationale in Section 8.x).

**Consequences**
- Consumers can use `cdctxorder` gaps for reliable intra-transaction loss detection, but must not use `sequence` gaps for loss detection.

**Alternatives Considered**
- *Require `sequence` to be gapless too.* Rejected: a producer streaming several tables to multiple filtered consumers via a shared counter will legitimately deliver gaps to a filtered consumer through no fault of its own.

---

## ADR-0019 -- `sequence_continuity` is a session-level declaration, not a per-event flag

**Status:** Accepted

**Context**
Continuity breaks (migration, failover, binlog rotation) are rare but must be signaled. A per-event flag would tax every event to communicate a condition that is almost always false.

**Decision**
Declare continuity once per session in STREAM_METADATA (`sequence_continuity`) and signal mid-session changes through HEARTBEAT (`lsn_reset`, `sequence_reset`) -- both natural transition-point carriers (Section 8.4).

**Consequences**
- No per-event overhead for a rare condition; at high throughput even one always-false boolean per event is measurable in aggregate.
- Transition points are unambiguous: "from this point in the session forward, the guarantee has changed."

**Alternatives Considered**
- *A per-event continuity flag.* Rejected: imposes constant overhead and creates ambiguity about whether the flag applies to the current or subsequent events.

---

## ADR-0020 -- The specification defines the output contract, not engine-specific implementation paths

**Status:** Accepted

**Context**
A specification that also defined GTID handling, SCN encoding, and WAL LSN normalization for each engine would become a database-internals reference, too large to be useful and too coupled to engine versions to stay accurate.

**Decision**
Specify what a conformant output looks like (for example, `pos.lsn` must be a hex-encoded monotonically increasing string; `sequence_continuity` must accurately reflect the producer's guarantee) and leave the path to that output to the implementer (Section 8.4.4).

**Consequences**
- The specification stays bounded and engine-agnostic; canonical discontinuity scenarios state producer obligations, not implementation recipes.

**Alternatives Considered**
- *Define per-engine position-handling algorithms in the specification.* Rejected: produces an oversized, version-coupled document and conflates a CDC standard with engine internals.

---

## ADR-0021 -- TRUNCATE is classified as a `dml.TRUNCATE` event

**Status:** Accepted

**Context**
TRUNCATE does not fit cleanly into either category: it changes data (so it is not really DDL) but carries no before/after image (so it is not ordinary DML). Existing CDC tools handle this ambiguity poorly.

**Decision**
Classify TRUNCATE as a DML-category `dml.TRUNCATE` event so it keeps its place in the transactional event stream alongside INSERT, UPDATE, and DELETE, with both `before` and `after` null and no new schema version (Section 10.2.1). It denotes deletion of all rows in the named table.

**Consequences**
- TRUNCATE retains transactional position and ordering with surrounding DML where the engine is transactional (ADR-0022 covers the engine-specific transactional differences).
- Consumers treat it as "delete all rows" (stated as consumer guidance in Appendix A.6).

**Alternatives Considered**
- *Classify TRUNCATE as DDL.* Rejected: it changes data, not schema, and would fall out of the data event stream.
- *Force it into ordinary DML semantics.* Rejected: it has no before/after image to carry.

---

## ADR-0022 -- `truncate_details` uses a four-value flag set

**Status:** Accepted

**Context**
TRUNCATE has materially different execution semantics across engines (cascade behavior, identity/sequence reset), and a producer cannot always observe these from the capture layer. A simple boolean cannot honestly represent all of these states. Consider `cascade` across engines: one engine can report a deterministic true/false from its log, while several others have no cascade-truncation concept at all. Under a boolean model the latter would always emit `false` -- implying "available but not chosen" when the truth is "the concept does not exist here."

**Decision**
Use a four-value set for `cascade` and `sequence_reset`: `true | false | "not_applicable" | "unknown"`. `multi_table` remains a deterministic boolean. The core contract is unchanged: TRUNCATE empties the table, `before` and `after` are null. `truncate_details` is optional and MUST NOT be fabricated (Section 10.2.5, rule P-TRUNC-4).

**Consequences**
- `"not_applicable"` gives a consumer an unambiguous contract for engines that lack the concept, so it can hard-code behavior without inspecting the flag per event.
- `"unknown"` lets a producer be honest about an observability gap rather than guessing; the consumer applies a safe default and logs the uncertainty.
- A `false` is meaningfully distinct from `"not_applicable"`: it asserts the option existed and was not used.

**Alternatives Considered**
- *A vendor-specific mini-language.* Rejected in favor of three portable, effect-oriented flags covering the semantically meaningful cases across engines.
- *Collapse `"not_applicable"` and `"unknown"` into one value.* Rejected: they are operationally distinct -- one is a stable engine fact, the other a runtime observability uncertainty; conflating them forces consumers to treat stable facts as uncertainties.
- *Name the field `identity_action` (one engine's vocabulary).* Rejected in favor of `sequence_reset` for cross-engine portability (see ADR-0024).
- *Make `truncate_details` required.* Rejected: not every engine exposes the semantics and not every capture layer can observe them; a SHOULD with a "do not fabricate" prohibition is the correct level.

---

## ADR-0023 -- `propagated_tables` (CASCADE-affected table list) is deferred

**Status:** Deferred

**Context**
The obvious extension to `truncate_details` is a `propagated_tables` array listing every table implicitly truncated by CASCADE. But CASCADE can propagate through multiple levels of foreign-key relationships, and the causal chain cannot be read from the log alone -- it requires catalog lookups (for example, querying constraint metadata at capture time) that are not reliably available across capture implementations, concurrency conditions, or replication-slot behavior.

**Decision**
Defer `propagated_tables` to a future specification version. Producers MUST NOT emit it in current conformant payloads. The explicit multi-table case (a single statement naming several tables) is handled instead by the `multi_table` flag and rule P-ORD-7, because that table list comes directly from the SQL statement with no catalog inference.

**Consequences**
- The standard avoids a field that producers would frequently populate incompletely -- an incomplete list is worse than none because it creates a false sense of completeness.
- A reliable mechanism can be defined later without breaking current payloads.

**Alternatives Considered**
- *Specify `propagated_tables` now.* Rejected: it cannot be reconstructed reliably from the log without catalog inference that imposes overhead not all producers can provide.

---

## ADR-0024 -- `truncate_details.sequence_reset` reuses the existing "reset" vocabulary

**Status:** Accepted

**Context**
The flag indicating whether a table's identity/auto-increment counter was reset by a TRUNCATE needs a name. Engine-native vocabulary for this concept is engine-specific and does not transfer. A field named `sequence_reset` also already exists in HEARTBEAT events, where it means something different (a reset of the stream-level `sequence` counter).

**Decision**
Name the field `sequence_reset`, expressing the effect (a counter was reset) rather than any engine's mechanism, and rely on a disambiguation note (Section 10.2.5) to separate it from the HEARTBEAT field of the same name.

**Consequences**
- The name is immediately legible across engine backgrounds and consistent with the specification's existing "reset" vocabulary (`lsn_reset`, HEARTBEAT `sequence_reset`).
- The two same-named fields live in entirely different event types and payload contexts, so a short disambiguation note is sufficient to prevent conflation.

**Alternatives Considered**
- *Use an engine-specific name (for example, one drawn from a single engine's identity-restart syntax).* Rejected: not portable across engines.
- *Introduce a new term such as `identity_action` or `autoincrement_reset`.* Rejected: creates a new vocabulary term for a concept the specification already has a word for.

## ADR-0025 -- Specification scope: govern producer behavior; consumer behavior is non-normative service-level guidance

**Status:** Accepted (supersedes the prior treatment of the Consumer Contract as normative; introduced at v0.6)

**Context**
Through v0.5 the specification stated normative obligations for *both* producers and consumers: a Producer Contract (Section 6) and a parallel Consumer Contract (Section 7), with consumer MUST/MUST NOT rules threaded through the normative summary, the compliance matrix, and several body sections. In practice this overreached. A producer can be held to an objective contract -- the structure, ordering, type fidelity, and lifecycle of the events it emits are observable and testable from the stream. A consumer cannot be held to a single contract, because consumers legitimately operate at different service levels against the *same* conformant stream. A financial replication target needs strict transactionality and exact type fidelity; a reporting tool computing coarse rolling averages may deliberately tolerate gaps and approximate types. Mandating one set of consumer behaviors is therefore both incorrect (it does not describe what real consumers do) and unenforceable (a "consumer conformance" claim has no objective referent without a declared target fidelity). The standard's real guarantee is narrower and stronger: a conformant producer emits a stream that a consumer *can* read and interpret with full fidelity. What the consumer then does with it is the consumer's choice.

**Decision**
Scope the specification to the mandatory and optional behaviors of *producers*. Treat consumer behavior as non-normative. Relocate the consumer obligations to a dedicated appendix (Appendix A: Consumer Conformance, Obligations & Service-Level Guidance), reframed as the behaviors a consumer adopts to achieve a chosen *service level* against a conformant producer, rather than as conformance mandates. Consumer behavior may still appear in the body where it is needed to illustrate how an object or guarantee is intended to be used, but only illustratively. A producer-scope statement is added to Document Authority and Scope; the Normative Summary and Compliance Matrix retain consumer rows for cross-reference but flag them as non-normative and defined in the appendix.

**Consequences**
- The conformance claim becomes objective and testable: "conformant producer" has a precise meaning; consumer behavior is graded by the service level it targets, not by a pass/fail mandate.
- A consumer that wants full fidelity follows the (former) MUST-level obligations now collected in Appendix A; a consumer that accepts a lower service level may relax them and knowingly forfeit the corresponding guarantee.
- The body of the specification stays focused on defining the event stream itself. This decision motivated the v0.6 producer-focused refactor and the creation of this ADR.
- Producer obligations are unaffected -- no producer-facing rule, field, or guarantee changed. The move is a change of normative *authority* over consumers, not of the wire contract.

**Alternatives Considered**
- *Keep a single normative Consumer Contract (the v0.5 model).* Rejected: it implies the standard can dictate consumer processing decisions it cannot observe or enforce, and it misrepresents the legitimate diversity of consumer service levels.
- *Define multiple normative consumer conformance tiers (e.g., "full-fidelity consumer," "lossy consumer") inside the specification.* Rejected for now: it re-imports consumer governance into the normative core and multiplies the conformance surface; the same outcome is achieved more honestly by describing service levels as non-normative guidance in the appendix. Could be revisited if a formal consumer certification program is ever required.
- *Drop consumer guidance entirely.* Rejected: implementers still need to know how to consume a stream at full fidelity; removing the guidance would push that knowledge out-of-band and undermine interoperability. The guidance is retained, just as non-normative service-level advice.

---

OpenCDC Working Group -- Draft for Discussion
