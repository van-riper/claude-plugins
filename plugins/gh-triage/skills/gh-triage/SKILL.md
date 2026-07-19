---
name: gh-triage
description: Use when adding, updating, or triaging backlog/roadmap items on a GitHub Project (v2) board via `gh project`. Covers the gh project commands, field/option IDs, and a Status/Priority/Target/Blocked/Decision/Active workflow.
---

## Setup (once per repo)

This skill needs a `gh-triage.conf.sh` file at your repo root
holding your project's number, owner, and field/option IDs - GitHub's
project GraphQL API takes opaque IDs, not field/option names, so every
script below needs them resolved up front.

1. Get your project's number and owner from its URL
   (`github.com/<owner>/projects/<num>` or
   `github.com/orgs/<owner>/projects/<num>`).
2. Run `scripts/init-config.sh <project-num> <owner>` from your repo
   root. It resolves the project ID and every field/option ID via `gh`
   and writes `gh-triage.conf.sh`, matching field/option names
   to the Status/Priority/Target/Blocked/Decision/Active model
   case-insensitively.
3. Review the generated file. Anything the script couldn't match by
   name is left as `# not found` - either fill it in by hand from
   `scripts/refresh-ids.sh`'s output, or delete it (and the matching
   arguments in `set-fields.sh` calls) if your project doesn't have that
   field.

If you'd rather not query `gh` at setup time, copy
`gh-triage.conf.sh.example` (bundled with this plugin) to your
repo root as `gh-triage.conf.sh` and fill it in by hand using
`scripts/refresh-ids.sh`'s output instead.

`scripts/lib.sh` loads this file for every script below, exposing its
values as `open`/`high`/`now`/`blocked`-style keys. If any script call
returns a "not found" GraphQL error, an ID has drifted (e.g. a field was
deleted and recreated) - rerun `refresh-ids.sh` and update the config
file before guessing.

## Fields

```
Status   - Open/Done (or your project's equivalents)
Priority - High/Medium/Low
Target   - Now/Next/Later/Someday
Blocked  - single-value flag: set or unset, not multi-option
Decision - single-value flag: set or unset, not multi-option
Active   - single-value flag: set or unset, not multi-option
```

## Scripts

Use `scripts/*.sh` instead of retyping raw `gh project` commands - same
calls, one invocation instead of a multi-line block generated fresh each
time:

| Script                    | Purpose                                         |
| ------------------------- | ------------------------------------------------ |
| `scripts/init-config.sh`  | `<project-num> <owner>` - bootstraps `gh-triage.conf.sh` at the repo root for a repo that doesn't have one yet (see Setup above). |
| `scripts/create-item.sh`  | `[--number] <title> <body> [priority] [target]` - creates an item as Status: Open and tags priority/target in one call. Field args default to `low`/`later`. `--number` prepends the next sequential ticket number to the title (see below). |
| `scripts/next-number.sh`  | Prints the next sequential ticket number on its own, without creating an item. Used internally by `create-item.sh --number`. |
| `scripts/set-fields.sh`   | `<item-id> [status] [priority] [target] [blocked] [decision] [active]` - updates fields on an existing item; pass `-` to leave a field unchanged. `blocked`/`decision`/`active` take `on`/`off`/`-`. |
| `scripts/find-item.sh`    | `<title-keyword-regex>` - prints matching items as JSON, including `.id` and `.content.id`. |
| `scripts/edit-item.sh`    | `<content-id> [title] [body]` - rewrites an item's title/body; pass `-` to leave a field unchanged. Uses the `.content.id` (`DI_...`), not the item id. |
| `scripts/archive-item.sh` | `<item-id>` - archives a placeholder item.       |
| `scripts/board-summary.sh`| Prints Status counts, then every item flagged Active, Blocked, or Decision - a one-call orientation dump for the start of a session. |
| `scripts/refresh-ids.sh`  | Prints current field/option IDs, for setup or when they've drifted. |
| `scripts/set-readme.sh`   | `<readme-file>` - sets the project README from a file's contents. |

Status/priority/target/blocked/decision/active arguments are the map
keys from your config file (e.g. `done`, `high`, `now`, `on`), not raw
option IDs.

## Add a new item

Before creating anything, run `find-item.sh` with a few likely keywords
to check whether the work is already tracked - duplicates are easy to
miss once a board grows past a couple dozen items.

If your project prepends a unique, sequential numeric ID to every item
title (e.g. `1: ...`, `2: ...`), pass `--number` and give just the rest
of the title - `create-item.sh` looks up the next number itself:

```sh
scripts/create-item.sh --number "..." "body text"
```

If your project doesn't use that convention, drop `--number` and pass
whatever title you want.

`create-item.sh` always sets Status: Open. Priority/target default to
`low`/`later` if omitted; pass them explicitly for items you're starting
in this same session, e.g.:

```sh
scripts/create-item.sh --number "..." "body text" medium now
```

## Update an existing item

Find its item first (title match):

```sh
scripts/find-item.sh "keyword"
```

Then update fields with its `.id` (the `PVTI_...` item id):

```sh
scripts/set-fields.sh <item-id> - - now - - on
```

Set Target to `now` and the Active flag on when you start non-trivial
work on an item, Status to `done` once it ships.

To edit an item's **title or body**, use `scripts/edit-item.sh
<content-id> [title] [body]`, with the **content ID** (`DI_...`, from
`.content.id` in `find-item.sh`'s output), not the item ID (`PVTI_...`).
Passing the item ID exits 0 and prints a usage error to stdout instead of
failing loudly - check the output, don't assume success from the exit
code alone.

## Split a placeholder item into finer items

When a bundled placeholder item (e.g. "16: Word pages, backtraces, and
SEO breakdowns (rest of Phase 3)") starts active work, replace it with
individually-tracked items rather than editing it in place:

1. Create the finer items (see "Add a new item" above), Target set to
   how urgently each should be picked up, Status Open (Done if a piece
   already shipped).
2. Retire the placeholder - archive rather than delete, so the split is
   recoverable if it turns out wrong:
   ```sh
   scripts/archive-item.sh <placeholder-item-id>
   ```
3. If your project's README carries a narrative summary (phase/milestone
   status), flag that it's now stale, draft the replacement text, save it
   to a file, then set it:
   ```sh
   scripts/set-readme.sh <path-to-readme.md>
   ```

## Permission gates

Some permission-gate tools block every non-read-only `gh` subcommand by
default, `gh project item-create`/`item-edit`/`item-archive`/etc.
included, even though these are safe, non-destructive project-board
writes. If your gate gives you a way to allowlist specific paths, scope
it to `scripts/**` in this skill directory rather than loosening `gh`
generally. If it doesn't, hand the blocked command to the user to run
themselves rather than retrying or bypassing the gate.

`gh project field-delete` has no safe default and needs a human's
explicit go-ahead every time - never retry it automatically or ask for a
standing grant.

## Don't

- Don't duplicate the board's backlog/roadmap detail into a separate doc
  in the repo - the project should stay the single source of truth once
  you've adopted this workflow.
- Don't rename field options via `gh` - there's no rename command; it's
  field-delete + field-create + re-tagging every item, and field-delete
  needs a human's go-ahead each time.
