#!/usr/bin/env python3
"""OpenCDC working-group tool: regenerate Section 19.1 Compliance Matrix table
from the matrix section of requirements.yaml, or verify with --check.
Usage: python3 generate_matrix.py [--check] [spec.md] [requirements.yaml]"""
import re, sys, yaml

check = "--check" in sys.argv
args = [a for a in sys.argv[1:] if a != "--check"]
spec_path = args[0] if args else "OpenCDC-Specification.md"
yaml_path = args[1] if len(args) > 1 else "requirements.yaml"

text = open(spec_path, encoding="utf-8").read()
reg = yaml.safe_load(open(yaml_path))
known = {r["id"] for r in reg["requirements"]}
for row in reg["matrix"]:
    for rid in row.get("req_ids", []):
        assert rid in known, f"matrix references unknown requirement ID {rid}"

m = re.search(r"(## 19\.1 Compliance Matrix\n\n)(.*?)(^## 19\.2 Conformance Test Scenarios)", text, re.S | re.M)
assert m, "Section 19.1 boundaries not found"
intro = m.group(2).split("\n\n")[0]
tbl = [intro, "", "| Capability | Producer | Consumer | Both | Section | Requirements |", "|---|---|---|---|---|---|"]
for row in reg["matrix"]:
    tbl.append("| " + " | ".join([
        row["capability"], row.get("producer") or "", row.get("consumer") or "",
        row.get("both") or "", ", ".join(str(s) for s in row["sections"]),
        ", ".join(row.get("req_ids", []))]) + " |")
new = "\n".join(tbl) + "\n\n"
if check:
    if m.group(2) == new:
        print("CHECK PASS: Section 19.1 matches the register matrix.")
        sys.exit(0)
    print("CHECK FAIL: Section 19.1 has drifted from the register matrix.")
    sys.exit(1)
open(spec_path, "w", encoding="utf-8").write(text[:m.start(2)] + new + text[m.start(3):])
print(f"Regenerated Section 19.1 from {yaml_path} ({len(reg['matrix'])} rows).")
