#!/usr/bin/env bash
# Usage: find-item.sh <title-keyword-regex>
# Prints matching items as JSON, including .id (PVTI_...) and
# .content.id (DI_..., needed to edit title/body).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [ "$#" -ne 1 ]; then
  echo "Usage: find-item.sh <title-keyword-regex>" >&2
  exit 1
fi

list_items | jq --arg kw "$1" '.items[] | select(.title | test($kw; "i"))'
