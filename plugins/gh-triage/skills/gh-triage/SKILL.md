---
name: gh-triage
description: Use when adding, updating, or triaging backlog/roadmap items on a GitHub Project (v2) board via `gh project`. Covers the gh project commands, field/option IDs, and a Status/Type/Effort workflow.
---

## Setup (once per repo)

This skill needs a `gh-triage.conf.sh` file at your repo root
holding your project's number, owner, and field/option IDs - GitHub's
project GraphQL API takes opaque IDs, not field/option names, so every
script below needs them resolved up front.

1. Get your project's number and owner from its URL
   (`github.com/<owner>/projects/<num>` or
   `github.com/orgs/<owner>/projects/<num>`).
2. Pick a short project key (your ticket prefix, e.g. `ETYM`), then run
   `scripts/init-config.sh <project-num> <owner> <project-key>` from your
   repo root. It resolves the project ID and every field/option ID via
   `gh` and writes `gh-triage.conf.sh`, matching field/option
   names to the Status/Type/Effort model case-insensitively.
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
values as `backlog`/`story`/`m`-style keys. If any script call
returns a "not found" GraphQL error, an ID has drifted (e.g. a field was
deleted and recreated) - rerun `refresh-ids.sh` and update the config
file before guessing.

## Fields

```
Status - Backlog/Ready/Blocked/In Progress/Done
Type   - Story/Bug/Task/Spike/Epic
Effort - XS/S/M/L/XL/XXL
```

Status is the single source of truth for where an item stands - Blocked
is its own stage (items get blocked before starting more often than
mid-flow), not a flag layered on top. Type doubles as the "needs a design
decision before it can start" signal: file that kind of item as a Spike
instead of flagging an existing item. Epic is a regular item like any
other Type - see "Epics" below, not a separate format.

Every item's title carries a project-wide ID prefix:
`<PROJECT_KEY>-<N>: <title>` (e.g. `ETYM-7: Add dark mode`), one flat
counter shared by every Type - Epics aren't numbered separately.

### Epics

An Epic is a `Type: Epic` item, not a separate README-based format -
this reuses `find-item.sh`/`set-fields.sh`/the ID counter instead of a
bespoke parser. Epics share the same flat ID counter as every other
item - there's no separate epic numbering, since baking a parent epic
into a child's ID would go stale the moment that child gets reassigned
to a different epic (the same reason Jira, which uses one flat counter
per project regardless of hierarchy, doesn't support nested IDs either).

Every Epic item carries its own canonical **slug** as the first line of
its body: `Slug: <slug>` (e.g. `Slug: onboarding-rework`), followed by
whatever other description the Epic has. Write this by hand when
creating an Epic - there's no auto-generation from the title, since
Epics are created rarely enough that it isn't worth automating, and a
human or agent picking the slug can make it shorter or clearer than a
mechanical slugify of the full title would.

A child item's `Epic` field (a Text field) holds a snapshot of its parent
Epic's slug (e.g. `onboarding-rework`), not the Epic's item ID - a slug
reads directly on the board, unlike an ID, since GitHub Projects has no
way to resolve an ID into something readable there. Set it with
`set-epic.sh <item-id> <epic-slug>`, or tag it at creation time with
`create-item.sh --epic <epic-slug> ...`. Nothing keeps this snapshot in
sync with the Epic's `Slug:` line if the Epic's slug is ever changed by
hand, and nothing validates that `<epic-slug>` corresponds to an existing
Epic at write time.

## Scripts

Use `scripts/*.sh` instead of retyping raw `gh project` commands - same
calls, one invocation instead of a multi-line block generated fresh each
time:

| Script                    | Purpose                                         |
| ------------------------- | ------------------------------------------------ |
| `scripts/init-config.sh`  | `<project-num> <owner> <project-key>` - bootstraps `gh-triage.conf.sh` at the repo root for a repo that doesn't have one yet (see Setup above). |
| `scripts/create-item.sh`  | `[--number] [--epic <epic-slug>] <title> <body> <type> <effort>` - creates an item as Status: Backlog and tags type/effort in one call - both required, no default. `--number` prepends the next sequential `<PROJECT_KEY>-N` to the title (see below); `--epic` tags the new item's Epic reference field with the parent Epic's slug. |
| `scripts/next-number.sh`  | Prints the next sequential ticket number on its own, without creating an item. Used internally by `create-item.sh --number`. |
| `scripts/set-fields.sh`   | `<item-id> [status] [type] [effort]` - updates fields on an existing item; pass `-` to leave a field unchanged. |
| `scripts/set-epic.sh`     | `<item-id> <epic-slug>` - sets an existing item's Epic reference field to the parent epic's slug. |
| `scripts/find-item.sh`    | `<title-keyword-regex>` - prints matching items as JSON, including `.id` and `.content.id`. |
| `scripts/edit-item.sh`    | `<content-id> [title] [body]` - rewrites an item's title/body; pass `-` to leave a field unchanged. Uses the `.content.id` (`DI_...`), not the item id. |
| `scripts/archive-item.sh` | `<item-id>` - archives a placeholder item.       |
| `scripts/board-summary.sh`| Prints Status counts - a one-call orientation dump for the start of a session. |
| `scripts/refresh-ids.sh`  | Prints current field/option IDs, for setup or when they've drifted. |
| `scripts/set-readme.sh`   | `<readme-file>` - sets the project README from a file's contents. |

Status/type/effort arguments are the map keys from your config file
(e.g. `done`, `spike`, `m`), not raw option IDs.

## Add a new item

Before creating anything, run `find-item.sh` with a few likely keywords
to check whether the work is already tracked - duplicates are easy to
miss once a board grows past a couple dozen items.

If your project prepends a unique, sequential ID to every item title
(e.g. `ETYM-1: ...`, `ETYM-2: ...`), pass `--number` and give just the
rest of the title - `create-item.sh` looks up the next number itself and
prepends your configured `PROJECT_KEY`. If your project doesn't use that
convention, drop `--number` and pass whatever title you want.

`create-item.sh` always sets Status: Backlog. Type and Effort are
required every time - there's no default, since guessing either wrong is
worse than asking:

```sh
scripts/create-item.sh --number "..." "body text" task m
```

If the new item belongs to an Epic, add `--epic <epic-slug>` with the
parent Epic's slug (from the `Slug:` line in the Epic's body, e.g.
`onboarding-rework`) to tag it at creation time, instead of a separate
`set-epic.sh` call afterward:

```sh
scripts/create-item.sh --number --epic onboarding-rework "..." "body text" task m
```

Creating an Epic itself is the same call with `type` set to `epic` - give
it a slug as the first line of its body:

```sh
scripts/create-item.sh --number "Onboarding rework" "Slug: onboarding-rework" epic l
```

## Update an existing item

Find its item first (title match):

```sh
scripts/find-item.sh "keyword"
```

Then update fields with its `.id` (the `PVTI_...` item id):

```sh
scripts/set-fields.sh <item-id> in_progress - -
```

Set Status to `in_progress` when you start non-trivial work on an item,
`done` once it ships.

To link an existing item to an Epic (or change its Epic), use
`scripts/set-epic.sh <item-id> <epic-slug>` with the parent Epic's slug
(from the `Slug:` line in its body).

To edit an item's **title or body**, use `scripts/edit-item.sh
<content-id> [title] [body]`, with the **content ID** (`DI_...`, from
`.content.id` in `find-item.sh`'s output), not the item ID (`PVTI_...`).
Passing the item ID exits 0 and prints a usage error to stdout instead of
failing loudly - check the output, don't assume success from the exit
code alone.

## Split a placeholder item into finer items

When a bundled placeholder item (e.g. "ETYM-16: Word pages, backtraces, and
SEO breakdowns (rest of Phase 3)") starts active work, replace it with
individually-tracked items rather than editing it in place:

1. Create the finer items (see "Add a new item" above), Status set to
   Backlog or Ready depending on how urgently each should be picked up
   (Done if a piece already shipped).
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
