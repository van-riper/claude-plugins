#!/usr/bin/env bash
# Usage: create-item.sh [--number] [--epic <epic-slug>] <title> <body> <type> <effort>
# Always creates the item as Status: Backlog. type/effort are required -
# see SKILL.md's Fields section for valid values. With --number, prepends
# the next sequential ticket number (see next-number.sh) to the title as
# "<PROJECT_KEY>-N: <title>". With --epic <epic-slug>, also tags the new
# item's Epic reference field to <epic-slug> (see set-epic.sh). Flags may
# appear in either order before the positional args.
set -euo pipefail
script_dir="$(dirname "${BASH_SOURCE[0]}")"
source "$script_dir/lib.sh"

number=false
epic=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --number)
      number=true
      shift
      ;;
    --epic)
      epic="$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

if [ "$#" -lt 4 ]; then
  echo "Usage: create-item.sh [--number] [--epic <epic-slug>] <title> <body> <type> <effort>" >&2
  exit 1
fi

title="$1"
body="$2"
type="$3"
effort="$4"

status_option=$(resolve STATUS backlog Status)
type_option=$(resolve TYPE "$type" Type)
effort_option=$(resolve EFFORT "$effort" Effort)

if [ "$number" = true ]; then
  title="${PROJECT_KEY}-$("$script_dir/next-number.sh"): $title"
fi

id=$(gh project item-create "$PROJECT_NUM" --owner "$OWNER" \
  --title "$title" --body "$body" --format json | jq -r '.id')

gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$STATUS_FIELD" --single-select-option-id "$status_option"
gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$TYPE_FIELD" --single-select-option-id "$type_option"
gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$EFFORT_FIELD" --single-select-option-id "$effort_option"

if [ -n "$epic" ]; then
  "$script_dir/set-epic.sh" "$id" "$epic"
fi

echo "$id"
