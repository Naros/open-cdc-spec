#!/usr/bin/env bash
# OpenCDC working-group check runner.
# Run from repo root: ./check.sh
# Exit non-zero on any failure.
set -euo pipefail

SPEC="spec/OpenCDC-Specification.md"
REG="registry/requirements.yaml"
EXAMPLES="examples/OpenCDC-PayloadExamples.md"
SCHEMAS="schemas"

# Documents that carry a generated TOC (flat-structure docs like GLOSSARY excluded)
TOC_DOCS="spec/OpenCDC-Specification.md spec/OpenCDC-TypeSystem.md spec/OpenCDC-ArchitectureDecisionRecord.md spec/OpenCDC-UserStories.md examples/OpenCDC-PayloadExamples.md"

PASS=0
FAIL=0

run() {
    local label="$1"; shift
    printf "%-45s" "  $label"
    if "$@" > /tmp/opencdc_check_out 2>&1; then
        echo "PASS"
        ((PASS++)) || true
    else
        echo "FAIL"
        cat /tmp/opencdc_check_out
        ((FAIL++)) || true
    fi
}

echo "OpenCDC check suite"
echo "==================="

echo ""
echo "Register checks"
run "Section 17 drift"    python3 tools/generate_sec17.py --check "$SPEC" "$REG"
run "Section 19.1 drift"  python3 tools/generate_matrix.py --check "$SPEC" "$REG"
run "Register <-> body"   python3 tools/audit_register.py "$SPEC" "$REG"

echo ""
echo "Version manifest"
run "versions.yaml agreement" python3 tools/check_versions.py "$SPEC" registry/versions.yaml "$REG"

echo ""
echo "Navigation checks"
run "Tables of contents"  python3 tools/generate_toc.py --check $TOC_DOCS

echo ""
echo "Schema validation"
run "Payload examples"    python3 tools/validate_examples.py "$EXAMPLES" "$SCHEMAS"

echo ""
echo "==================="
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
