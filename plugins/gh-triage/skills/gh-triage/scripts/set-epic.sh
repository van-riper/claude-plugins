#!/usr/bin/env bash
# Usage: set-epic.sh <item-id> <epic-id>
# Sets an item's Epic reference (the Epic Text field) to <epic-id> - the
# parent epic's plain item ID string (e.g. "ETYM-2"), not the epic's own
# item id (PVTI_...). No check that <epic-id> is an existing Epic item.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [ "$#" -ne 2 ]; then
  echo "Usage: set-epic.sh <item-id> <epic-id>" >&2
  exit 1
fi

id="$1"
epic_id="$2"

gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$EPIC_FIELD" --text "$epic_id"
