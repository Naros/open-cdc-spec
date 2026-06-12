# OpenCDC Glossary

**Location:** `spec/GLOSSARY.md`
**Status:** Working Group Draft · June 2026
**Role:** Informative reference. Definitions are condensed from normative text in the OpenCDC Specification and Type System Proposal; section references point to the governing normative source. In any conflict between a definition here and the normative text, the normative text prevails.

---

**Change Data Capture (CDC)** — Detecting and delivering row-level changes (inserts, updates, deletes, schema changes) from a database's transaction log as an ordered event stream.

**Producer** — The system emitting OpenCDC events: a CDC tool or a database engine emitting natively. The specification's normative scope governs producer behavior. (Document Authority and Scope; ADR-0025)

**Consumer** — Any system reading an OpenCDC stream. Consumer behavior is non-normative service-level guidance. (Appendix A; ADR-0025)

**Event** — One CloudEvents v1.1 envelope carrying an OpenCDC payload: a DML change, DDL change, schema declaration, or lifecycle signal. (§3)

**Stream** — The ordered sequence of events a producer emits for a set of captured tables. (§6.1)

**Session** — One consumer connection to a producer. Some guarantees (CloudEvents `sequence` monotonicity, STREAM_METADATA) are session-scoped, not stream-scoped. (§8.4.1)

**Wire protocol version** — The version of the event contract itself, carried in every event as `cdcspecversion` / `opencdc_version`; distinct from the specification document revision. Currently `0.2`. (§3.3; versions.yaml)

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

**Partition alignment (`partitionkey`)** — All events of one transaction carry the same `partitionkey` so partitioned transports (e.g., Kafka) preserve transaction ordering. (§3.3; P-ORD-6)

**Sequence (`sequence`)** — Producer-assigned, session-scoped global counter providing total cross-table ordering across all partitions. Gaps are permitted and MUST NOT be interpreted as dropped events. Never derived from source log positions. (§3.3, §8.4; ADR-0016)

**Closed-world schema** — `additionalProperties: false` enforcement: row value objects in DML events may contain only columns declared in the current OBJECT_METADATA schema. Unrecognized fields are a validation failure. (§2.4; ADR-0012)

**LOB overflow (`_lob_overflow`)** — The mechanism that distinguishes a genuinely NULL large-object column (signaled via `_null_columns`) from a LOB column whose content was not captured at the source (signaled via `_lob_overflow`). Both carry `null` in the value payload; the arrays are the only way to tell them apart. (§6.3; P-LOB-1)

**Partial UPDATE image (`changed_columns`)** — An optional array declaring which columns are included in a partial `before`/`after` payload. Columns absent from a partial image MUST be interpreted as unchanged, not null. (§5.4; C-DML-1; ADR-0013)

**Loop suppression** — In bidirectional sync, a producer must never re-emit a change whose `source` field matches its own identity, preventing infinite replication loops. (§3.4; P-LOOP-1; ADR-0014)

**Durable Mode / Ephemeral Mode** — Operational deployment modes. Durable Mode provides replayable delivery with at-least-once guarantees. Ephemeral Mode is transient delivery that accepts data-loss risk. A single producer deployment may serve both simultaneously if it meets the Durable Mode superset obligations. (§15; Appendix A.9)

**Interoperability profile** — The minimum viable conformance subset that all implementations claiming OpenCDC conformance must support. (§2.8)

**Requirements register** — `registry/requirements.yaml`: the working-group data file from which Spec §17 Normative Summary and §19.1 Compliance Matrix are generated. The specification body prose remains the source of truth for requirement semantics; the register is the source of truth for the derived sections. (§17, §19.1)
