OpenCDC Specification -- Type System Proposal -- Draft v0.1

# OpenCDC Specification

# Type System Proposal

Payload Type System Design -- Draft v0.2

May 2026 -- CDC-OIS Working Group

# Change Log

- **v0.1**
  - Date: May 2026
  - Changes: Initial draft. Two-layer type system, canonical vocabulary, four normative rules, five engine wire format examples.

- **v0.2**
  - Date: May 2026
  - Changes: Added Section 4: Schema Delivery Model. Adopted schema-before-first-use as the single mandatory baseline. Defined producer obligations for consumer reconnection (Approach 1) and position-based replay (Approach 2). Updated column descriptor structure to separate schema-time metadata from per-event value encoding. Updated all wire format examples to reflect schema/value separation. Resolved Open Question Q1 (MySQL TIMESTAMP). Updated Open Questions section.

# Abstract

This proposal defines the type system for the OpenCDC (Open Change Data Capture) payload specification. It addresses the core challenge of representing data values from five heterogeneous relational database engines -- Oracle 23ai, PostgreSQL 17, MySQL 9, SQL Server 2022, and IBM Db2 LUW 12.1 -- in a single CDC event stream without silent precision loss, semantic reinterpretation, or undetectable data gaps.

The proposal adopts a two-layer design: a verbatim source_type field that carries the exact DDL declaration from the originating engine, and a logical_type field drawn from a controlled canonical vocabulary of approximately 60 named types. Wire encoding rules are specified for each logical type. Four normative rules govern all conforming implementations: no silent truncation, no semantic reinterpretation, distinguishable null versus uncaptured LOB values, and preserved timezone offsets.

Schema delivery follows the schema-before-first-use model: a complete column descriptor block (the OBJECT_METADATA event) is emitted once per table before any DML events for that table, and re-emitted after any DDL change. Per-event value payloads carry data values only -- column names as keys, wire-encoded values as values -- with no type metadata repeated. Two producer behaviors are defined for consumer reconnection: schema re-emission on new connection, and schema availability within the position-based replay window.

The canonical vocabulary is explicitly inspired by Apache Arrow's type system, with extensions to cover temporal precision, engine-specific types, spatial geometry, vector embeddings, and CDC-specific edge cases that Arrow does not address.

# 1. Problem Statement

A CDC event stream that originates from a heterogeneous database environment must carry data values from source engines whose type systems differ in fundamental and often incompatible ways. The CDC-OIS Data Type Survey (March 2026) documents these differences across Oracle 23ai, PostgreSQL 17, MySQL 9, SQL Server 2022, and IBM Db2 LUW 12.1. The survey identifies five categories of cross-engine incompatibility that any type system must address:

## 1.1 Semantic Divergence -- Same Name, Different Meaning

The most dangerous incompatibilities are cases where an identical type name carries different semantics in different engines. An implementation that maps type names naively will produce silent data corruption.

- **DATE**
  - Engine: Oracle 23ai
  - Actual Semantics: Stores year, month, day, HOUR, MINUTE, SECOND
  - Risk: Mapping to any other engine's DATE silently drops the time component

- **DATE**
  - Engine: All others
  - Actual Semantics: Calendar date only -- no time stored
  - Risk: Receiving an Oracle DATE and treating it as date-only causes silent data loss

- **FLOAT**
  - Engine: Oracle
  - Actual Semantics: Binary precision alias to NUMBER -- NOT IEEE 754
  - Risk: Consumers expecting IEEE 754 float receive exact decimal semantics

- **FLOAT**
  - Engine: MySQL
  - Actual Semantics: IEEE 754 single if precision <= 24; double if > 24
  - Risk: Same keyword, different width depending on precision parameter

- **TIMESTAMP**
  - Engine: MySQL
  - Actual Semantics: Stored as UTC; auto-updates on row modification
  - Risk: Wire value is identical to DATETIME but semantics differ entirely

- **TIMESTAMP**
  - Engine: All others
  - Actual Semantics: Point in time, no auto-update
  - Risk: Consumers cannot distinguish from MySQL DATETIME without metadata

- **BIT**
  - Engine: SQL Server
  - Actual Semantics: Boolean 0/1 -- not a bit string
  - Risk: PostgreSQL BIT(n) is a true bit string -- completely different type

- **NUMBER**
  - Engine: Oracle
  - Actual Semantics: Universal exact numeric -- covers integers AND decimals
  - Risk: Consumers may assume fixed precision; Oracle NUMBER has flexible scale including negative

## 1.2 Precision and Range Incompatibility

Several type characteristics exist in one engine at a precision or range that no other engine can represent natively. A CDC stream must carry these values without loss, even when the target engine cannot store them at full precision. The consumer -- not the transport layer -- must decide how to handle the mismatch.

- **PostgreSQL 17 -- NUMERIC**
  - Capability: Precision up to 1,000 digits
  - Other Engines: Oracle/SQL Server: max 38; DB2: max 31. Values with >31 significant digits cannot be stored in DB2 targets without truncation

- **Oracle 23ai -- NUMBER(p,s)**
  - Capability: Negative scale supported (s = -84 to 127)
  - Other Engines: No other engine supports negative scale. NUMBER(10,-2) rounds to nearest 100

- **Oracle 23ai -- TIMESTAMP(9)**
  - Capability: Nanosecond precision (9 fractional digits)
  - Other Engines: PostgreSQL/MySQL: microseconds (6). SQL Server: 100-nanoseconds (7). Truncation required for most targets

- **IBM Db2 LUW -- DECFLOAT(34)**
  - Capability: IEEE 754-2008 decimal float, 34 significant digits
  - Other Engines: No equivalent in any other engine. AWS DMS explicitly does not support CDC of this type

- **MySQL 9 -- BIGINT UNSIGNED**
  - Capability: Range 0 to 18.4x10^18
  - Other Engines: Exceeds signed BIGINT max (9.2x10^18). Cannot be stored as BIGINT in any other engine without overflow risk

## 1.3 Engine-Unique Types With No Cross-Engine Equivalent

A substantial number of types exist in only one engine and have no structural equivalent elsewhere. The type system must name and encode these types consistently so that downstream consumers can at minimum preserve the value as a string even if they cannot natively process the type.

- **INTERVAL YEAR TO MONTH / INTERVAL DAY TO SECOND**
  - Engine: Oracle, PostgreSQL
  - Nature: Native SQL duration types
  - CDC Challenge: MySQL, SQL Server, DB2 have no interval type. Must serialize as ISO 8601 duration strings

- **DECFLOAT(16/34)**
  - Engine: IBM Db2 LUW
  - Nature: IEEE 754-2008 decimal floating point
  - CDC Challenge: No equivalent anywhere. Cannot be represented as IEEE 754 binary float without approximation

- **tsvector / tsquery**
  - Engine: PostgreSQL
  - Nature: Full-text search document and query types
  - CDC Challenge: Pre-tokenized representation is PostgreSQL-specific; no reconstruction possible

- **Arrays (any type)**
  - Engine: PostgreSQL
  - Nature: Native typed arrays of any base type
  - CDC Challenge: No structural equivalent in other engines; must serialize as JSON arrays

- **Range types**
  - Engine: PostgreSQL
  - Nature: Typed intervals with inclusive/exclusive bounds
  - CDC Challenge: Unique to PostgreSQL; serialize as JSON objects with bound metadata

- **sql_variant**
  - Engine: SQL Server
  - Nature: Self-describing heterogeneous container
  - CDC Challenge: Must carry both base type and value; consumers need special handling

- **hierarchyid**
  - Engine: SQL Server
  - Nature: Variable-length hierarchy position type
  - CDC Challenge: No equivalent; serialize as path string notation

- **BFILE**
  - Engine: Oracle
  - Nature: External file pointer -- content not in database
  - CDC Challenge: Content is never in the transaction log; cannot be captured by any CDC tool

- **SDO_GEOMETRY**
  - Engine: Oracle
  - Nature: Oracle Spatial -- proprietary encoding
  - CDC Challenge: Must convert to standard WKT/EWKT for cross-engine portability

## 1.4 LOB Capture Ambiguity

Large Object (LOB) columns present a universal challenge across all five engines. In many CDC configurations, the LOB content is not written to the transaction log. The CDC tool must perform a supplemental read to fetch the LOB value -- and if the row has since been deleted or the LOB modified, the content may not be recoverable.

**Critical Ambiguity**
A null LOB value and an uncaptured LOB value are not the same thing. In existing CDC implementations, both typically appear as null in the event payload. A consumer that receives a null for a LOB column cannot determine whether the source column was actually null or whether the LOB content was simply not captured. This is silent data loss. The OpenCDC type system must define a distinct representation for the "LOB not captured" state that is unambiguous from a genuine null value.

## 1.5 Wire Encoding Edge Cases

Several types present specific wire encoding challenges that a type system must resolve explicitly:

- JSON number precision: IEEE 754 double precision cannot exactly represent integers larger than 2^53 (approximately 9 quadrillion). MySQL UNSIGNED BIGINT values above this threshold must not be encoded as JSON numbers.

- SQL Server UNIQUEIDENTIFIER uses non-RFC 4122 byte ordering for the first three UUID components (little-endian). The same GUID stored in SQL Server and PostgreSQL displays as different strings if bytes are compared directly.

- JSON column values in CDC events create a double-serialization problem: the JSON document must be embedded as an escaped string inside the CDC event JSON payload, not as a nested object, to avoid ambiguity between the column value and the event structure.

- Spatial type binary encodings (WKB) differ between PostGIS (EWKB with embedded SRID) and Oracle SDO_GEOMETRY (proprietary serialization). A common text encoding is required.

# 2. Design Principles

The following principles govern every decision in this proposal. They are listed in priority order; when principles conflict, the higher-ranked principle takes precedence.

## Principle 1: Lossless Carry, Not Lossless Conversion

OpenCDC's responsibility is to carry data values with full source fidelity so that downstream consumers can make informed decisions. It is not OpenCDC's responsibility to convert types across engines. Silent truncation, silent precision loss, and silent semantic reinterpretation are the primary failure modes this specification exists to prevent.

A consumer that cannot represent a value at full source precision must emit an explicit error or warning. It must not silently round, truncate, or reinterpret.

## Principle 2: Two Layers -- Source Fidelity and Canonical Interoperability

The type system uses two distinct fields in every column descriptor, both of which reside in the schema (OBJECT_METADATA event) rather than repeating per row event:

- source_type carries the verbatim DDL type declaration from the originating engine. It is never interpreted or normalized by the CDC tool. It exists so that consumers with knowledge of the source engine can reconstruct exact type semantics.

- logical_type carries a named type from the OpenCDC canonical vocabulary. It exists so that consumers can implement type-based routing, validation, and mapping without parsing engine-specific DDL strings.

Both fields are mandatory in every column descriptor in the schema. They serve different audiences and neither replaces the other. Neither field repeats in per-row DML value payloads -- that is the purpose of the schema delivery model.

## Principle 3: Named Types for All Engine-Specific Behaviors

Every type behavior that differs across engines must have a distinct named logical type in the canonical vocabulary. This is why the vocabulary includes ORACLE_DATE as a distinct type from DATE, GUID as distinct from UUID, BIT as distinct from BOOLEAN, and TINYINT1 as distinct from either. A consumer that receives a logical_type of ORACLE_DATE must treat it as a datetime value regardless of whether the consuming engine has a DATE type.

## Principle 4: String Encoding for Exact Numeric Values

JSON number encoding cannot guarantee exact representation of arbitrary-precision decimal values, IEEE 754 special values (NaN, Infinity), or large unsigned integers. The canonical wire encoding for all exact numeric types (DECIMAL, ORACLE_NUMBER, DECFLOAT) is an exact decimal string. This is a deliberate tradeoff of wire compactness for correctness. For a CDC specification where data integrity is the primary concern, this is the correct tradeoff.

# 3. Why Apache Arrow -- Rationale and Limitations

The canonical type vocabulary is explicitly inspired by Apache Arrow's type system. This section explains the reasoning and the specific areas where this proposal diverges from or extends Arrow.

## 3.1 What Arrow Gets Right

- **Decimal128 and Decimal256 as distinct types**
  - Relevance to OpenCDC: Naturally maps to the real precision split: most engines max at 38 digits (fits Decimal128); PostgreSQL NUMERIC supports up to 1,000 (requires Decimal256)

- **Timestamp includes timezone as a type parameter, not a separate type**
  - Relevance to OpenCDC: Eliminates the need for separate TIMESTAMP and TIMESTAMPTZ types; the parameter carries whether timezone offset is present

- **Duration as a first-class type (separate from Timestamp)**
  - Relevance to OpenCDC: Directly maps to Oracle and PostgreSQL INTERVAL types; avoids forcing intervals into string representations without a named type

- **Float16, Float32, Float64 as distinct named types**
  - Relevance to OpenCDC: Clearer than SQL FLOAT(p) which means different things in different engines; makes wire encoding rules unambiguous

- **Large variants for string and binary (LargeUtf8, LargeBinary)**
  - Relevance to OpenCDC: Maps to the LOB type category -- CLOB, BLOB, TEXT, BYTEA -- where sizes exceed inline representation limits

- **List type for variable-length arrays of any base type**
  - Relevance to OpenCDC: Directly applicable to PostgreSQL native array types (int[], text[], jsonb[], etc.)

- **Struct type for composite / nested record types**
  - Relevance to OpenCDC: Applicable to PostgreSQL composite types and Oracle ANYDATA

- **Union type for heterogeneous containers**
  - Relevance to OpenCDC: Applicable to SQL Server sql_variant and Oracle ANYDATA which can hold different types in different rows

## 3.2 Where Arrow Is Insufficient for CDC

- **Oracle DATE semantic divergence**
  - Arrow Behavior: Arrow has no mechanism to flag that a Date32 value also carries time components
  - OpenCDC Extension Required: ORACLE_DATE as a distinct logical type that mandates datetime wire encoding

- **Timezone offset preservation**
  - Arrow Behavior: Arrow Timestamp with timezone normalizes to UTC
  - OpenCDC Extension Required: OpenCDC TIMESTAMP_TZ preserves the original offset. UTC normalization is a consumer decision

- **LOB capture ambiguity**
  - Arrow Behavior: Arrow has no concept of "value not captured" as distinct from null
  - OpenCDC Extension Required: lob_overflow flag in schema column descriptor; EXTERNAL_REF type for Oracle BFILE

- **DB2 DECFLOAT**
  - Arrow Behavior: Arrow has no decimal floating point type (IEEE 754-2008)
  - OpenCDC Extension Required: DECFLOAT16 and DECFLOAT34 as distinct logical types with string wire encoding

- **MySQL TIME > 24 hours**
  - Arrow Behavior: Arrow Time32/Time64 represents time-of-day only
  - OpenCDC Extension Required: OpenCDC TIME carries elapsed-time values as ISO 8601 strings when value exceeds day boundary

- **Vector types (AI embeddings)**
  - Arrow Behavior: Arrow does not define a VECTOR type (FixedSizeList is used in practice)
  - OpenCDC Extension Required: VECTOR logical type with explicit dimension count and element_type parameter

- **SQL Server GUID byte order**
  - Arrow Behavior: Arrow UUID follows RFC 4122
  - OpenCDC Extension Required: GUID as distinct from UUID -- different byte order in first three components

- **PostgreSQL range types**
  - Arrow Behavior: Arrow has no range type with bound semantics
  - OpenCDC Extension Required: RANGE logical type with lower/upper/bounds JSON object encoding

- **Spatial geometry**
  - Arrow Behavior: Arrow does not define a geometry type (WKB used in practice)
  - OpenCDC Extension Required: GEOMETRY logical type with EWKT string wire encoding and SRID parameter

## 3.3 What This Proposal Takes Directly from Arrow

- Decimal128 and Decimal256 with precision and scale parameters for exact numeric types

- Float32 and Float64 for IEEE 754 binary floating point

- The treatment of NaN, Infinity, and -Infinity as string sentinels rather than omissions

- Duration (INTERVAL_YM and INTERVAL_DS in this proposal) as a named first-class type

- List (ARRAY in this proposal) for typed variable-length arrays

- Struct (COMPOSITE in this proposal) for named field composite types

- Union-style handling for self-describing containers (SQL_VARIANT, ANYDATA)

- LargeUtf8 / LargeBinary as the model for LOB types (STRING_LOB, BYTES_LOB)

## 3.4 Why Not Avro, Protobuf, or Parquet?

- **Apache Avro**
  - Primary Limitation: The base type system is insufficient for this use case. Avro's logicalType extension system requires every implementation to define its own extension vocabulary -- which is exactly what this proposal is doing, so Avro adds a serialization layer without providing a type vocabulary. The schema registry model also creates schema evolution complexity unnecessary for a streaming CDC event format.

- **Protocol Buffers**
  - Primary Limitation: No decimal type. google.protobuf.Timestamp normalizes to UTC, destroying timezone offsets. No interval, no geometry, no UUID distinct from string. Custom types require schema distribution infrastructure.

- **Apache Parquet**
  - Primary Limitation: Parquet is a columnar file format, not an event format. Its logical type system has the same gaps as Avro. Parquet is the wrong unit of processing for row-level CDC events.

- **JSON Schema**
  - Primary Limitation: JSON Schema describes structure but does not define a type vocabulary with wire encoding rules. It cannot represent the distinction between Oracle DATE and calendar DATE, or the difference between a JSON null and a LOB overflow, without custom extensions equivalent in scope to this proposal.

# 4. Schema Delivery Model

This section defines how column descriptor metadata -- source_type, logical_type, parameters, and nullability -- travels in the stream relative to data values. This is a foundational architectural decision that determines wire efficiency, consumer complexity, and stream independence.

## 4.1 Adopted Model: Schema-Before-First-Use

CDC-OIS adopts schema-before-first-use as the single mandatory baseline for schema delivery. Under this model:

- A complete OBJECT_METADATA event carrying the full column descriptor block for a table MUST be emitted in the stream before any DML event for that table.

- The OBJECT_METADATA event MUST be re-emitted after any DDL event that changes the structure of a table, and before the first DML event for that table under the new structure.

- DML event value payloads carry data values only -- column names as keys, wire-encoded values as values. Type metadata (source_type, logical_type, parameters) does NOT repeat per row.

- A DML event's dataschema field references the CloudEvents id of the most recently emitted OBJECT_METADATA event for its table. This reference is the normative link between a value payload and its schema.

**Why Schema-Before-First-Use?**
This model matches the two most successful CDC implementations (GoldenGate Data Streams and the GoldenGate-derived CDC-OIS baseline) and is immediately familiar to any engineer who has worked with either. It amortizes schema cost to the minimum necessary: paid once per table, then again only when the schema actually changes -- which is the DDL event, a precisely defined trigger. The alternative of schema-per-row (Debezium's default) repeats type metadata on every event. For a table with 20 columns receiving 10,000 inserts in a single session, schema-per-row emits the column descriptor block 10,000 times. Schema-before-first-use emits it once. The wire efficiency gain is O(rows x columns) reduced to O(columns). Schema-per-transaction was also evaluated. It reduces redundancy further for multi-row transactions, but requires a transaction envelope structure that adds producer complexity. Schema-before-first-use achieves equivalent efficiency in high-volume single-table workloads -- the dominant CDC pattern -- with substantially simpler producer implementation.

## 4.2 Stream Ordering Guarantee -- Normative Rule

The following stream ordering constraint is a MUST requirement for all conforming producers. It is the load-bearing guarantee that makes schema-before-first-use watertight:

```
MANDATORY STREAM ORDERING:
  [1]  OBJECT_METADATA  id:"schema-ORDERS-v1"     <- MUST precede first DML
  [2]  INSERT           dataschema:"schema-ORDERS-v1"
  [3]  UPDATE           dataschema:"schema-ORDERS-v1"
  [4]  INSERT           dataschema:"schema-ORDERS-v1"
  [5]  DDL ALTER        (adds TRACKING_CODE column)
  [6]  OBJECT_METADATA  id:"schema-ORDERS-v2"     <- MUST precede first DML after DDL
  [7]  INSERT           dataschema:"schema-ORDERS-v2"
  [8]  HEARTBEAT        (no schema ref required)
VIOLATION: emitting [7] before [6] is a conformance failure.
VIOLATION: emitting [2] before [1] is a conformance failure.
```

**DDL Is the Sole Schema Invalidation Trigger**
A producer MUST re-emit an OBJECT_METADATA event if and only if a DDL event changes the structure of the table. Time elapsed, consumer reconnection, and high event volume are NOT triggers for schema re-emission in the stream itself. Schema re-emission on consumer reconnection is a separate producer behavior defined in Section 4.3 and does not affect in-stream ordering.

## 4.3 Producer Obligations for Consumer Reconnection

A consumer that connects or reconnects to a live stream may do so at a position where OBJECT_METADATA events for active tables were emitted before the connection began. The producer MUST support at least one of the two following behaviors. Both are RECOMMENDED; Approach 1 MUST be the fallback if Approach 2 is not implemented.

### Approach 1 -- Schema Re-Emission on Connection (Required Baseline)

When a new consumer connection is established -- whether an initial connection or a reconnect -- the producer MUST emit current OBJECT_METADATA events for all tables that are active in the stream before resuming data delivery from the requested start position.

```
Consumer connects with begin position P (may be "now", "earliest", or a saved LSN):
  Producer sends:
  [A]  OBJECT_METADATA  id:"schema-ORDERS-v2"      <- current schema for ORDERS
  [B]  OBJECT_METADATA  id:"schema-PRODUCTS-v1"    <- current schema for PRODUCTS
  [C]  OBJECT_METADATA  id:"schema-AUDIT_LOG-v3"   <- current schema for AUDIT_LOG
  ... then resumes stream from position P:
  [D]  INSERT  table:ORDERS  dataschema:"schema-ORDERS-v2"
  [E]  UPDATE  table:PRODUCTS  dataschema:"schema-PRODUCTS-v1"
  ...
The consumer has a complete, current schema for every table before receiving any data
event, regardless of where in the stream it connects.
```

Key properties of Approach 1:

- The consumer never receives a DML event for a table whose schema it has not seen in this session.

- The re-emitted OBJECT_METADATA events are NOT inserted into the durable stream -- they are session-scoped, sent only to the connecting consumer. The durable stream ordering is unaffected.

- The producer maintains a current schema registry per table (in memory or persistent). This is a producer-side concern; consumers have no dependency on external registries.

- If a table's schema has changed since a consumer's last connection, the consumer receives the current schema version. It can detect the schema change by comparing the schema id against its last known schema id for that table.

### Approach 2 -- Schema Availability Within Replay Window (Recommended Enhancement)

When a consumer resumes from a saved stream position (LSN + sequence), the producer MUST guarantee that replaying from that position will include the OBJECT_METADATA event that was current for each table at that position. Specifically: the replay window for a given position MUST begin at or before the most recent OBJECT_METADATA event for each table that was current at that position.

```
Consumer saved position P after processing event [4] in this stream:
  [1]  OBJECT_METADATA  id:"schema-ORDERS-v1"
  [2]  INSERT  dataschema:"schema-ORDERS-v1"
  [3]  UPDATE  dataschema:"schema-ORDERS-v1"
  [4]  INSERT  dataschema:"schema-ORDERS-v1"   <- consumer saved position here
  [5]  UPDATE  dataschema:"schema-ORDERS-v1"
  ...
Consumer reconnects with resume position P. Producer MUST replay starting from at most
event [1], NOT from [4]:
  Correct:   replay begins at [1] -> consumer receives schema before data
  Incorrect: replay begins at [4] -> consumer receives data without schema
The producer scans back from position P to find the most recent OBJECT_METADATA for
each in-scope table, and begins replay there.
```

Key properties of Approach 2:

- The consumer's saved position remains the logical resume point for data delivery. The schema scan-back is transparent -- the consumer simply receives the schema before its first data event, as in any fresh connection.

- This approach requires the producer to index or scan the durable stream to locate OBJECT_METADATA events preceding a given position. For trail-based CDC implementations (GoldenGate, log-mining), this is a trail position lookup. For Kafka-based implementations, this may require topic scan-back or a separate schema topic.

- Approach 2 is more efficient than Approach 1 for consumers with very large numbers of active tables, because only the schemas relevant to the replay window need to be identified rather than all active tables.

- Approach 2 MUST be combined with Approach 1 for initial connections (no saved position), since there is no position from which to scan back.

**Combining Both Approaches**
The recommended producer implementation supports both approaches simultaneously:

Initial connection (no saved position): use Approach 1 -- emit all current schemas before resuming from "now" or "earliest".

Resume from saved position: use Approach 2 -- scan back to the most recent OBJECT_METADATA for each in-scope table, replay from there. This combination ensures that every consumer, in every connection scenario, receives a complete and current schema before its first data event -- with no external registry dependency and no consumer-side schema management burden.

## 4.4 OBJECT_METADATA Event Structure

The OBJECT_METADATA event is the authoritative schema carrier. Its column descriptor array is the source for all type metadata that DML value payloads reference but do not repeat. The following structure is normative:

```
{
  // CloudEvents envelope
  "specversion":    "1.1",
  "id":             "schema-ORDERS-v2",           // referenced by DML dataschema field
  "source":         "//oracle-prod/ORCL/FINANCE",
  "subject":        "FINANCE.ORDERS",
  "type":           "com.acme.cdc.meta.OBJECT_METADATA",
  "time":           "2026-03-22T14:00:00.000Z",
  "datacontenttype":"application/json",
  "cdcspecversion": "1.0",
  // CDC-OIS payload
  "data": {
    "table": { "catalog": "ORCL", "schema": "FINANCE", "name": "ORDERS" },
    "schema_version": 2,                         // increments on each DDL change
    "primary_key": ["ORDER_ID"],
    "columns": [
      {
        "name":         "ORDER_ID",
        "ordinal":      1,                       // 1-based column position
        "source_type":  "NUMBER(10,0)",          // verbatim DDL -- never normalized
        "logical_type": "DECIMAL",               // from OpenCDC canonical vocabulary
        "parameters":   { "precision": 10, "scale": 0 },
        "nullable":     false,
        "pk":           true
      },
      {
        "name":         "STATUS",
        "ordinal":      2,
        "source_type":  "VARCHAR2(20 BYTE)",
        "logical_type": "STRING",
        "parameters":   { "max_length": 20, "length_semantics": "BYTE" },
        "nullable":     false,
        "pk":           false
      },
      {
        "name":         "AMOUNT",
        "ordinal":      3,
        "source_type":  "NUMBER(10,2)",
        "logical_type": "DECIMAL",
        "parameters":   { "precision": 10, "scale": 2 },
        "nullable":     false,
        "pk":           false
      },
      {
        "name":         "POSTED_DATE",
        "ordinal":      4,
        "source_type":  "DATE",
        "logical_type": "ORACLE_DATE",           // NOT "DATE" -- critical distinction
        "parameters":   {},
        "nullable":     true,
        "pk":           false
      },
      {
        "name":         "NOTES",
        "ordinal":      5,
        "source_type":  "CLOB",
        "logical_type": "STRING_LOB",
        "parameters":   {},
        "nullable":     true,
        "pk":           false,
        "lob":          true                     // hints that this column has LOB capture constraints
      }
    ]
  }
}
```

## 4.5 DML Event Value Payload -- Values Only

Once a consumer has received the OBJECT_METADATA event for a table, subsequent DML events for that table carry values only. The source_type, logical_type, and parameters fields do NOT appear in the DML payload -- they are resolved by the consumer by looking up the column name in the schema referenced by dataschema.

```
{
  // CloudEvents envelope
  "specversion":   "1.1",
  "id":            "7f3a2b10-e14c-4d8a-9f62-3c1d8e4b5a09",
  "source":        "//oracle-prod/ORCL/FINANCE",
  "subject":       "FINANCE.ORDERS",
  "type":          "com.acme.cdc.dml.UPDATE",
  "time":          "2026-03-22T14:23:01.000Z",
  "datacontenttype":"application/json",
  "dataschema":    "schema-ORDERS-v2",           // <- links to OBJECT_METADATA id
  "cdcspecversion":"1.0",
  "cdcxid":        "1510528009.5.13.7625",
  "cdctxorder":    2,
  "cdcpos":        "0000012C000004D2:14",
  "partitionkey":  "1001",
  // CDC-OIS payload -- values only, no type metadata repeated
  "data": {
    "table":       { "catalog": "ORCL", "schema": "FINANCE", "name": "ORDERS" },
    "primary_key": ["ORDER_ID"],
    "before": {
      "ORDER_ID":    1001,
      "STATUS":      "PENDING",
      "AMOUNT":      "99.95",
      "POSTED_DATE": "2026-03-22T09:00:00",
      "NOTES":       null
    },
    "after": {
      "ORDER_ID":    1001,
      "STATUS":      "SHIPPED",
      "AMOUNT":      "99.95",
      "POSTED_DATE": "2026-03-22T09:00:00",
      "NOTES":       null
    },
    "_lob_overflow": [],                         // empty = no uncaptured LOBs
    "_null_columns": ["NOTES"]                   // explicit: NOTES is genuinely null
  }
}
```

**How a Consumer Resolves Column Types**
1. Consumer receives OBJECT_METADATA "schema-ORDERS-v2" -- caches the column descriptor array keyed by column name.
2. Consumer receives UPDATE event with dataschema: "schema-ORDERS-v2".
3. To interpret "AMOUNT": "99.95" -- consumer looks up "AMOUNT" in the cached schema: logical_type=DECIMAL, parameters={precision:10, scale:2}. It knows the string "99.95" is an exact decimal with 2 scale digits.
4. To interpret "POSTED_DATE": "2026-03-22T09:00:00" -- consumer looks up "POSTED_DATE": logical_type=ORACLE_DATE. It knows the value includes a time component and must not strip it.
5. Consumer receives no further type information in the DML event. The schema cache is the sole type resolution authority.

## 4.6 LOB Overflow Signaling in Value Payloads

The distinction between a genuinely null LOB and an uncaptured LOB MUST be preserved in the value payload. Two fields handle this in the DML event data object:

- **_null_columns**
  - Type: Array of column names
  - Meaning: Columns whose value is genuinely NULL in the source row. The value field for these columns MUST be JSON null.

- **_lob_overflow**
  - Type: Array of column names
  - Meaning: LOB columns whose content was not captured by the CDC tool (e.g., LOB not in transaction log, size exceeded inline limit). The value field for these columns MUST be JSON null. Consumers MUST NOT interpret this null as the actual column value.

```
Scenario: NOTES column is genuinely NULL, PAYLOAD column exceeded inline capture limit.
"before": {
  "ORDER_ID": 1001,
  "NOTES":    null,       // genuinely null
  "PAYLOAD":  null        // NOT captured -- content was in LOB segment, not log
},
"_null_columns":  ["NOTES"],    // NOTES = actual null
"_lob_overflow":  ["PAYLOAD"]   // PAYLOAD = not captured -- treat as unknown, not null
```

## 4.7 Wire Efficiency Analysis

The following illustrates the schema overhead reduction achieved by schema-before-first-use compared to the schema-per-row alternative, for a representative 20-column table.

- **Schema-per-row (Debezium default)**
  - Schema metadata per row: ~1,600 bytes (20 cols x ~80 bytes)
  - 1,000 rows: ~1.6 MB
  - 100,000 rows: ~160 MB
  - Consumer complexity: Low -- schema always present

- **Schema-before-first-use (this proposal)**
  - Schema metadata per row: 0 bytes (schema paid once: ~1,600 bytes total)
  - 1,000 rows: ~1,600 bytes total
  - 100,000 rows: ~1,600 bytes total
  - Consumer complexity: Low -- schema cached from OBJECT_METADATA

- **Schema-per-transaction (evaluated, not adopted)**
  - Schema metadata per row: ~1,600 bytes per transaction (paid once per transaction, not per row)
  - 1,000 rows: Depends on rows-per-txn
  - 100,000 rows: Depends on rows-per-txn
  - Consumer complexity: Medium -- transaction envelope required

- **External registry (optional enhancement)**
  - Schema metadata per row: ~20 bytes (schema ID reference only)
  - 1,000 rows: ~20 KB
  - 100,000 rows: ~2 MB
  - Consumer complexity: High -- registry dependency, lookup latency

**Schema-Per-Transaction vs. Schema-Before-First-Use**
Schema-per-transaction was the initial candidate evaluated during v0.1 design discussions. It was not adopted for the mandatory baseline because: (1) its efficiency advantage over schema-before-first-use is negligible in high-volume single-table workloads -- the dominant CDC pattern; (2) it requires a transaction envelope structure that significantly increases producer implementation complexity; (3) schema-before-first-use is already proven in GoldenGate Data Streams and requires no new structural innovation. Schema-per-transaction remains available as an optional extension (Option C in CDC-OIS Section 5.4) for implementations that require explicit transaction grouping at the envelope level.

# 5. The Two-Layer Type System

## 5.1 Column Descriptor Structure

Every column in an OBJECT_METADATA schema block carries a column descriptor. The descriptor is a JSON object that appears once in the schema -- never in per-row DML value payloads. The following fields are mandatory:

```
{
  "name":         "order_amount",    // Column name -- also the key in DML value objects
  "ordinal":      3,                 // 1-based column position in source table
  "source_type":  "NUMBER(10,2)",    // Verbatim DDL declaration -- never normalized
  "logical_type": "DECIMAL",         // From the OpenCDC canonical vocabulary
  "parameters": {
    "precision": 10,
    "scale": 2
  },
  "nullable":     true,              // Whether the column accepts NULL
  "pk":           false,             // Whether this column is part of the primary key
  "lob":          false              // Whether this column has LOB capture constraints
}
// The corresponding DML value payload entry is simply:
// "order_amount": "9999.99"
// -- no type metadata, just the wire-encoded value.
```

## 5.2 Layer 1: source_type -- Verbatim Source Fidelity

The source_type field carries the exact DDL type declaration as it appears in the source engine's schema. It is populated by the CDC capture layer and is never interpreted, normalized, or modified by any intermediate layer. It travels in the OBJECT_METADATA column descriptor and is consulted by consumers at schema-load time, not at value-decode time.

- **Oracle 23ai -- order_dt DATE**
  - source_type Value: "DATE"
  - What Is Preserved: Source engine identity (from CloudEvents source field) identifies this as ORACLE_DATE semantics

- **Oracle 23ai -- price NUMBER(10,2)**
  - source_type Value: "NUMBER(10,2)"
  - What Is Preserved: Precision 10, scale 2 -- exact Oracle NUMBER declaration

- **Oracle 23ai -- big_num NUMBER(20,-2)**
  - source_type Value: "NUMBER(20,-2)"
  - What Is Preserved: Negative scale (rounds to nearest 100) -- unique to Oracle

- **PostgreSQL 17 -- amount NUMERIC(1000,500)**
  - source_type Value: "NUMERIC(1000,500)"
  - What Is Preserved: Precision 1000 -- exceeds all other engines; Decimal256 required

- **MySQL 9 -- counter BIGINT UNSIGNED**
  - source_type Value: "BIGINT UNSIGNED"
  - What Is Preserved: Unsigned modifier -- no equivalent in other engines

- **Oracle 23ai -- name VARCHAR2(200 BYTE)**
  - source_type Value: "VARCHAR2(200 BYTE)"
  - What Is Preserved: Length semantics (BYTE vs CHAR) -- critical for multibyte character sets

- **Oracle 23ai -- ts TIMESTAMP(9) WITH TIME ZONE**
  - source_type Value: "TIMESTAMP(9) WITH TIME ZONE"
  - What Is Preserved: Full 9-digit nanosecond precision and timezone flag

- **DB2 LUW 12.1 -- rate DECFLOAT(34)**
  - source_type Value: "DECFLOAT(34)"
  - What Is Preserved: IBM-specific decimal float type with 34-digit precision

## 5.3 Layer 2: logical_type -- Canonical Interoperability Vocabulary

The logical_type field carries a named type from the OpenCDC canonical vocabulary defined in Section 6. The mapping from source_type to logical_type is performed by the CDC capture layer at schema emit time. It is deterministic: the same source_type from the same engine always produces the same logical_type. Consumers resolve logical_type at schema-load time from the OBJECT_METADATA event and use it to decode values in subsequent DML events.

- **source_type: "DATE" / Source Engine: Oracle 23ai**
  - logical_type: "ORACLE_DATE"
  - parameters: {} -- no parameters; wire encoding mandates full datetime

- **source_type: "DATE" / Source Engine: PostgreSQL/MySQL/SQL Server/DB2**
  - logical_type: "DATE"
  - parameters: {} -- calendar date only

- **source_type: "NUMBER(10,2)" / Source Engine: Oracle 23ai**
  - logical_type: "DECIMAL"
  - parameters: {"precision": 10, "scale": 2}

- **source_type: "NUMBER(20,-2)" / Source Engine: Oracle 23ai**
  - logical_type: "ORACLE_NUMBER"
  - parameters: {"precision": 20, "scale": -2}

- **source_type: "NUMERIC(1000,500)" / Source Engine: PostgreSQL 17**
  - logical_type: "DECIMAL256"
  - parameters: {"precision": 1000, "scale": 500}

- **source_type: "BIGINT UNSIGNED" / Source Engine: MySQL 9**
  - logical_type: "UINT64"
  - parameters: {} -- wire-encoded as decimal string

- **source_type: "VARCHAR2(200 BYTE)" / Source Engine: Oracle 23ai**
  - logical_type: "STRING"
  - parameters: {"max_length": 200, "length_semantics": "BYTE"}

- **source_type: "TIMESTAMP(9) WITH TIME ZONE" / Source Engine: Oracle 23ai**
  - logical_type: "TIMESTAMP_TZ"
  - parameters: {"precision": 9}

- **source_type: "DECFLOAT(34)" / Source Engine: DB2 LUW 12.1**
  - logical_type: "DECFLOAT34"
  - parameters: {} -- wire-encoded as exact decimal string

- **source_type: "BOOLEAN" / Source Engine: PostgreSQL 17 / Oracle 23ai**
  - logical_type: "BOOLEAN"
  - parameters: {} -- wire-encoded as JSON true/false

- **source_type: "BIT" / Source Engine: SQL Server 2022**
  - logical_type: "BIT"
  - parameters: {} -- wire-encoded as JSON 0/1, NOT boolean

- **source_type: "TIMESTAMP(6)" / Source Engine: MySQL 9**
  - logical_type: "MYSQL_TIMESTAMP"
  - parameters: {"precision": 6} -- UTC-stored, auto-updates on row change

- **source_type: "DATETIME(6)" / Source Engine: MySQL 9**
  - logical_type: "DATETIME"
  - parameters: {"precision": 6} -- stored as-is, no timezone conversion

# 6. Canonical Type Vocabulary

The following sections define the complete canonical type vocabulary. Each type entry specifies: the logical_type name, applicable parameters, the mandatory wire encoding for DML value payloads, and notes on engine mapping and edge cases. All type metadata travels in the OBJECT_METADATA schema block; only wire-encoded values appear in DML events.

## 6.1 Integer Types

- **INT8**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: MySQL TINYINT (signed). Range: -128 to 127

- **UINT8**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: MySQL TINYINT UNSIGNED, SQL Server TINYINT. Range: 0 to 255

- **INT16**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: SMALLINT in all engines

- **INT32**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: INTEGER / INT in all engines. Range: +-2,147,483,647

- **INT64**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: BIGINT in all engines (signed). Range: +-9.2x10^18

- **UINT16**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: MySQL SMALLINT UNSIGNED. No native equivalent in other engines

- **UINT32**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: MySQL INT UNSIGNED. No native equivalent in other engines

- **UINT64**
  - Parameters: none
  - Wire Encoding: Exact decimal STRING
  - Engine Mapping Notes: MySQL BIGINT UNSIGNED only. Max 18.4x10^18 -- exceeds JSON safe integer range. MUST be string-encoded

- **MEDIUMINT**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: MySQL MEDIUMINT only. 3-byte signed integer

- **UINT_MEDIUMINT**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: MySQL MEDIUMINT UNSIGNED. Range: 0 to 16,777,215

**UINT64 Must Be String-Encoded**
MySQL BIGINT UNSIGNED max (18,446,744,073,709,551,615) exceeds IEEE 754 double precision safe integer range (2^53 approximately 9x10^15). All conforming implementations MUST encode UINT64 values as exact decimal strings regardless of the actual column value. This rule applies at the value-encoding layer -- the logical_type=UINT64 in the schema tells the consumer to expect a string.

## 6.2 Exact Decimal Types

All exact decimal types use string wire encoding in DML value payloads. JSON numbers cannot represent trailing zeros (3.10 becomes 3.1), arbitrary precision, or IEEE 754 special values. The logical_type in the schema tells the consumer how to parse the string.

- **DECIMAL**
  - Parameters: precision (1-38), scale (0 to precision)
  - Wire Encoding: Exact decimal STRING
  - Notes: Standard SQL NUMERIC/DECIMAL in all engines. Use when precision <= 38 and scale >= 0

- **DECIMAL256**
  - Parameters: precision (1-1000), scale (any)
  - Wire Encoding: Exact decimal STRING
  - Notes: PostgreSQL NUMERIC only -- precision up to 1,000. No other engine can store >38 significant digits

- **ORACLE_NUMBER**
  - Parameters: precision (1-38), scale (-84 to 127)
  - Wire Encoding: Exact decimal STRING
  - Notes: Oracle NUMBER with negative scale only. The negative scale MUST be preserved in schema parameters

Special values for exact numerics (PostgreSQL NUMERIC only) -- these appear as strings in DML value payloads:

- **Not a Number**
  - Wire Encoding: "NaN"
  - Notes: String sentinel. PostgreSQL NUMERIC only

- **Positive Infinity**
  - Wire Encoding: "Infinity"
  - Notes: String sentinel. PostgreSQL NUMERIC only

- **Negative Infinity**
  - Wire Encoding: "-Infinity"
  - Notes: String sentinel. PostgreSQL NUMERIC only

## 6.3 Floating Point Types

- **FLOAT32**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: IEEE 754 single. PostgreSQL REAL, MySQL FLOAT (p<=24), SQL Server REAL, DB2 REAL, Oracle BINARY_FLOAT

- **FLOAT64**
  - Parameters: none
  - Wire Encoding: JSON number
  - Engine Mapping Notes: IEEE 754 double. PostgreSQL DOUBLE PRECISION, MySQL DOUBLE, SQL Server FLOAT, DB2 DOUBLE, Oracle BINARY_DOUBLE

- **DECFLOAT16**
  - Parameters: none
  - Wire Encoding: Exact decimal STRING
  - Engine Mapping Notes: IBM Db2 LUW DECFLOAT(16) ONLY. 16 significant decimal digits. No equivalent in any other engine

- **DECFLOAT34**
  - Parameters: none
  - Wire Encoding: Exact decimal STRING
  - Engine Mapping Notes: IBM Db2 LUW DECFLOAT(34) ONLY. 34 significant decimal digits. AWS DMS does not support CDC of this type

Special float values (appear as strings in DML value payloads): "NaN", "Infinity", "-Infinity". Negative zero encoded as JSON -0 and MUST be preserved.

## 6.4 String and Binary Types

- **STRING**
  - Parameters: max_length (integer), length_semantics: "BYTE" or "CHAR"
  - Wire Encoding: UTF-8 JSON string
  - Notes: CHAR, VARCHAR, VARCHAR2, TEXT. length_semantics mandatory for Oracle and DB2

- **STRING_LOB**
  - Parameters: none
  - Wire Encoding: UTF-8 string or null + _lob_overflow flag
  - Notes: CLOB, NCLOB, LONGTEXT, VARCHAR(MAX). LOB capture constraints apply

- **BYTES**
  - Parameters: max_length (integer)
  - Wire Encoding: Base64 JSON string
  - Notes: BYTEA, RAW, VARBINARY, BINARY. Always Base64-encoded

- **BYTES_LOB**
  - Parameters: none
  - Wire Encoding: Base64 or null + _lob_overflow flag
  - Notes: BLOB, LONGBLOB, VARBINARY(MAX). LOB capture constraints apply

- **EXTERNAL_REF**
  - Parameters: none
  - Wire Encoding: null + _lob_overflow flag
  - Notes: Oracle BFILE ONLY. Content is a filesystem file; never in transaction log

- **NATIONAL_STRING**
  - Parameters: max_length (integer), length_semantics: "CHAR"
  - Wire Encoding: UTF-8 JSON string
  - Notes: NCHAR, NVARCHAR, NCHAR VARYING, DB2 GRAPHIC/VARGRAPHIC

## 6.5 Date and Time Types

- **DATE**
  - Parameters: none
  - Wire Encoding in DML: "YYYY-MM-DD"
  - Notes: Calendar date only. PostgreSQL, MySQL, SQL Server, DB2. No time component.

- **ORACLE_DATE**
  - Parameters: none
  - Wire Encoding in DML: "YYYY-MM-DDTHH:MM:SS"
  - Notes: Oracle DATE ONLY. Stores date AND time. Consumers MUST NOT strip the time component.

- **DATETIME**
  - Parameters: precision (0-9)
  - Wire Encoding in DML: "YYYY-MM-DDTHH:MM:SS.ffffff"
  - Notes: MySQL DATETIME, SQL Server DATETIME2. No timezone stored.

- **MYSQL_TIMESTAMP**
  - Parameters: precision (0-6)
  - Wire Encoding in DML: "YYYY-MM-DDTHH:MM:SS.ffffff"
  - Notes: MySQL TIMESTAMP ONLY. Distinct from DATETIME: stored as UTC, auto-updates on row change. logical_type in schema signals this semantic to consumers.

- **TIMESTAMP**
  - Parameters: precision (0-12)
  - Wire Encoding in DML: "YYYY-MM-DDTHH:MM:SS.ffffff"
  - Notes: Timestamp without timezone. PostgreSQL, Oracle, DB2.

- **TIMESTAMP_TZ**
  - Parameters: precision (0-9)
  - Wire Encoding in DML: "YYYY-MM-DDTHH:MM:SS+HH:MM"
  - Notes: Timestamp WITH TIME ZONE. Original offset MUST be preserved. MUST NOT normalize to UTC.

- **TIMESTAMP_LTZ**
  - Parameters: precision (0-9)
  - Wire Encoding in DML: "YYYY-MM-DDTHH:MM:SS+HH:MM"
  - Notes: Oracle TIMESTAMP WITH LOCAL TIME ZONE. Carry DB timezone offset at capture time.

- **TIME**
  - Parameters: precision (0-9)
  - Wire Encoding in DML: "HH:MM:SS.ffffff" or ISO 8601 for elapsed
  - Notes: Time of day. MySQL TIME can exceed 24h -- serialize as string for values outside 00:00:00-23:59:59.

- **SMALLDATETIME**
  - Parameters: none
  - Wire Encoding in DML: "YYYY-MM-DDTHH:MM:00"
  - Notes: SQL Server SMALLDATETIME. Minute precision only.

- **YEAR**
  - Parameters: none
  - Wire Encoding in DML: JSON integer (4-digit)
  - Notes: MySQL YEAR type. MUST NOT be encoded as DATE.

**Oracle DATE -- Highest-Risk Type Behavior**
Oracle DATE stores year, month, day, hour, minute, and second. Every other engine's DATE stores only a calendar date. A CDC stream that maps Oracle DATE to logical_type DATE will silently drop the time component for every row. ORACLE_DATE as a distinct logical_type is mandatory. This is the single most dangerous cross-engine semantic divergence in the survey.

**MySQL TIMESTAMP vs DATETIME -- Resolved in v0.2**
MySQL TIMESTAMP (logical_type: MYSQL_TIMESTAMP) and MySQL DATETIME (logical_type: DATETIME) display identically in SELECT output but have fundamentally different semantics: TIMESTAMP is stored as UTC and auto-updates on row modification; DATETIME is stored as-is and does not auto-update. v0.1 Open Question Q1 (whether to use a separate logical type for MySQL TIMESTAMP) is resolved in v0.2: MYSQL_TIMESTAMP is adopted as a distinct logical type. The semantic difference is material for consumers implementing replication, auditing, or bi-directional sync and must not be collapsed into a single type.

## 6.6 Interval Types

- **INTERVAL_YM**
  - Parameters: year_precision (0-9)
  - Wire Encoding in DML: ISO 8601: "P1Y2M"
  - Notes: INTERVAL YEAR TO MONTH. Oracle 23ai and PostgreSQL only. MySQL, SQL Server, DB2 consumers must store as VARCHAR or convert.

- **INTERVAL_DS**
  - Parameters: day_precision (0-9), sec_precision (0-9)
  - Wire Encoding in DML: ISO 8601: "P1DT2H3M4.567890S"
  - Notes: INTERVAL DAY TO SECOND. Oracle 23ai and PostgreSQL only. Oracle supports nanosecond precision in fractional seconds.

## 6.7 Boolean Types

- **BOOLEAN**
  - Wire Encoding in DML: JSON true / false / null
  - Engine Mapping Notes: PostgreSQL BOOLEAN/BOOL and Oracle 23ai BOOLEAN/BOOL. True SQL boolean semantics. Wire-encoded as JSON boolean literals -- not 0/1 integers.

- **BIT**
  - Wire Encoding in DML: JSON 0 / 1 / null
  - Engine Mapping Notes: SQL Server BIT. Stores 1, 0, or NULL. Not a SQL boolean. MUST NOT be encoded as JSON boolean.

- **TINYINT1**
  - Wire Encoding in DML: JSON 0 / 1 / null
  - Engine Mapping Notes: MySQL TINYINT(1) boolean alias. MUST NOT be encoded as JSON boolean. Consumer applies domain knowledge to interpret as boolean.

## 6.8 UUID and Identity Types

- **UUID**
  - Wire Encoding in DML: Hyphenated lowercase string, RFC 4122 order: "550e8400-e29b-41d4-a716-446655440000"
  - Notes: PostgreSQL UUID native type. RFC 4122 big-endian byte order.

- **GUID**
  - Wire Encoding in DML: Hyphenated string, SQL Server display order: "6F9619FF-8B86-D011-B42D-00C04FC964FF"
  - Notes: SQL Server UNIQUEIDENTIFIER ONLY. Non-RFC-4122 byte ordering. Always serialize in SQL Server display order (CONVERT(VARCHAR(36), column)) to preserve identity.

## 6.9 JSON, Document, and Spatial Types

- **JSON**
  - Wire Encoding in DML: Escaped JSON string (NOT a nested JSON object)
  - Notes: PostgreSQL JSON/JSONB, MySQL JSON, SQL Server JSON, Oracle JSON. Value is an escaped string -- parse with JSON.parse() if needed. See double-serialization rule.

- **JSONB**
  - Wire Encoding in DML: Escaped JSON string
  - Notes: PostgreSQL JSONB only. Semantically identical to JSON for wire purposes. Distinct logical_type retained for schema fidelity.

- **XML**
  - Wire Encoding in DML: XML string (escaped)
  - Notes: PostgreSQL XML, SQL Server XML, Oracle XMLType. Full document as string value.

- **GEOMETRY**
  - Wire Encoding in DML: OGC EWKT: "SRID=####;TYPE(...)"
  - Notes: All engines (PostGIS, MySQL, SQL Server, DB2 Spatial, Oracle SDO_GEOMETRY). SRID MUST be included in wire value. EWKT preferred over WKB for cross-engine readability.

## 6.10 Vector Types

- **VECTOR**
  - Parameters (in schema): dimensions (integer), element_type: "FLOAT32" or "FLOAT64" or "INT8" or "BINARY" or "BIT"
  - Wire Encoding in DML: JSON array of numbers or Base64 for BINARY/BIT
  - Notes: Oracle 23ai VECTOR, pgvector, MySQL 9 VECTOR, SQL Server VECTOR (preview). dimensions and element_type are mandatory in schema parameters -- they do not repeat per row.

## 6.11 Engine-Specific Types

- **TSVECTOR**
  - Engine: PostgreSQL
  - Wire Encoding in DML: Text string
  - Notes: Full-text search document. Cannot reconstruct in non-PostgreSQL targets.

- **TSQUERY**
  - Engine: PostgreSQL
  - Wire Encoding in DML: Text string
  - Notes: Full-text search query. PostgreSQL-specific syntax.

- **ARRAY**
  - Engine: PostgreSQL
  - Wire Encoding in DML: JSON array
  - Notes: Typed arrays (int[], text[], jsonb[]). Element logical_type in schema parameters. Multi-dimensional = nested JSON arrays.

- **RANGE**
  - Engine: PostgreSQL
  - Wire Encoding in DML: JSON: {"lower": x, "upper": y, "bounds": "[)"}
  - Notes: Typed ranges. Element logical_type in schema parameters. Bounds string uses PostgreSQL notation.

- **COMPOSITE**
  - Engine: PostgreSQL
  - Wire Encoding in DML: JSON object with field names
  - Notes: User-defined composite types. Field-to-logical_type mapping in schema parameters.

- **ENUM**
  - Engine: PostgreSQL, MySQL
  - Wire Encoding in DML: String (enum value)
  - Notes: Enum member list in schema source_type. Value is always the string label.

- **SET**
  - Engine: MySQL
  - Wire Encoding in DML: Comma-separated string
  - Notes: MySQL SET multi-value column. Example: "gift,signature_req"

- **YEAR**
  - Engine: MySQL
  - Wire Encoding in DML: JSON integer (4-digit)
  - Notes: MySQL YEAR. MUST NOT be encoded as DATE.

- **MONEY**
  - Engine: PostgreSQL, SQL Server
  - Wire Encoding in DML: Exact decimal STRING
  - Notes: Always string to avoid locale-dependent interpretation.

- **SQL_VARIANT**
  - Engine: SQL Server
  - Wire Encoding in DML: JSON: {"base_type": "INT", "value": 42}
  - Notes: Self-describing heterogeneous container. base_type carries the actual type name.

- **HIERARCHYID**
  - Engine: SQL Server
  - Wire Encoding in DML: Path string: "/1/2/3/"
  - Notes: SQL Server hierarchy position.

- **ROWVERSION**
  - Engine: SQL Server
  - Wire Encoding in DML: Hex string
  - Notes: Binary counter. MUST NOT be treated as a datetime.

- **ANYDATA**
  - Engine: Oracle
  - Wire Encoding in DML: JSON: {"type": "VARCHAR2", "value": "..."}
  - Notes: Oracle self-describing container. GoldenGate 23ai supports capture.

- **ROWID**
  - Engine: Oracle, DB2
  - Wire Encoding in DML: Base64 string
  - Notes: Physical row address. Not portable. Informational only.

- **BFILE_REF**
  - Engine: Oracle
  - Wire Encoding in DML: null + _lob_overflow flag
  - Notes: External file pointer. Content NEVER capturable. Path in schema metadata only.

# 7. Wire Encoding Summary

The following is a quick reference for DML value payload wire encoding by type category. All type metadata (source_type, logical_type, parameters) travels in the OBJECT_METADATA schema block and is not repeated here.

- **Signed integers (INT8-INT64)**
  - DML Wire Encoding: JSON number
  - Special Values / Notes: Within JSON safe integer range (+-2^53)

- **UINT64 (MySQL BIGINT UNSIGNED)**
  - DML Wire Encoding: Exact decimal STRING
  - Special Values / Notes: Always string regardless of actual value

- **Exact decimals (DECIMAL, DECIMAL256, ORACLE_NUMBER)**
  - DML Wire Encoding: Exact decimal STRING
  - Special Values / Notes: "NaN", "Infinity", "-Infinity" as string sentinels for PostgreSQL NUMERIC special values

- **IEEE 754 floats (FLOAT32, FLOAT64)**
  - DML Wire Encoding: JSON number
  - Special Values / Notes: "NaN", "Infinity", "-Infinity" as string sentinels. -0.0 preserved as JSON -0

- **DECFLOAT (IBM Db2)**
  - DML Wire Encoding: Exact decimal STRING
  - Special Values / Notes: Always string -- cannot be approximated as IEEE 754 binary

- **Strings / CHAR / VARCHAR**
  - DML Wire Encoding: UTF-8 JSON string
  - Special Values / Notes: length_semantics (BYTE vs CHAR) in schema parameters, not in DML value

- **Binary / BYTEA / RAW**
  - DML Wire Encoding: Base64 JSON string
  - Special Values / Notes: Standard Base64 (RFC 4648), no line breaks

- **LOB columns (STRING_LOB, BYTES_LOB)**
  - DML Wire Encoding: String/Base64 or null + _lob_overflow
  - Special Values / Notes: _lob_overflow distinguishes uncaptured from genuine null

- **DATE (non-Oracle)**
  - DML Wire Encoding: "YYYY-MM-DD"
  - Special Values / Notes: No time component under any circumstances

- **ORACLE_DATE**
  - DML Wire Encoding: "YYYY-MM-DDTHH:MM:SS"
  - Special Values / Notes: Time component ALWAYS included. Never strip.

- **DATETIME, TIMESTAMP (no TZ)**
  - DML Wire Encoding: "YYYY-MM-DDTHH:MM:SS.ffffff"
  - Special Values / Notes: Precision from schema parameters determines fractional digits

- **MYSQL_TIMESTAMP**
  - DML Wire Encoding: "YYYY-MM-DDTHH:MM:SS.ffffff"
  - Special Values / Notes: UTC-captured. Schema logical_type=MYSQL_TIMESTAMP signals auto-update semantics to consumers

- **TIMESTAMP_TZ, DATETIMEOFFSET**
  - DML Wire Encoding: "...+HH:MM" or "...Z"
  - Special Values / Notes: Original offset preserved. MUST NOT normalize to UTC.

- **INTERVAL (year-month)**
  - DML Wire Encoding: ISO 8601 duration: "P#Y#M"
  - Special Values / Notes: P2Y3M = 2 years, 3 months

- **INTERVAL (day-second)**
  - DML Wire Encoding: ISO 8601 duration: "P#DT#H#M#.#S"
  - Special Values / Notes: Full nanosecond precision in fractional seconds

- **YEAR (MySQL)**
  - DML Wire Encoding: JSON integer (4-digit)
  - Special Values / Notes: Never a DATE

- **BOOLEAN**
  - DML Wire Encoding: JSON true / false / null
  - Special Values / Notes: PostgreSQL and Oracle 23ai BOOLEAN only

- **BIT, TINYINT1**
  - DML Wire Encoding: JSON 0 / 1 / null
  - Special Values / Notes: Not JSON boolean -- integer encoding

- **UUID**
  - DML Wire Encoding: Hyphenated lowercase (RFC 4122)
  - Special Values / Notes: "550e8400-e29b-41d4-a716-446655440000"

- **GUID (SQL Server)**
  - DML Wire Encoding: Hyphenated (SQL Server display order)
  - Special Values / Notes: Different byte order than RFC 4122

- **JSON, JSONB**
  - DML Wire Encoding: Escaped JSON string (not nested object)
  - Special Values / Notes: Parse with JSON.parse() if needed

- **XML, XMLType**
  - DML Wire Encoding: XML string (escaped)
  - Special Values / Notes: Full document as string value

- **GEOMETRY (spatial)**
  - DML Wire Encoding: OGC EWKT: "SRID=####;TYPE(...)"
  - Special Values / Notes: SRID always included in DML value string

- **VECTOR**
  - DML Wire Encoding: JSON array of numbers
  - Special Values / Notes: Base64 for BIT/BINARY. Dimensions and element_type in schema only.

- **MONEY**
  - DML Wire Encoding: Exact decimal STRING
  - Special Values / Notes: Locale-independent; full precision preserved

- **SQL_VARIANT**
  - DML Wire Encoding: JSON: {"base_type": "...", "value": ...}
  - Special Values / Notes: base_type carries the actual underlying type name

- **HIERARCHYID**
  - DML Wire Encoding: Path string: "/1/2/3/"
  - Special Values / Notes: SQL Server path notation

- **ROWVERSION**
  - DML Wire Encoding: Hex string
  - Special Values / Notes: Binary counter -- NOT a datetime

- **BFILE_REF / EXTERNAL_REF**
  - DML Wire Encoding: null + _lob_overflow flag
  - Special Values / Notes: Content never capturable

# 8. Normative Conformance Rules

These rules are MUST requirements for all conforming OpenCDC implementations. Rules 1-4 govern the type system. Rules 5-6 govern schema delivery and are new in v0.2.

## Rule 1: No Silent Truncation

A conforming implementation MUST NOT silently truncate, round, or reduce the precision of any value during capture or forwarding. If a consumer cannot represent a value at full source precision, it MUST emit an error, a warning, or a configurable conversion action. Silence is not permitted.

## Rule 2: No Semantic Reinterpretation

A conforming implementation MUST NOT reinterpret the semantic meaning of a type based on the consuming engine's type system. An ORACLE_DATE value MUST include its time component. A TIMESTAMP_TZ value MUST preserve its original timezone offset. A BIT or TINYINT1 value MUST be encoded as an integer (0/1), not as a JSON boolean.

## Rule 3: LOB Null and LOB Overflow Are Distinct States

A conforming implementation MUST distinguish between a genuinely null LOB value and a LOB value not captured due to CDC infrastructure limitations. Genuinely null columns appear in _null_columns. Uncaptured LOB columns appear in _lob_overflow. Both have JSON null as the value field. These two states MUST be distinguishable.

```
// Genuine NULL in a nullable LOB column:
"_null_columns": ["NOTES"],
"NOTES": null

// LOB column with content NOT CAPTURED by CDC tool:
"_lob_overflow": ["PAYLOAD"],
"PAYLOAD": null

// Both null and not-captured in same event:
"_null_columns": ["NOTES"],
"_lob_overflow": ["PAYLOAD"]
"NOTES": null,
"PAYLOAD": null    // consumer distinguishes by checking both arrays
```

## Rule 4: Timezone Offsets Must Be Preserved

A conforming implementation MUST preserve the original timezone offset for all TIMESTAMP_TZ and TIMESTAMP_LTZ values. UTC normalization MUST NOT be performed by the capture layer or any intermediate forwarding layer. UTC normalization is a consumer decision.

## Rule 5: Schema MUST Precede First DML -- Stream Ordering

A conforming producer MUST emit an OBJECT_METADATA event for a table before emitting any DML event for that table. A conforming producer MUST emit a new OBJECT_METADATA event after any DDL event that changes a table's structure, and before the first DML event for that table under the new structure. Violating this ordering is a conformance failure.

## Rule 6: Producers MUST Support Consumer Reconnection

A conforming producer MUST implement at least one of the following behaviors, and MUST implement Approach 1 as a fallback when Approach 2 is not available:

- Approach 1 (required baseline): On any new consumer connection, emit current OBJECT_METADATA events for all in-scope tables before resuming data delivery. Re-emitted schemas are session-scoped and do not modify the durable stream.

- Approach 2 (recommended enhancement): When a consumer resumes from a saved position, replay MUST begin at or before the most recent OBJECT_METADATA event for each in-scope table that was current at that position. The consumer must receive its schema before its first data event regardless of where in the stream it resumes from.

# 9. Wire Format Examples

The following examples show the full schema-before-first-use pattern: an OBJECT_METADATA event followed by DML events with values-only payloads. Each example covers one source engine and illustrates key type system decisions in context.

## 9.1 Oracle 23ai -- Schema Event Then DML Events

DDL context: Financial transactions table with Oracle-specific types including ORACLE_DATE, negative-scale NUMBER, nanosecond TIMESTAMP_TZ, and CLOB.

```
// -- Step 1: OBJECT_METADATA (emitted once, before first DML) --
{
  "specversion": "1.1",
  "id":          "schema-FIN_TXN-v1",
  "type":        "com.acme.cdc.meta.OBJECT_METADATA",
  "source":      "//oracle-prod/ORCL/FINANCE",
  "subject":     "FINANCE.FIN_TRANSACTIONS",
  "data": {
    "table": {"catalog":"ORCL","schema":"FINANCE","name":"FIN_TRANSACTIONS"},
    "schema_version": 1,
    "primary_key": ["TXN_ID"],
    "columns": [
      {"name":"TXN_ID",     "ordinal":1, "source_type":"NUMBER(19,0)",
       "logical_type":"DECIMAL",     "parameters":{"precision":19,"scale":0},   "nullable":false,"pk":true},
      {"name":"AMOUNT",     "ordinal":2, "source_type":"NUMBER(15,2)",
       "logical_type":"DECIMAL",     "parameters":{"precision":15,"scale":2},   "nullable":false,"pk":false},
      {"name":"MAGNITUDE",  "ordinal":3, "source_type":"NUMBER(20,-2)",
       "logical_type":"ORACLE_NUMBER","parameters":{"precision":20,"scale":-2}, "nullable":true, "pk":false},
      {"name":"POSTED_DATE","ordinal":4, "source_type":"DATE",
       "logical_type":"ORACLE_DATE", "parameters":{},                           "nullable":false,"pk":false},
      {"name":"SETTLED_TS", "ordinal":5, "source_type":"TIMESTAMP(9) WITH TIME ZONE",
       "logical_type":"TIMESTAMP_TZ","parameters":{"precision":9},              "nullable":true, "pk":false},
      {"name":"NOTES",      "ordinal":6, "source_type":"CLOB",
       "logical_type":"STRING_LOB",  "parameters":{},                           "nullable":true, "pk":false,"lob":true}
    ]
  }
}
// -- Step 2: INSERT -- values only, no type metadata repeated --
{
  "specversion": "1.1",
  "id":          "7f3a2b10-e14c-4d8a-9f62-3c1d8e4b5a09",
  "type":        "com.acme.cdc.dml.INSERT",
  "dataschema":  "schema-FIN_TXN-v1",
  "cdcxid":      "1510528009.5.13.7625",
  "cdctxorder":  1,
  "data": {
    "table":       {"catalog":"ORCL","schema":"FINANCE","name":"FIN_TRANSACTIONS"},
    "primary_key": ["TXN_ID"],
    "before":      null,
    "after": {
      "TXN_ID":      "8675309000001",          // DECIMAL -> exact string
      "AMOUNT":      "1250000.00",              // DECIMAL -> trailing zero preserved
      "MAGNITUDE":   "134500",                  // ORACLE_NUMBER(20,-2) -> represents 1345 hundreds
      "POSTED_DATE": "2026-03-22T14:30:00",    // ORACLE_DATE -> time always included
      "SETTLED_TS":  "2026-03-22T14:30:00.123456789+05:30",  // TZ offset preserved
      "NOTES":       null
    },
    "_null_columns":  ["NOTES"],               // NOTES is genuinely null
    "_lob_overflow":  []
  }
}
// -- Step 3: UPDATE where NOTES LOB was not captured --
{
  "type":       "com.acme.cdc.dml.UPDATE",
  "dataschema": "schema-FIN_TXN-v1",
  "data": {
    "table":       {"catalog":"ORCL","schema":"FINANCE","name":"FIN_TRANSACTIONS"},
    "primary_key": ["TXN_ID"],
    "before": { "TXN_ID": "8675309000001", "AMOUNT": "1000000.00", "NOTES": null },
    "after":  { "TXN_ID": "8675309000001", "AMOUNT": "1250000.00", "NOTES": null },
    "_null_columns": [],
    "_lob_overflow": ["NOTES"]                 // NOTES updated but content not in log
  }
}
```

## 9.2 MySQL 9 -- Schema Change (DDL) Sequence

This example shows the mandatory ordering when a DDL ALTER adds a column. Schema v1 precedes pre-DDL DML; schema v2 is emitted after the ALTER and before the next DML.

```
// -- Schema v1 --
{ "id": "schema-ORDERS-v1", "type": "...OBJECT_METADATA",
  "data": { "schema_version":1, "primary_key":["ORDER_ID"],
    "columns": [
      {"name":"ORDER_ID",  "source_type":"BIGINT UNSIGNED","logical_type":"UINT64",
       "nullable":false,"pk":true},
      {"name":"IS_PAID",   "source_type":"TINYINT(1)",     "logical_type":"TINYINT1",
       "nullable":false,"pk":false},
      {"name":"TOTAL",     "source_type":"DECIMAL(10,2)",  "logical_type":"DECIMAL",
       "parameters":{"precision":10,"scale":2},"nullable":false,"pk":false},
      {"name":"CREATED_AT","source_type":"DATETIME(6)",    "logical_type":"DATETIME",
       "parameters":{"precision":6},"nullable":false,"pk":false},
      {"name":"SHIPPED_AT","source_type":"TIMESTAMP(6)",   "logical_type":"MYSQL_TIMESTAMP",
       "parameters":{"precision":6},"nullable":true,"pk":false}
    ]
  }
}
// -- DML under v1 --
{ "type":"...INSERT", "dataschema":"schema-ORDERS-v1",
  "data": { "after": {
    "ORDER_ID":   "18446744073709551000",   // UINT64 -> always string
    "IS_PAID":    1,                         // TINYINT1 -> integer, NOT true
    "TOTAL":      "1299.99",
    "CREATED_AT": "2026-03-22T14:30:00.123456",
    "SHIPPED_AT": null
  }, "_null_columns":["SHIPPED_AT"], "_lob_overflow":[] }
}
// -- DDL: ALTER TABLE ORDERS ADD COLUMN TRACKING_CODE VARCHAR(50) --
{ "type":"...ddl.ALTER", "subject":"ecommerce.ORDERS",
  "data": { "ddl": {"statement":"ALTER TABLE ORDERS ADD COLUMN TRACKING_CODE VARCHAR(50)"} }
}
// -- Schema v2 (MUST precede next DML -- conformance requirement) --
{ "id": "schema-ORDERS-v2", "type": "...OBJECT_METADATA",
  "data": { "schema_version":2, "primary_key":["ORDER_ID"],
    "columns": [
      {"name":"ORDER_ID",      "source_type":"BIGINT UNSIGNED","logical_type":"UINT64",
       "nullable":false,"pk":true},
      {"name":"IS_PAID",       "source_type":"TINYINT(1)",     "logical_type":"TINYINT1",
       "nullable":false,"pk":false},
      {"name":"TOTAL",         "source_type":"DECIMAL(10,2)",  "logical_type":"DECIMAL",
       "parameters":{"precision":10,"scale":2},"nullable":false,"pk":false},
      {"name":"CREATED_AT",    "source_type":"DATETIME(6)",    "logical_type":"DATETIME",
       "parameters":{"precision":6},"nullable":false,"pk":false},
      {"name":"SHIPPED_AT",    "source_type":"TIMESTAMP(6)",   "logical_type":"MYSQL_TIMESTAMP",
       "parameters":{"precision":6},"nullable":true,"pk":false},
      {"name":"TRACKING_CODE", "source_type":"VARCHAR(50)",    "logical_type":"STRING",
       "parameters":{"max_length":50,"length_semantics":"CHAR"},"nullable":true,"pk":false}
    ]
  }
}
// -- DML under v2 --
{ "type":"...UPDATE", "dataschema":"schema-ORDERS-v2",
  "data": { "after": {
    "ORDER_ID":      "18446744073709551000",
    "TRACKING_CODE": "TRK-2026-00812"       // new column present in schema v2
  }, "_null_columns":[], "_lob_overflow":[] }
}
```

## 9.3 Consumer Reconnection -- Approach 1 (Session-Scoped Schema Re-Emission)

This example shows what a consumer sees when it connects or reconnects while DML is in progress, under Approach 1.

```
// Durable stream (what is stored on the server):
// [pos 001] OBJECT_METADATA  id:"schema-ORDERS-v2"
// [pos 050] INSERT            dataschema:"schema-ORDERS-v2"
// [pos 051] UPDATE            dataschema:"schema-ORDERS-v2"
// [pos 052] INSERT            dataschema:"schema-ORDERS-v2"   <- consumer connects here
// [pos 053] DELETE            dataschema:"schema-ORDERS-v2"

// Consumer connects with begin=pos:052 (resume from saved position)
// What the consumer RECEIVES (producer Approach 1 behavior):
// [session] OBJECT_METADATA  id:"schema-ORDERS-v2"   <- session-scoped, NOT in durable stream
//           (producer re-emits current schema for ORDERS before any data)
// [pos 052] INSERT            dataschema:"schema-ORDERS-v2"   <- data stream resumes from pos:052
// [pos 053] DELETE            dataschema:"schema-ORDERS-v2"

// Consumer has schema before its first data event.
// It can validate: schema version in OBJECT_METADATA matches dataschema reference in events.
// If schema version differs from last known version, consumer detects schema change.
```

## 9.4 PostgreSQL 17 -- Complex Types in Schema

This example shows the OBJECT_METADATA structure for PostgreSQL-specific types: UUID, ARRAY, RANGE, INTERVAL, and JSONB. DML values are compact strings resolved against the schema.

```
// -- OBJECT_METADATA --
{ "id": "schema-MEASUREMENTS-v1", "type": "...OBJECT_METADATA",
  "data": { "schema_version":1, "primary_key":["SAMPLE_ID"],
    "columns": [
      {"name":"SAMPLE_ID", "source_type":"uuid",
       "logical_type":"UUID",      "nullable":false,"pk":true},
      {"name":"VALUE",     "source_type":"NUMERIC(500,250)",
       "logical_type":"DECIMAL256","parameters":{"precision":500,"scale":250},"nullable":true},
      {"name":"TAGS",      "source_type":"text[]",
       "logical_type":"ARRAY",     "parameters":{"element_logical_type":"STRING"},"nullable":true},
      {"name":"VALID_RNG", "source_type":"numrange",
       "logical_type":"RANGE",     "parameters":{"element_logical_type":"DECIMAL"},"nullable":true},
      {"name":"DURATION",  "source_type":"INTERVAL DAY TO SECOND(6)",
       "logical_type":"INTERVAL_DS","parameters":{"day_precision":4,"sec_precision":6},"nullable":true},
      {"name":"LOCATION",  "source_type":"geometry(Point,4326)",
       "logical_type":"GEOMETRY",  "parameters":{"subtype":"POINT","srid":4326},"nullable":true},
      {"name":"META",      "source_type":"jsonb",
       "logical_type":"JSONB",     "nullable":true},
      {"name":"EMBEDDING", "source_type":"vector(1536)",
       "logical_type":"VECTOR",    "parameters":{"dimensions":1536,"element_type":"FLOAT32"},"nullable":true}
    ]
  }
}
// -- DML INSERT -- values only --
{ "type":"...INSERT", "dataschema":"schema-MEASUREMENTS-v1",
  "data": { "after": {
    "SAMPLE_ID": "550e8400-e29b-41d4-a716-446655440000",  // UUID -> hyphenated string
    "VALUE":     "12345678901234567890.12345",             // DECIMAL256 -> exact string
    "TAGS":      ["temperature","pressure","calibrated"],  // ARRAY -> JSON array
    "VALID_RNG": {"lower":"0.5","upper":"2.5","bounds":"[)"},  // RANGE -> JSON object
    "DURATION":  "P2DT4H30M15.123456S",                   // INTERVAL_DS -> ISO 8601
    "LOCATION":  "SRID=4326;POINT(-73.9857 40.7484)",     // GEOMETRY -> EWKT
    "META":      "{\"sensor_id\":42,\"readings\":[1.1,2.2]}",  // JSONB -> escaped string
    "EMBEDDING": [0.023,-0.184,0.762]                     // VECTOR -> JSON array
  }, "_null_columns":[], "_lob_overflow":[] }
}
```

# 10. Open Questions for Working Group Review

The following questions are presented for working group discussion. Q1 from v0.1 is resolved; the remaining questions are either carried forward or new in v0.2.

- **Q1**
  - Question: MySQL TIMESTAMP vs DATETIME -- separate logical types?
  - Status: RESOLVED in v0.2. MYSQL_TIMESTAMP adopted as a distinct logical type. The semantic difference (UTC storage, auto-update behavior) is material and must not be collapsed with DATETIME.

- **Q2**
  - Question: Maximum inline LOB size
  - Status: OPEN. The proposal defines the _lob_overflow flag but does not specify a mandatory maximum inline LOB size. Should the specification define a threshold (e.g., 64 KB) or leave this implementation-defined with _lob_overflow as the signaling mechanism?

- **Q3**
  - Question: Vector dimension limits
  - Status: OPEN. Engine limits differ: Oracle 23ai (flexible), pgvector (16,000 for float4), MySQL 9 (16,383), SQL Server preview (1,998). Should the spec define a maximum dimension count for interoperability, or carry dimensions as-is and let consumers handle the mismatch?

- **Q4**
  - Question: DECFLOAT capture failure -- error vs. skip
  - Status: OPEN. AWS DMS explicitly does not support CDC of IBM Db2 DECFLOAT columns. Should the spec require producers to emit a structured error event (not silently skip) when a DECFLOAT column cannot be captured?

- **Q5**
  - Question: PostgreSQL NUMERIC special values in non-PostgreSQL targets
  - Status: OPEN. When consumers receive "NaN", "Infinity", or "-Infinity" for a DECIMAL column targeting an engine that cannot represent them, should the spec require an error (MUST) or a warning (SHOULD)?

- **Q6**
  - Question: Approach 2 replay window -- implementation guidance
  - Status: NEW in v0.2. Approach 2 (position-based schema availability) requires producers to scan back in the durable stream to locate OBJECT_METADATA events. Should the spec define a maximum scan-back depth, or leave this to the implementation? For Kafka-based producers, a separate schema topic may be more practical than scan-back -- should this be explicitly addressed?

- **Q7**
  - Question: _null_columns and _lob_overflow for partial UPDATE images
  - Status: NEW in v0.2. When a producer emits partial before/after images (changed columns only), _null_columns and _lob_overflow must distinguish between "column is null" and "column not included in this image". Should a third category (_unchanged_columns or similar) be defined to make the three states explicit?

# 11. References

- **CDC-OIS Specification Draft v0.1, March 2026**
  - Relevance: Primary specification document. Section 5 defines schema delivery model. Section 2 defines CloudEvents envelope. This proposal is an extension to and consistent with that specification.

- **CDC-OIS Data Type Survey v1.0, March 2026**
  - Relevance: Primary source document for all engine-specific type behaviors documented in this proposal

- **Oracle GoldenGate Data Streams Documentation (GoldenGate 26) docs.oracle.com/en/database/goldengate/core/26/coredoc/**
  - Relevance: Reference implementation for schema-before-first-use delivery model. Four record types (DDL, DML, OBJECT_METADATA, Data Streams Metadata) map directly to CDC-OIS event types.

- **Apache Arrow Columnar Format Specification arrow.apache.org/docs/format/Columnar.html**
  - Relevance: Type system inspiration; Decimal128/Decimal256, Duration, List, Struct, Union type definitions

- **ISO 8601:2019 -- Date and Time**
  - Relevance: Canonical wire encoding standard for all date, time, and duration values in DML payloads

- **OGC Simple Features Specification (SFS)**
  - Relevance: Well-Known Text (WKT) and Extended WKT (EWKT) geometry encoding standard

- **RFC 4122 -- UUID Format**
  - Relevance: Canonical UUID representation; baseline for UUID logical type. SQL Server UNIQUEIDENTIFIER deviation documented in Section 6.8.

- **IEEE 754-2008 -- Floating Point Arithmetic**
  - Relevance: Basis for FLOAT32, FLOAT64, and DECFLOAT special value handling

- **CloudEvents Specification v1.1 cloudevents.io**
  - Relevance: Envelope specification. cdcxid, cdctxorder, cdcpos defined as CloudEvents extension attributes.

- **Debezium Data Change Events Documentation debezium.io/documentation/reference/stable/**
  - Relevance: Reference implementation for schema-per-message pattern (not adopted) and LOB handling patterns

- **Oracle Database 23ai SQL Language Reference -- Data Types**
  - Relevance: Authoritative source for Oracle NUMBER, DATE, TIMESTAMP, INTERVAL, VECTOR, ANYDATA behaviors

- **PostgreSQL 17 Documentation -- Chapter 8: Data Types**
  - Relevance: Authoritative source for PostgreSQL NUMERIC, INTERVAL, range types, array types, tsvector

- **IBM Db2 LUW 12.1 SQL Reference -- DECFLOAT**
  - Relevance: Authoritative source for IEEE 754-2008 decimal float behavior and limitations

- **AWS DMS Source -- IBM Db2 LUW: Supported Data Types**
  - Relevance: Documents explicit non-support for DECFLOAT in CDC pipelines

OpenCDC Type System Proposal -- Draft v0.2 -- May 2026 -- CDC-OIS Working Group

CDC-OIS Working Group -- Confidential Draft
