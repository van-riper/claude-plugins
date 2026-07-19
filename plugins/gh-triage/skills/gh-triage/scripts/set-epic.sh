#!/usr/bin/env bash
# Usage: set-epic.sh <item-id> <epic-slug>
# Sets an item's Epic reference (the Epic Text field) to <epic-slug> - a
# snapshot of the parent epic's slug (the "Slug: <slug>" first line of
# the epic's own body, e.g. "onboarding-rework"), not the epic's item ID
# or item id (PVTI_...). No check that <epic-slug> matches an existing
# Epic item's current slug.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [ "$#" -ne 2 ]; then
  echo "Usage: set-epic.sh <item-id> <epic-slug>" >&2
  exit 1
fi

id="$1"
epic_slug="$2"

gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
  --field-id "$EPIC_FIELD" --text "$epic_slug"
