#!/usr/bin/env python3
"""OpenCDC working-group tool: two-way audit between the requirements register
and the specification body.
A) every register ID must be anchored in body text (changelog and Section 17 excluded)
B) every requirement-ID token in the body must exist in the register
   (T-NN conformance test scenario ids are a separate namespace and are skipped)
C) every register section reference must resolve to a real heading
Usage: python3 tools/audit_register.py [spec.md] [requirements.yaml]"""
import re, sys, yaml

SPEC = sys.argv[1] if len(sys.argv) > 1 else "OpenCDC-Specification.md"
YAMLP = sys.argv[2] if len(sys.argv) > 2 else "requirements.yaml"
text = open(SPEC, encoding="utf-8").read()
reg = yaml.safe_load(open(YAMLP))
reg_ids = [r["id"] for r in reg["requirements"]]

pre_cl, rest = text.split("# Change Log", 1)
_, after_cl = rest.split("# Normative References", 1)
full = pre_cl + "# Normative References" + after_cl
pre17, rest2 = full.split("# 17. Normative Summary", 1)
_, post17 = rest2.split("# 18. Design Decision Record", 1)
body = pre17 + post17

fail = False
unanchored = [rid for rid in reg_ids if not re.search(r"\b" + re.escape(rid) + r"\b", body)]
print(f"A) Register IDs anchored in body: {len(reg_ids)-len(unanchored)}/{len(reg_ids)}")
if unanchored:
    fail = True
    for rid in unanchored: print(f"   UNANCHORED: {rid}")

tok_re = re.compile(r"\b(?:P|C|R|S)-[A-Z]+-\d+\b|\bT-[A-Z]+\b")  # T-NN test ids excluded
missing = sorted(set(tok_re.findall(body)) - set(reg_ids))
print(f"B) Body requirement-ID tokens not in register: {len(missing)}")
if missing:
    fail = True
    for t in missing: print(f"   MISSING FROM REGISTER: {t}")

headings = set()
for hm in re.finditer(r"^#{1,3} (\d+(?:\.\d+)*)|^## (A\.\d+)", text, re.M):
    headings.add(hm.group(1) or hm.group(2))
bad = []
for r in reg["requirements"]:
    for s in r["sections"]:
        if str(s).replace("Appendix ", "") not in headings:
            bad.append((r["id"], str(s)))
print(f"C) Unresolved register section references: {len(bad)}")
if bad:
    fail = True
    for rid, s in bad: print(f"   {rid} -> '{s}'")

print("AUDIT " + ("FAIL" if fail else "PASS"))
sys.exit(1 if fail else 0)
