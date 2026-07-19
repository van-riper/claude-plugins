#!/usr/bin/env bash
# Usage: create-item.sh [--number] <title> <body> [priority] [target]
# Always creates the item as Status: Open. priority/target default to
# low/later if omitted. With --number, prepends the next sequential
# ticket number (see next-number.sh) to the title as "N: <title>".
set -euo pipefail
script_dir="$(dirname "${BASH_SOURCE[0]}")"
source "$script_dir/lib.sh"

number=false
if [ "${1:-}" = "--number" ]; then
  number=true
  shift
fi

title="$1"
body="$2"
priority="${3:-low}"
target="${4:-later}"

if [ "$number" = true ]; then
  title="$("$script_dir/next-number.sh"): $title"
fi

id=$(gh project item-create "$PROJECT_NUM" --owner "$OWNER" \
  --title "$title" --body "$body" --format json | jq -r '.id')

gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$STATUS_FIELD" --single-select-option-id "${STATUS[open]}"
gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$PRIORITY_FIELD" --single-select-option-id "${PRIORITY[$priority]}"
gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$TARGET_FIELD" --single-select-option-id "${TARGET[$target]}"

echo "$id"
