#!/usr/bin/env bash
# Usage: refresh-ids.sh
# Prints current field/option IDs - run when an item-edit call fails with
# a "not found" error, meaning a field was deleted/recreated, or when
# bootstrapping gh-triage.conf.sh for a new project. Update
# gh-triage.conf.sh by hand from the result.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

gh project field-list "$PROJECT_NUM" --owner "$OWNER" --format json
