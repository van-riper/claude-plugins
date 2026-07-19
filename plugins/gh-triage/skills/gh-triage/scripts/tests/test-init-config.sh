#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

fail() { echo "FAIL: $1" >&2; exit 1; }

scripts_src="$(cd .. && pwd)"

# setup_bare_repo <field-list-json>
# A repo with no gh-triage.conf.sh yet and a stub gh answering
# `project view`/`field-list`, unlike harness.sh's setup_stub_project
# (which always pre-writes a conf and stubs item-list instead).
setup_bare_repo() {
  local fields_json="$1" repo
  repo=$(mktemp -d)
  git -C "$repo" init -q
  mkdir -p "$repo/bin"
  cat > "$repo/bin/gh" <<STUB
#!/usr/bin/env bash
if [[ "\$*" == *"project view"* ]]; then
  echo '{"id":"PVT_test"}'
elif [[ "\$*" == *"field-list"* ]]; then
  echo '$fields_json'
fi
STUB
  chmod +x "$repo/bin/gh"
  mkdir -p "$repo/scripts"
  cp "$scripts_src"/*.sh "$repo/scripts/"
  echo "$repo"
}

FULL_FIELDS='{"fields":[
  {"id":"F_status","name":"Status","options":[
    {"id":"O_backlog","name":"Backlog"},{"id":"O_ready","name":"Ready"},
    {"id":"O_blocked","name":"Blocked"},{"id":"O_inprogress","name":"In Progress"},
    {"id":"O_done","name":"Done"}]},
  {"id":"F_type","name":"Type","options":[
    {"id":"O_story","name":"Story"},{"id":"O_bug","name":"Bug"},{"id":"O_task","name":"Task"},
    {"id":"O_spike","name":"Spike"},{"id":"O_epic","name":"Epic"}]},
  {"id":"F_effort","name":"Effort","options":[
    {"id":"O_xs","name":"XS"},{"id":"O_s","name":"S"},{"id":"O_m","name":"M"},
    {"id":"O_l","name":"L"},{"id":"O_xl","name":"XL"},{"id":"O_xxl","name":"XXL"}]},
  {"id":"F_epic","name":"Epic","options":[]}
]}'

# Case 1: a full field-list resolves every field/option, none left blank
repo=$(setup_bare_repo "$FULL_FIELDS")
(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/init-config.sh 1 test-owner ETYM)
conf="$repo/gh-triage.conf.sh"
[ -f "$conf" ] || fail "expected gh-triage.conf.sh to be written"
grep -q "=  # not found" "$conf" && fail "expected every field/option to resolve"
grep -q "STATUS_FIELD=F_status" "$conf" || fail "expected STATUS_FIELD resolved"
grep -qF "[backlog]=O_backlog" "$conf" || fail "expected backlog option resolved"

# Case 2: refuses to overwrite an existing conf file
if (cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/init-config.sh 1 test-owner ETYM 2>/dev/null); then
  fail "expected init-config.sh to refuse an existing conf file"
fi

# Case 3: a field the project doesn't have is left "not found", not guessed
repo=$(setup_bare_repo '{"fields":[{"id":"F_status","name":"Status","options":[{"id":"O_backlog","name":"Backlog"}]}]}')
(cd "$repo" && PATH="$repo/bin:$PATH" bash scripts/init-config.sh 1 test-owner ETYM)
grep -q -- "TYPE_FIELD=  # not found" "$repo/gh-triage.conf.sh" \
  || fail "expected TYPE_FIELD left as not found"

echo "PASS: test-init-config.sh"
