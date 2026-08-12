#!/usr/bin/env python3
"""OpenCDC working-group tool: regenerate Section 17 Normative Summary from
requirements.yaml, or verify they match (--check). MUST / MUST NOT entries
render; SHOULD entries are register-only.
Usage: python3 generate_sec17.py [--check] [spec.md] [requirements.yaml]"""
import re, sys, yaml

check = "--check" in sys.argv
args = [a for a in sys.argv[1:] if a != "--check"]
spec_path = args[0] if len(args) > 0 else "OpenCDC-Specification.md"
yaml_path = args[1] if len(args) > 1 else "requirements.yaml"

text = open(spec_path, encoding="utf-8").read()
reg = yaml.safe_load(open(yaml_path))
m = re.search(r"(# 17\. Normative Summary\n)(.*?)(^# 18\. Design Decision Record)", text, re.S | re.M)
assert m, "Section 17 boundaries not found"

PARTIES = ("Producer", "Both", "Delivery Layer")   # Consumer entries are register-only (D-8)

out = ["\n" + reg["meta"]["intro"].strip() + "\n"]
for r in reg["requirements"]:
    if r["level"] not in ("MUST", "MUST NOT"):
        continue
    if r["who"] not in PARTIES:                       # skips who: Consumer
        continue
    q = r.get("qualifier")
    head = f"{r['id']} ({q})" if q else r["id"]
    # binds_when is structured metadata for the auditor and conformance harness; never rendered.
    out.append(f"\n- **{head}**\n  - Requirement: {r['requirement']}\n"
               f"  - Who: {r['who']}\n  - Section: {', '.join(str(s) for s in r['sections'])}\n")
new17 = "".join(out) + "\n"

if check:
    if m.group(2) == new17:
        print("CHECK PASS: Section 17 matches the register.")
        sys.exit(0)
    print("CHECK FAIL: Section 17 has drifted from the register. Regenerate or update the register.")
    sys.exit(1)
open(spec_path, "w", encoding="utf-8").write(text[:m.start(2)] + new17 + text[m.start(3):])
n = sum(1 for r in reg["requirements"]
        if r["level"] in ("MUST", "MUST NOT") and r["who"] in PARTIES)
print(f"Regenerated Section 17 from {yaml_path} ({n} entries).")
