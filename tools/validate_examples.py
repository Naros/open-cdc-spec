#!/usr/bin/env python3
"""OpenCDC working-group tool: validate every event in PayloadExamples against
the companion JSON Schemas (envelope + per-type data payload).
Usage: python3 validate_examples.py [PayloadExamples.md] [schemas_dir]"""
import json, os, re, sys
from jsonschema import Draft202012Validator

md_path = sys.argv[1] if len(sys.argv) > 1 else "OpenCDC-PayloadExamples.md"
sdir = sys.argv[2] if len(sys.argv) > 2 else "schemas"

def load(name):
    # Canonical filename is <name>.schema.json; some environments (e.g. the
    # Claude project sandbox) normalize dots in filenames to underscores,
    # producing <name>_schema.json. Try both so the tool works everywhere.
    for path in (f"{sdir}/{name}.schema.json", f"{sdir}/{name}_schema.json"):
        if os.path.exists(path):
            return Draft202012Validator(json.load(open(path)))
    raise FileNotFoundError(
        f"Schema not found for '{name}' in '{sdir}' "
        f"(tried {name}.schema.json and {name}_schema.json)")

ENV = load("opencdc-envelope")
PAYLOAD = {
    "OBJECT_METADATA": load("opencdc-object-metadata"),
    "STREAM_METADATA": load("opencdc-stream-metadata"),
    "HEARTBEAT": load("opencdc-heartbeat"),
    "DML": load("opencdc-dml"),
    "DDL": load("opencdc-ddl"),
    "TRX_COMMIT": load("opencdc-trx-commit"),
}

def strip_comments(block):
    block = re.sub(r"(?m)^\s*//.*$", "", block)        # full-line comments
    block = re.sub(r"(?m)[ \t]{2,}//.*$", "", block)    # trailing aligned comments
    block = re.sub(r",\s*(\}|\])", r"\1", block)         # trailing commas
    return block

text = open(md_path, encoding="utf-8").read()
blocks = re.findall(r"```json\n(.*?)```", text, re.S)
print(f"Found {len(blocks)} JSON example blocks\n")

failures = 0
for i, raw in enumerate(blocks, 1):
    try:
        ev = json.loads(strip_comments(raw))
    except json.JSONDecodeError as e:
        print(f"[{i}] PARSE FAIL: {e}")
        failures += 1
        continue
    etype = ev.get("type", "?")
    op = etype.rsplit(".", 1)[-1]
    if ".dml." in etype or ".snapshot." in etype:
        pkey = "DML"
    elif ".ddl." in etype:
        pkey = "DDL"
    else:
        pkey = op  # meta.X
    label = f"[{i}] {etype}"
    errs = []
    for e in ENV.iter_errors(ev):
        errs.append(("envelope", "/".join(str(p) for p in e.path) or "(root)", e.message))
    pv = PAYLOAD.get(pkey)
    if pv is None:
        errs.append(("payload", "(root)", f"no schema for event class '{pkey}'"))
    else:
        for e in pv.iter_errors(ev.get("data", {})):
            errs.append(("payload", "/".join(str(p) for p in e.path) or "(root)", e.message))
    if errs:
        failures += 1
        print(f"{label}: FAIL ({len(errs)} issue(s))")
        for layer, path, msg in errs:
            print(f"    [{layer}] at {path}: {msg[:140]}")
    else:
        print(f"{label}: PASS")

print(f"\n{len(blocks) - failures}/{len(blocks)} events fully conformant")
sys.exit(1 if failures else 0)
