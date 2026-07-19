#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source harness.sh

fail() { echo "FAIL: $1" >&2; exit 1; }

# Case 1: "-" skips a field entirely (no matching gh call logged)
repo=$(setup_stub_project '{"items":[]}')
(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/set-fields.sh PVTI_x - spike -)
log="$repo/gh-calls.log"
grep -q -- "field_status" "$log" && fail "expected no Status call when status is -"
grep -q -- "--field-id field_type --single-select-option-id opt_spike" "$log" \
  || fail "expected Type set to spike"
grep -q -- "field_effort" "$log" && fail "expected no Effort call when effort omitted"

# Case 2: a real status value sets the right option id
repo=$(setup_stub_project '{"items":[]}')
(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/set-fields.sh PVTI_x blocked - -)
grep -q -- "--field-id field_status --single-select-option-id opt_blocked" "$repo/gh-calls.log" \
  || fail "expected Status set to blocked"

echo "PASS: test-set-fields.sh"
