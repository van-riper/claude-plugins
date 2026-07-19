#!/usr/bin/env bash
# Loads this repo's gh-triage config and exposes it to the other
# scripts in this folder. Project number/owner/field IDs are consumer
# specific, so they live in gh-triage.conf.sh at the repo root,
# not here - copy gh-triage.conf.sh.example from the plugin and
# fill it in with your own project's IDs (see refresh-ids.sh).
set -euo pipefail

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "error: lib.sh is a library sourced by the other scripts in this" >&2
  echo "folder - it isn't meant to be run directly." >&2
  exit 1
fi

repo_root=$(git rev-parse --show-toplevel)
conf="$repo_root/gh-triage.conf.sh"

if [ ! -f "$conf" ]; then
  echo "error: $conf not found." >&2
  echo "Copy gh-triage.conf.sh.example from the plugin to" >&2
  echo "$repo_root and fill in your project's IDs. Run refresh-ids.sh" >&2
  echo "once you have PROJECT_NUM/OWNER set to discover the field IDs." >&2
  exit 1
fi

source "$conf"

# Shared by next-number.sh/find-item.sh/board-summary.sh. `gh project
# item-list` requires an explicit --limit (default 30) and silently
# caps output there instead of erroring, so a hardcoded --limit would
# silently truncate once a board grows past it. Ask for the project's
# actual item count first (a cheap --limit 1 call still reports the
# true .totalCount), then fetch exactly that many.
list_items() {
  local total
  total=$(gh project item-list "$PROJECT_NUM" --owner "$OWNER" \
    --format json --limit 1 | jq -r '.totalCount')
  gh project item-list "$PROJECT_NUM" --owner "$OWNER" \
    --format json --limit "$total"
}

# resolve <map-name> <key> <field-label>
# Looks up <key> in the named STATUS/TYPE/EFFORT associative array and
# prints its option id, or fails loudly with the valid keys instead of
# forwarding an empty --single-select-option-id to `gh` on a typo or an
# unresolved ("not found") config entry.
resolve() {
  local -n map="$1"
  local key="$2" label="$3"
  if [ -z "${map[$key]:-}" ]; then
    echo "error: invalid $label '$key' - expected one of: ${!map[*]}" >&2
    exit 1
  fi
  echo "${map[$key]}"
}
