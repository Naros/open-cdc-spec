# OpenCDC Glossary

**Location:** `spec/GLOSSARY.md`
**Status:** Working Group Draft v1.1 · August 2026 (aligned to Specification v0.7.0, wire 0.3)
**Role:** Informative reference. Definitions are condensed from normative text in the OpenCDC Specification and Type System Proposal; section references point to the governing normative source. In any conflict between a definition here and the normative text, the normative text prevails.

---

**Change Data Capture (CDC)** — Detecting and delivering row-level changes (inserts, updates, deletes, schema changes) from a database's transaction log as an ordered event stream.

**Producer** — The system emitting OpenCDC events: a CDC tool or a database engine emitting natively. The specification's normative scope governs producer behavior. (Document Authority and Scope; ADR-0025)

**Consumer** — Any system reading an OpenCDC stream. Consumer behavior is non-normative service-level guidance. (Appendix A; ADR-0025)

**Delivery layer** — The transport, broker, or intermediary between a producer's emission point and a consumer's point of consumption. Not a conformance party of this core specification: delivery semantics are the province of future transport binding profiles (§12). Two body rules (R-POS-7, P-RET-1) are labelled "Delivery-layer obligation (binding-defined)" and are chartered for inheritance by binding profiles rather than enforced by the core. (Terms and Definitions; §12; ADR-0034)

**Emission schema** — The `columns[]` descriptor set declared in the most recent OBJECT_METADATA event for a table. It governs the shape and typing of that table's DML payloads and describes what the producer *emits*, which may differ from the source catalog after column filtering, masking, or type mapping. Any change to it triggers a new OBJECT_METADATA before the next DML. (§4.1, §4.2; ADR-0030)

**Bidirectional pair** — Two deployments, each declaring `bidirectional: true`, exchanging changes with one another. The axis declares participation in a pair, not membership in a larger topology; acyclic chains compose from conformant legs, while cyclic and multi-path topologies are deferred. (Terms and Definitions, §3.4; ADR-0028)

**Ingress counterpart** — For an applied change, the counterpart it was received from, recorded in the apply-time mark. Loop suppression keys on this, not on the change's original origin, which continues to travel in `source` for provenance. (§3.4, P-LOOP-1; ADR-0028)

**`ddl_capture`** — Capability axis declaring whether source DDL operations affecting captured tables are surfaced as DDL events, and whether statement text is verbatim: `"verbatim"`, `"structural"`, or `"none"` (absent = `"none"`). Source-ceilinged and deployment-determined. It never affects the OBJECT_METADATA obligation. (§2.2a, §9; ADR-0030)

**`cdcschemauri`** — OPTIONAL extension attribute carrying a resolvable URI to an external schema registry. Mandatory on DML and DDL events when `schema_by_reference` is active (P-SCHEMA-6). Supplemental only: schema identity is always the `dataschema` OBJECT_METADATA id. (§3.3, §4.5.4; ADR-0029)

**Event** — One CloudEvents v1.1 envelope carrying an OpenCDC payload: a DML change, DDL change, schema declaration, or lifecycle signal. (§3)

**Stream** — The ordered sequence of events a producer emits for a set of captured tables. (§6.1)

**Session** — One consumer connection to a producer. Some guarantees (CloudEvents `sequence` monotonicity, STREAM_METADATA) are session-scoped, not stream-scoped. (§8.4.1)

**Wire protocol version** — The version of the event contract itself, carried in every event as `cdcspecversion` / `opencdc_version`; distinct from the specification document revision. Currently `0.3`. (§3.3; Terms and Definitions; versions.yaml)

**DML event** — INSERT, UPDATE, DELETE, UPSERT, or TRUNCATE: a data change to one table. One DML event maps to exactly one table. (§3.2, §5)

**DDL event** — A schema change (CREATE, ALTER, DROP), emitted as a first-class event in the same ordered stream as data events. (§2.5, §9)

**OBJECT_METADATA** — The schema-declaration event for a table: column descriptors, primary key, and JSON Schema. Must precede the table's first DML event and follow any structural DDL event. (§4.2; ADR-0007)

**STREAM_METADATA** — Session-scoped opening event declaring producer identity, captured tables, schema delivery modes, and sequence continuity. Not part of durable stream ordering. (§10.4)

**HEARTBEAT** — Periodic liveness event emitted during idle periods; also signals mid-session LSN or sequence discontinuities. Consumers use it to distinguish a quiet stream from a broken one. (§10.1, §8.4.2; C-HB-1)

**Schema-before-first-use** — The mandatory baseline: a consumer always receives a table's OBJECT_METADATA schema before any DML events for that table. (§4.1; ADR-0002)

**Schema delivery modes** — The four named producer behaviors governing when OBJECT_METADATA is emitted: Schema on Change (mandatory), Schema on Reconnect, Schema on Each Event, and Schema by Reference. (§4.4; ADR-0003)

**Two-layer type system** — Every column descriptor carries `source_type` (verbatim source DDL declaration, never normalized) and `logical_type` (canonical OpenCDC vocabulary, authoritative for decoding). (Type System §5; ADR-0007)

**source_type** — The verbatim DDL type declaration from the source engine (e.g., `NUMBER(19,0)`, `VARCHAR2(200 BYTE)`). Preserved for passthrough; never normalized or aliased. (Type System §5.2; P-TYPE-1)

**logical_type** — The canonical OpenCDC type name from the standard vocabulary (e.g., `DECIMAL`, `STRING`, `ORACLE_DATE`). Authoritative for wire encoding and consumer decoding. (Type System §5.3; C-TYPE-1)

**Transaction identity (`cdcxid`)** — Envelope attribute shared by all events belonging to one source transaction. Combined with `cdctxorder` (0-based ordinal within the transaction), it defines intra-transaction ordering. (§3.3, §8.3)

**Synthetic cdcxid** — A producer-assigned transaction identifier for operations with no real source transaction (e.g., Oracle and MySQL TRUNCATE); must be unique, replay-stable, and documented. (§10.2.2; P-TRUNC-3)

**Transaction ordering (`cdctxorder`)** — 0-based integer ordinal of an event within its transaction. Gaps in `cdctxorder` within a transaction are a producer conformance violation. (§3.3; P-ORD-3)

**Position (`cdcpos` / `pos`)** — `cdcpos` is the opaque, authoritative resume handle on the CloudEvents envelope. The payload `pos` object (`lsn`, `lsn_offset`, `source_timestamp`) is the structured equivalent for consumer-side ordering logic and gap detection. (§8.1; R-POS-3)

**LSN (Log Sequence Number)** — Source-engine position in the transaction log. Carried in `pos.lsn`. Not comparable across sessions when `sequence_continuity` is `reset` or `best_effort`. (§8.1, §8.4.1)

**Replay** — Re-delivery of events from a saved `cdcpos` position, in original order, with original event IDs. At-least-once delivery is the minimum guarantee; duplicate events may occur and consumers must deduplicate. (§8.2; R-POS-5)

**Deduplication key** — The pair `(source, id)` used by consumers to identify and discard replay duplicates. (§11.1; C-IDEM-1)

**Partition alignment (`partitionkey`)** — Advisory routing hint: events of one transaction SHOULD share the same `partitionkey` as a convenience for partitioned transports. Not the ordering anchor -- ordering rests on T-NOINTERLEAVE and the CloudEvents `sequence` field, and consumers key on `primary_key` (C-KEY-1). (§3.3; P-ORD-6, SHOULD)

**Sequence (`sequence`)** — Producer-assigned, session-scoped monotonic counter. Yields cross-transaction total order only where `ordering_scope: "stream"` is declared and the consumer receives the stream as one ordered channel; comparable within a session, but not a consumable total order across channels read independently. Gaps are permitted and are not evidence of dropped events. Never derived from source log positions. (§3.3, §8.2 R-POS-0, §8.4; ADR-0016)

**Closed-world schema** — `additionalProperties: false` enforcement: row value objects in DML events may contain only columns declared in the current OBJECT_METADATA schema. Unrecognized fields are a validation failure. (§2.4; ADR-0012)

**LOB overflow (`_lob_overflow`)** — The mechanism that distinguishes a genuinely NULL large-object column (signaled via `_null_columns`) from a LOB column whose content was not captured at the source (signaled via `_lob_overflow`). Both carry `null` in the value payload; the arrays are the only way to tell them apart. (§6.3; P-LOB-1)

**Partial UPDATE image (`changed_columns`)** — An optional array declaring which columns are included in a partial `before`/`after` payload. Columns absent from a partial image MUST be interpreted as unchanged, not null. (§5.4; C-DML-1; ADR-0013)

**Loop suppression** — In bidirectional sync, a producer never re-emits an applied change toward the ingress counterpart recovered from the apply-time mark, and never emits a marked change whose recorded original origin is this deployment; native unmarked changes are unaffected. Keyed on the ingress counterpart, not the change's original origin, which continues to travel in `source` for provenance. (§3.4; P-LOOP-1; ADR-0028)

**Durable Mode / Ephemeral Mode** — Operational deployment modes. Durable Mode provides replayable delivery with at-least-once guarantees. Ephemeral Mode is transient delivery that accepts data-loss risk. A single producer deployment may serve both simultaneously if it meets the Durable Mode superset obligations. (§15; Appendix A.9)

**Interoperability profile** — The minimum viable conformance subset that all implementations claiming OpenCDC conformance must support. (§2.8)

**`ordering_scope`** — Capability axis (`"stream"` | `"channel"`): whether the producer emits one totally ordered sequence or several independently ordered emission channels. MUST be declared; conservative value is `"channel"`. Governs the comparison domain only, never marker obligations. (§2.2a, §10.4; P-SCOPE-1/2)

**`transaction_interleaving`** — Capability axis (`"none"` | `"possible"`): whether events of different transactions can arrive interspersed. MUST be declared; conservative value is `"possible"`. Governs the completion strategy (§8.3) and the TRX_COMMIT obligation. (§2.2a, §10.4; P-ILV-1/2; ADR-0032)

**`transaction_boundaries`** — Completion-marker mode (`"none"` | `"commit_all"` | `"commit_multi_event"`; absent = `"none"`). `"none"` is legal only under `transaction_interleaving: "none"`; under `"possible"` the value MUST be `"commit_all"` (P-TRX-1). `"commit_multi_event"` marks only transactions with two or more events and is valid only under `"none"`. (§10.4, §10.5)

**`transaction_marker_delivery`** — Where TRX_COMMIT markers are delivered (`"transaction_metadata_channel"` | `"per_channel"`), declared when `transaction_interleaving: "possible"`. The marker is an in-band logical event; physical transport coordinates are never embedded. (§10.4, §10.5)

**`transaction_visibility`** — Declared stream visibility; `"committed_only"` is the only value defined in this revision and the default when absent (P-TRX-6). The value space is reserved fail-closed: consumers treat unrecognized values per C-TRX-1. (§10.4, §2.2a)

**TRX_COMMIT** — Lifecycle event (`meta.TRX_COMMIT`) giving a deterministic transaction-completeness signal: `event_count` counts the distinct `cdctxorder` ordinals of DML and DDL events; the optional `distribution` map gives per-table counts. Mandatory when `transaction_interleaving: "possible"` is declared, optional (and recommended for payload-only producers, P-TRX-7) otherwise. Carries `cdcxid` but never `cdctxorder`. (§10.5; P-TRX-1..4; R-POS-6)

**Emission channel / delivery channel** — The two layers of "channel": emission channels are the ordered sequences the producer generates (declared via `ordering_scope`); delivery channels are the transport's units of ordered delivery. The axes describe emission; what survives delivery is a binding-profile question. (Terms and Definitions; §2.2a)

**Incarnation** — A subject's lifetime between CREATE and DROP. Re-creation of a dropped subject starts a new incarnation: the producer emits new OBJECT_METADATA with `schema_version` above the prior maximum even when the column descriptors are byte-identical. (§4.2)

**Forward reference (`dataschema`)** — The one case in which `dataschema` names an event the consumer has not yet received: a `ddl.CREATE` for a subject with no governing schema carries the id of the next OBJECT_METADATA the producer will emit for that subject. (§9.1)

**Scope of Declarations** — The normative statement that the capability axes declare what the producer's emitted sequence guarantees -- no more and no less; the core makes no claims about the stream as delivered. Conservative-consumption guidance for consumers is C-COMP-1 (SHOULD, Appendix A.1). (§2.2a; ADR-0034)

**Requirements register** — `registry/requirements.yaml`: the working-group data file from which Spec §17 Normative Summary and §19.1 Compliance Matrix are generated. The specification body prose remains the source of truth for requirement semantics; the register is the source of truth for the derived sections. (§17, §19.1)
