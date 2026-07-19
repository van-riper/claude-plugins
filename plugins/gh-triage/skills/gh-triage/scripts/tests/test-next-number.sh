#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source harness.sh

fail() { echo "FAIL: $1" >&2; exit 1; }

# Case 1: two prior ABC- items, next should be 8
items='{"items":[{"title":"ABC-5: thing"},{"title":"ABC-7: other thing"}]}'
repo=$(setup_stub_project "$items")
got=$(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/next-number.sh)
[ "$got" = "8" ] || fail "expected 8, got $got"

# Case 2: a title with leading digits but no PROJECT_KEY prefix must not
# be counted (this is the bug the prefix-anchored regex fixes)
items='{"items":[{"title":"2026 roadmap"},{"title":"ABC-3: thing"}]}'
repo=$(setup_stub_project "$items")
got=$(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/next-number.sh)
[ "$got" = "4" ] || fail "expected 4 (ignoring the non-prefixed title), got $got"

# Case 3: no items at all yet, next should be 1
items='{"items":[]}'
repo=$(setup_stub_project "$items")
got=$(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/next-number.sh)
[ "$got" = "1" ] || fail "expected 1 on an empty project, got $got"

echo "PASS: test-next-number.sh"
