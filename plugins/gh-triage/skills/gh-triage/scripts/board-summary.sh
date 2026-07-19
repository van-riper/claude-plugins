#!/usr/bin/env bash
# Usage: board-summary.sh
# Prints Status counts - a one-call orientation dump for the start of a
# session.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

echo "== Status counts =="
list_items | jq -r '.items | group_by(.status) | map({status: .[0].status, count: length}) | .[] | "\(.status): \(.count)"'
