#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source harness.sh

fail() { echo "FAIL: $1" >&2; exit 1; }

# Case 1: type/effort are required - omitting either is a usage error
repo=$(setup_stub_project '{"items":[]}')
if (cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/create-item.sh "t" "b" "task" 2>/dev/null); then
  fail "expected usage error when effort is omitted"
fi

# Case 2: a full call sets Status:Backlog + the given Type/Effort options
repo=$(setup_stub_project '{"items":[]}')
(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/create-item.sh "My title" "body" task m >/dev/null)
log="$repo/gh-calls.log"
grep -q -- "--field-id field_status --single-select-option-id opt_backlog" "$log" \
  || fail "expected Status set to backlog"
grep -q -- "--field-id field_type --single-select-option-id opt_task" "$log" \
  || fail "expected Type set to task"
grep -q -- "--field-id field_effort --single-select-option-id opt_m" "$log" \
  || fail "expected Effort set to m"

# Case 3: --number prepends PROJECT_KEY-N
repo=$(setup_stub_project '{"items":[{"title":"ETYM-4: existing"}]}')
(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/create-item.sh --number "New" "body" bug s >/dev/null)
grep -q -- "--title ETYM-5: New" "$repo/gh-calls.log" \
  || fail "expected title prefixed ETYM-5:"

echo "PASS: test-create-item.sh"
