#!/usr/bin/env bash
# Usage: archive-item.sh <item-id>
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [ "$#" -ne 1 ]; then
  echo "Usage: archive-item.sh <item-id>" >&2
  exit 1
fi

gh project item-archive "$PROJECT_NUM" --owner "$OWNER" --id "$1"
