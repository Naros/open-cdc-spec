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

def excise(txt, start, end):
    """Remove the section from `start` up to `end` (or EOF when end is absent
    or precedes start). Position-independent: works with the Change Log at
    either end of the document."""
    i = txt.find(start)
    if i < 0:
        return txt
    j = txt.find(end, i + len(start)) if end else -1
    return txt[:i] + (txt[j:] if j >= 0 else "")

body = excise(text, "# Change Log", "\n# Normative References")
body = excise(body, "# 17. Normative Summary", "# 18. Design Decision Record")

fail = False
unanchored = [rid for rid in reg_ids if not re.search(r"\b" + re.escape(rid) + r"\b", body)]
print(f"A) Register IDs anchored in body: {len(reg_ids)-len(unanchored)}/{len(reg_ids)}")
if unanchored:
    fail = True
    for rid in unanchored: print(f"   UNANCHORED: {rid}")

tok_re = re.compile(r"\b(?:P|C|R|S)-[A-Z]+-\d+(?:-[A-Z]{2})?\b|\bT-[A-Z]+(?:-[A-Z]{2})?\b")  # T-NN test ids excluded; -MC/-SC suffixes captured
BODY_ONLY = {"P-ORD-1-MC", "T-NOINTERLEAVE-MC", "C-ORD-3-MC",
             "P-ORD-6-MC", "R-POS-2-MC"}          # multi-channel profile variants: body prose only
UNREGISTERED_OK = {"R-POS-7", "P-RET-1"}           # binding-defined delivery-layer duties (Section 12 charter; body-labelled)
missing = sorted(set(tok_re.findall(body)) - set(reg_ids) - BODY_ONLY - UNREGISTERED_OK)
print(f"B) Body requirement-ID tokens not in register: {len(missing)}")
if missing:
    fail = True
    for t in missing: print(f"   MISSING FROM REGISTER: {t}")

headings = set()
for hm in re.finditer(r"^#{1,3} (\d+(?:\.\d+)*[a-z]?)|^## (A\.\d+)", text, re.M):
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
