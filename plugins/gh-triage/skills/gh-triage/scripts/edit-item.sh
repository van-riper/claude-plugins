#!/usr/bin/env bash
# Usage: edit-item.sh <content-id> [title] [body]
# Pass "-" (or omit) to leave a field unchanged. Content id is the
# DI_... id (from find-item.sh's .content.id), not the item id
# (PVTI_...) used by set-fields.sh.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [ "$#" -lt 1 ]; then
  echo "Usage: edit-item.sh <content-id> [title] [body]" >&2
  exit 1
fi

content_id="$1"
title="${2:--}"
body="${3:--}"

args=(--project-id "$PROJECT_ID" --id "$content_id")
if [ "$title" != "-" ]; then
  args+=(--title "$title")
fi
if [ "$body" != "-" ]; then
  args+=(--body "$body")
fi

gh project item-edit "${args[@]}"
