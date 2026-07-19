#!/usr/bin/env bash
# Shared setup for gh-triage script self-checks. Not a test
# framework - just the temp-repo/stub-gh scaffolding every script test
# needs, since lib.sh always resolves a real git root and calls the real
# `gh` binary.
set -euo pipefail

# setup_stub_project <items-json>
# Creates a throwaway git repo with a fake gh-triage.conf.sh and a
# stub `gh` on PATH that serves <items-json> for `gh project item-list`
# and logs every other `gh` invocation to gh-calls.log for assertions.
# Prints the repo path on stdout; scripts under test are copied into
# <repo>/scripts/.
setup_stub_project() {
  local items_json="$1"
  local repo scripts_src
  repo=$(mktemp -d)
  scripts_src="$(cd "$(dirname "${BASH_SOURCE[1]}")/.." && pwd)"

  git -C "$repo" init -q

  cat > "$repo/gh-triage.conf.sh" <<'EOF'
PROJECT_KEY=ETYM
PROJECT_NUM=1
OWNER=test-owner
PROJECT_ID=PVT_test
STATUS_FIELD=field_status
TYPE_FIELD=field_type
EFFORT_FIELD=field_effort
declare -A STATUS=( [backlog]=opt_backlog [ready]=opt_ready [blocked]=opt_blocked [in_progress]=opt_inprogress [done]=opt_done )
declare -A TYPE=( [story]=opt_story [bug]=opt_bug [task]=opt_task [spike]=opt_spike [epic]=opt_epic )
declare -A EFFORT=( [xs]=opt_xs [s]=opt_s [m]=opt_m [l]=opt_l [xl]=opt_xl [xxl]=opt_xxl )
EOF

  mkdir -p "$repo/bin"
  cat > "$repo/bin/gh" <<EOF
#!/usr/bin/env bash
echo "\$*" >> "$repo/gh-calls.log"
if [[ "\$*" == *"item-list"* ]]; then
  count_file="$repo/.item-list-calls"
  n=\$(( \$(cat "\$count_file" 2>/dev/null || echo 0) + 1 ))
  echo "\$n" > "\$count_file"
  if [ "\$n" -eq 1 ]; then
    count=\$(echo '$items_json' | jq '.items | length')
    echo '{"totalCount": '"\$count"'}'
  else
    echo '$items_json'
  fi
else
  echo '{"id":"PVTI_stub"}'
fi
EOF
  chmod +x "$repo/bin/gh"

  mkdir -p "$repo/scripts"
  cp "$scripts_src"/*.sh "$repo/scripts/"

  echo "$repo"
}
