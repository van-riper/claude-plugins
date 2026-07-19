#!/usr/bin/env bash
# Usage: create-item.sh [--number] <title> <body> <type> <effort>
# Always creates the item as Status: Backlog. type/effort are required -
# see SKILL.md's Fields section for valid values. With --number, prepends
# the next sequential ticket number (see next-number.sh) to the title as
# "<PROJECT_KEY>-N: <title>".
set -euo pipefail
script_dir="$(dirname "${BASH_SOURCE[0]}")"
source "$script_dir/lib.sh"

number=false
if [ "${1:-}" = "--number" ]; then
  number=true
  shift
fi

if [ "$#" -lt 4 ]; then
  echo "Usage: create-item.sh [--number] <title> <body> <type> <effort>" >&2
  exit 1
fi

title="$1"
body="$2"
type="$3"
effort="$4"

if [ "$number" = true ]; then
  title="${PROJECT_KEY}-$("$script_dir/next-number.sh"): $title"
fi

id=$(gh project item-create "$PROJECT_NUM" --owner "$OWNER" \
  --title "$title" --body "$body" --format json | jq -r '.id')

gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$STATUS_FIELD" --single-select-option-id "${STATUS[backlog]}"
gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$TYPE_FIELD" --single-select-option-id "${TYPE[$type]}"
gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$EFFORT_FIELD" --single-select-option-id "${EFFORT[$effort]}"

echo "$id"
