---
name: pythonic-canon
description: "Use when writing or editing Python: new functions, classes, dataclasses, types, modules, or packages; refactoring or renaming; or changing type hints, signatures, or dependencies. Enforces the house conventions for naming, typing, structure, docstrings, and packaging. Not for Python tasks that change no code (env/install, requirements syntax, docs, format-only passes, porting to another language)."
---

# Pythonic canon

The house Python styleguide, derived from the vault source of truth and enforced
on agentic Python work. This file is always loaded; the full canon lives in
`references/`, one file per section, with the shared Audit Protocol in
`references/audit-protocol.md`.

## Precedence and severity

Precedence: project `CLAUDE.md` > this canon > Google Python Style Guide > PEP 8.

Severity rides on the RFC 2119 keyword each rule leads with — there is no longer
a house-rule marker to scan for:

| Keyword | Severity |
| ------- | -------- |
| must / must not | blocker |
| should / should not | warning |
| may | optional |

A bare imperative maps by verb: "never" and "do not" carry **must not**; "avoid"
reads as **should not**; "prefer", "use", and "keep" read as **should**.

## Two-layer enforcement

- **Mechanical (automatic).** A PostToolUse hook runs `ruff format`, `ruff check
  --fix`, and `ty check` on every `.py` you edit; residual findings return as
  feedback. Let ruff and ty be the authority; never re-litigate what they own.
- **Judgment (yours).** The rules ruff and ty cannot see. Each section's `Audit`
  callout is the authoritative checklist. Walk the relevant ones before calling
  Python work done; for a substantial change, dispatch `pythonic-reviewer`.

## Freshness

The canon is generated from the vault docs. If they may have changed, verify
before trusting it: run `python3 hooks/sync_canon.py --check` from the plugin
root (locate it with `find ~/.claude/plugins -name sync_canon.py`). If it
reports STALE, rebuild with `python3 hooks/sync_canon.py`.

## Quick reference

| Area | Rule |
| ---- | ---- |
| Lines | Wrap at 80, hard max 100. 4 spaces, never tabs. |
| Imports | Absolute only; no relative, no `import *`. Type-only imports under `if TYPE_CHECKING:` plus `from __future__ import annotations`. |
| Typing | `list[str]`, `dict[str, int]`, `X \| None`; never `Optional`/`Union`/`typing.List`. `collections.abc` for params. Annotate every public signature, not `self`/`cls`. |
| Aliases | Name meaningful primitives with `type`: `type UserId = int`. |
| Naming | S-I-D; `CapWords` / `lower_with_under` / `CAPS_WITH_UNDER`. No abbreviations; units on quantities; modifiers trail the object. |
| Functions | Guard clauses first; under ~60 lines; nest 3 target / 4 max; complexity at or below 10; one responsibility. |
| Args | No mutable default; use `None` and assign inside. Boolean flags keyword-only. |
| Control flow | Direct truthiness; `is None`. EAFP over LBYL. A `while` needs a secondary bound. No `else` after `return`. |
| Exceptions | Catch specific types; no bare or broad `except`. Minimal `try`; `with`/`finally` for cleanup. No `assert` for runtime checks. Bind a long message to a variable. |
| Docstrings | Google style, plain (no sphinx). Required on every public module, class, function. `Attributes:` for public fields. No blank after a function docstring; one after a class. |
| Strings/logs | f-strings; never build with `+` in a loop. Logging takes `%`-args, not a prebuilt f-string. |
| Security | No `eval`/`exec` or `shell=True` on untrusted input. Secrets from the environment. Timezone-aware datetimes. |
| Packaging | uv-managed; one `pyproject.toml`; `~=` constraints, commit `uv.lock`. `src/` layout, `__init__.py` in every package, `tests/` at top level. |

## Judgment checklist (no linter catches these)

A fast digest; each `references/<section>.md` carries the section's authoritative
`Audit` callout. Before declaring Python work complete, confirm:

- [ ] Every blank line inside a function marks a nameable pivot.
- [ ] Names holding a quantity end with their unit, e.g. `timeout_seconds`.
- [ ] No abbreviations beyond `i`/`j`/`k`, a comprehension throwaway, `e`, `f`.
- [ ] Meaningful or repeated primitive types are aliased with `type`.
- [ ] Every public attribute and dataclass field sits in an `Attributes:` section.
- [ ] Each module docstring states purpose, not an inventory of its contents.
- [ ] No comment names a source identifier; comments explain why, not what.
- [ ] Each function does one thing at one level of abstraction.
- [ ] Docstrings describe the contract and do not restate annotated types.
- [ ] Added dependencies are few, justified, and version-constrained.

## Auditing a change

The shared Audit Protocol lives once in `references/audit-protocol.md`; each
`references/<section>.md` carries only that section's rules and `Audit`
checklist. To review a diff, read the protocol once, then the files for the
sections it touches. For a large change, dispatch one `pythonic-reviewer` per
touched section in parallel — each reads the protocol once plus its section
file, keeping every subagent's context tight and focused.

## Full canon

Read `references/index.md` to find the right section. Precedence, conventions,
and the Zen live in `references/principles.md`; the protocol alone is in
`references/audit-protocol.md`.
