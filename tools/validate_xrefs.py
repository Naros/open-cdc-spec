#!/usr/bin/env python3
"""OpenCDC working-group tool: validate prose cross-references.

Two modes:
  (default)   resolve every "Section N" / "Appendix X.N" reference in the spec
              body and in registry prose against real headings; fail on any
              unresolved reference.
  --snapshot  write ref -> heading-title pairs to a JSON file.
  --verify F  re-resolve every reference and compare the heading TITLE it now
              points at against the snapshot. This is the check a renumber
              needs: a uniform-offset error leaves every reference resolvable
              but pointing one section off, which the default mode cannot see.

Scope notes:
  * The Change Log is excluded (out of scope by working-group direction).
  * Fenced code blocks are excluded -- the operation-type vocabulary block
    contains '#' lines that are not headings, and comments that are not prose.
  * registry/requirements.yaml is scanned too: meta.intro contains a literal
    "(see Section 19)" that is injected verbatim into the generated Section 17
    and is invisible to every other tool.
  * The registry 'matrix' rows carry a sections: field that audit_register.py
    does not check at all; they are validated here.

Usage: python3 tools/validate_xrefs.py [spec.md] [requirements.yaml]
                                       [--snapshot F | --verify F]
"""
import re, sys, json, yaml

argv = sys.argv[1:]
snapshot_to = verify_from = None
args = []
i = 0
while i < len(argv):
    a = argv[i]
    if a == "--snapshot":
        snapshot_to = argv[i + 1] if i + 1 < len(argv) else None; i += 2
    elif a == "--verify":
        verify_from = argv[i + 1] if i + 1 < len(argv) else None; i += 2
    elif a.startswith("--"):
        i += 1
    else:
        args.append(a); i += 1
spec_p = args[0] if len(args) > 0 else "spec/OpenCDC-Specification.md"
yaml_p = args[1] if len(args) > 1 else "registry/requirements.yaml"

text = open(spec_p, encoding="utf-8").read()
reg = yaml.safe_load(open(yaml_p))

# ---------- scope ----------
cut = text.find("\n# Change Log")
body = text[:cut] if cut > 0 else text

def strip_fences(s):
    out, fenced = [], False
    for line in s.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else line)
    return "\n".join(out)

clean = strip_fences(body)

# ---------- headings: number -> title ----------
H = {}
for m in re.finditer(r"^#{1,4} (\d+(?:\.\d+)*[a-z]?)\.? +(.+)$", clean, re.M):
    H[m.group(1)] = m.group(2).strip()
for m in re.finditer(r"^#{1,4} ([AB]\.\d+(?:\.\d+)*) +(.+)$", clean, re.M):
    H[m.group(1)] = m.group(2).strip()
for m in re.finditer(r"^# Appendix ([AB]):(.*)$", clean, re.M):
    H[m.group(1)] = ("Appendix " + m.group(1) + ":" + m.group(2)).strip()

# ---------- references ----------
def line_of(src, pos):
    return src.count("\n", 0, pos) + 1

def ctxkey(src, a, b):
    """Stable identity for a reference SITE.

    Deliberately not the file path or line number: item 2 deletes whole
    sections, so every line below shifts and a line-keyed snapshot would
    silently match nothing. Instead: the surrounding prose with the number
    itself masked out, whitespace-normalised. A renumber changes the number
    and nothing else, so this key survives it."""
    left  = re.sub(r"\s+", " ", src[max(0, a - 70):a])[-70:]
    right = re.sub(r"\s+", " ", src[b:b + 70])[:70]
    return left + "<<#>>" + right

refs = []   # (kind, number, sitekey, human_origin)
seen = {}
for pat, kind in ((r"Section (\d+(?:\.\d+)*[a-z]?)", "Section"),
                  (r"Appendix ([AB](?:\.\d+(?:\.\d+)*)?)", "Appendix")):
    for m in re.finditer(pat, clean):
        k = ctxkey(clean, m.start(), m.end())
        seen[k] = seen.get(k, 0) + 1          # disambiguate identical contexts
        refs.append((kind, m.group(1), f"{k}#{seen[k]}",
                     f"{spec_p}:{line_of(clean, m.start())}"))

# registry prose (meta.*) -- a cross-reference can hide inside a YAML string
for k, v in (reg.get("meta") or {}).items():
    if isinstance(v, str):
        for m in re.finditer(r"Section (\d+(?:\.\d+)*[a-z]?)", v):
            refs.append(("Section", m.group(1), f"registry:meta.{k}", f"{yaml_p}:meta.{k}"))

# registry structured section fields
for r in reg.get("requirements", []):
    for s in r.get("sections", []):
        refs.append(("Section", str(s).replace("Appendix ", ""), f"registry:{r['id']}:{s}", f"{yaml_p}:{r['id']}"))
for row in reg.get("matrix", []):
    for s in row.get("sections", []):
        refs.append(("Section", str(s).replace("Appendix ", ""),
                     f"registry:matrix:{row['capability']}:{s}",
                     f"{yaml_p}:matrix[{row['capability'][:40]}]"))

# ---------- modes ----------
unresolved = [r for r in refs if r[1] not in H]

if snapshot_to:
    json.dump({"headings": H,
               "refs": [{"kind": k, "num": n, "site": sk, "origin": o,
                         "title": H.get(n)}
                        for k, n, sk, o in refs]},
              open(snapshot_to, "w"), indent=1, sort_keys=True)
    print(f"snapshot written: {snapshot_to}  ({len(refs)} refs, {len(H)} headings)")

fail = False
print(f"headings indexed  : {len(H)}")
print(f"references checked: {len(refs)}  ({spec_p} prose + {yaml_p})")
print(f"A) unresolved references: {len(unresolved)}")
for k, n, sk, o in unresolved:
    fail = True
    print(f"   UNRESOLVED  {k} {n}   <- {o}")

if verify_from:
    snap = json.load(open(verify_from))
    old = {(e["kind"], e["site"]): e["title"] for e in snap["refs"]}
    drift, unmatched = [], 0
    for k, n, sk, o in refs:
        key = (k, sk)
        if key not in old:
            unmatched += 1
            continue
        if H.get(n) != old[key]:
            drift.append((k, n, o, old[key], H.get(n)))
    if unmatched:
        print(f"   note: {unmatched} reference site(s) not present in snapshot "
              f"(new or reworded prose)")
    print(f"B) references now pointing at a different heading: {len(drift)}")
    for k, n, o, was, now in drift:
        fail = True
        print(f"   DRIFT  {k} {n} at {o}\n          was: {was}\n          now: {now}")

print("XREF " + ("FAIL" if fail else "PASS"))
sys.exit(1 if fail else 0)
