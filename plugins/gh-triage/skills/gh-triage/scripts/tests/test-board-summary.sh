#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source harness.sh

fail() { echo "FAIL: $1" >&2; exit 1; }

items='{"items":[{"status":"Backlog"},{"status":"Backlog"},{"status":"Done"}]}'
repo=$(setup_stub_project "$items")
out=$(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/board-summary.sh)
echo "$out" | grep -q "^Backlog: 2$" || fail "expected Backlog: 2"
echo "$out" | grep -q "^Done: 1$" || fail "expected Done: 1"

echo "PASS: test-board-summary.sh"
