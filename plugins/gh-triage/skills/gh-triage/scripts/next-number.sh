#!/usr/bin/env bash
# Usage: next-number.sh
# Prints the next sequential ticket number for a new item's title prefix
# (e.g. 8, for a title of "ETYM-8: ..."). Anchored on the configured
# PROJECT_KEY so a draft item that happens to start with digits for
# unrelated reasons (not created through create-item.sh) can't get
# miscounted as a ticket ID.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

highest=$(list_items | jq -r '.items[].title' \
  | { grep -oE "^${PROJECT_KEY}-[0-9]+" || true; } \
  | { grep -oE '[0-9]+$' || true; } \
  | sort -n | tail -1)
echo "$((${highest:-0} + 1))"
