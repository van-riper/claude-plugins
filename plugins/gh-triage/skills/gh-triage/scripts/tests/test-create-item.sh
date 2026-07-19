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
repo=$(setup_stub_project '{"items":[{"title":"ABC-4: existing"}]}')
(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/create-item.sh --number "New" "body" bug s >/dev/null)
grep -q -- "--title ABC-5: New" "$repo/gh-calls.log" \
  || fail "expected title prefixed ABC-5:"

# Case 4: --epic tags the new item's Epic field with the given slug
repo=$(setup_stub_project '{"items":[]}')
(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/create-item.sh --epic onboarding-rework "New" "body" bug s >/dev/null)
grep -q -- "--field-id field_epic --text onboarding-rework" "$repo/gh-calls.log" \
  || fail "expected Epic field set to onboarding-rework"

# Case 5: a mistyped type/effort key fails loudly instead of forwarding
# an empty --single-select-option-id to gh
repo=$(setup_stub_project '{"items":[]}')
if (cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/create-item.sh "t" "b" "tsak" m 2>/dev/null); then
  fail "expected an error on an invalid type key"
fi

echo "PASS: test-create-item.sh"
