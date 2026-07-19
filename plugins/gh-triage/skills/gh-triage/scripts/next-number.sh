#!/usr/bin/env bash
# Usage: next-number.sh
# Prints the next sequential ticket number for a new item's title prefix.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

list_items | jq -r '.items[].title' | grep -oE '^[0-9]+' | sort -n | tail -1 \
  | awk '{print $1 + 1}'
