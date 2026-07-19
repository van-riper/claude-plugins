#!/usr/bin/env bash
# Usage: archive-item.sh <item-id>
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

gh project item-archive "$PROJECT_NUM" --owner "$OWNER" --id "$1"
