#!/usr/bin/env bash
# Usage: set-fields.sh <item-id> [status] [type] [effort]
# status: backlog|ready|blocked|in_progress|done|-
# type: story|bug|task|spike|epic|-
# effort: xs|s|m|l|xl|xxl|-
# Pass "-" for any positional arg to skip it; trailing args may be
# omitted entirely.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

id="$1"
status="${2:--}"
type="${3:--}"
effort="${4:--}"

if [ "$status" != "-" ]; then
  status_option=$(resolve STATUS "$status" Status)
  gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
    --field-id "$STATUS_FIELD" --single-select-option-id "$status_option"
fi
if [ "$type" != "-" ]; then
  type_option=$(resolve TYPE "$type" Type)
  gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
    --field-id "$TYPE_FIELD" --single-select-option-id "$type_option"
fi
if [ "$effort" != "-" ]; then
  effort_option=$(resolve EFFORT "$effort" Effort)
  gh project item-edit --project-id "$PROJECT_ID" --id "$id" \
    --field-id "$EFFORT_FIELD" --single-select-option-id "$effort_option"
fi
