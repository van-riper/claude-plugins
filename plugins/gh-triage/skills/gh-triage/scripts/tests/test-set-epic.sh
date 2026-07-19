#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source harness.sh

fail() { echo "FAIL: $1" >&2; exit 1; }

# Case 1: usage error when epic-slug is omitted
repo=$(setup_stub_project '{"items":[]}')
if (cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/set-epic.sh PVTI_x 2>/dev/null); then
  fail "expected usage error when epic-slug is omitted"
fi

# Case 2: sets the Epic Text field to the given epic slug
repo=$(setup_stub_project '{"items":[]}')
(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/set-epic.sh PVTI_x onboarding-rework)
grep -q -- "--field-id field_epic --text onboarding-rework" "$repo/gh-calls.log" \
  || fail "expected Epic field set to onboarding-rework"

echo "PASS: test-set-epic.sh"
