#!/usr/bin/env python3
"""OpenCDC working-group tool: assert the version manifest (versions.yaml)
agrees with the specification header and the requirements register.
Usage: python3 tools/check_versions.py [spec.md] [versions.yaml] [requirements.yaml]"""
import re, sys, yaml

spec_p = sys.argv[1] if len(sys.argv) > 1 else "spec/OpenCDC-Specification.md"
ver_p  = sys.argv[2] if len(sys.argv) > 2 else "registry/versions.yaml"
reg_p  = sys.argv[3] if len(sys.argv) > 3 else "registry/requirements.yaml"

spec = open(spec_p, encoding="utf-8").read()
ver  = yaml.safe_load(open(ver_p))
reg  = yaml.safe_load(open(reg_p))

fail = False
def check(label, got, want):
    global fail
    ok = str(got) == str(want)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: manifest={want!r} observed={got!r}")
    fail |= not ok

m = re.match(r"OpenCDC Specification -- Draft v([0-9.]+)", spec)
check("spec header version", m.group(1) if m else None, ver["documents"]["specification"]["version"])
check("register tracks spec", reg["meta"]["spec_version"], ver["documents"]["specification"]["version"])
wm = re.search(r'"cdcspecversion":\s*"([0-9.]+)"', spec)
check("wire version in spec examples", wm.group(1) if wm else None, ver["wire_protocol"])
sys.exit(1 if fail else 0)
