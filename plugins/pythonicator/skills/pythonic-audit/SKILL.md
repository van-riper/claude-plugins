---
name: pythonic-audit
description: Use to audit an existing or unreviewed Python codebase against the house canon — a whole-repo conformance snapshot plus a full findings list. Run when asked to audit, assess, or review an entire project/directory for style conformance, not a single diff.
---

# Pythonic audit

Audit a whole Python codebase against the canon and produce one report: a
conformance snapshot (metrics) over the top, the full findings below. Two
tiers: a static scan over every file, then a judgment review of each module.

## Procedure

1. **Resolve the target.** Use the path the user gave, else the current
   directory. Locate the plugin: `find ~/.claude/plugins -path '*pythonicator*/src/audit_scan.py'`.
2. **Freshness.** Run `python3 <plugin>/src/sync_canon.py --check`; rebuild
   if stale so the review uses the current canon. (Skip quietly if the vault
   docs are absent on this machine.)
3. **Static tier.** Run `python3 <plugin>/src/audit_scan.py <target>` and
   capture the JSON. This is whole-repo, machine-decidable coverage.
4. **Deep tier.** Group the discovered `.py` files by directory. Dispatch one
   `pythonic-reviewer` per directory, in **audit mode**: tell each reviewer
   "Audit mode: run ty for information and note its status, but do NOT stop if
   it is not green — proceed with the judgment review. The ruff restriction is
   unchanged. Do not run audit_scan.py; this skill already ran the static tier
   and merges it." Ask each to return
   findings as a list of `file · line · section · rule · severity · why · fix`.
5. **Merge and report.** Combine the two tiers, then dedupe by underlying
   issue, not by exact key. The tiers use different rule names for the same
   violation (static `mutable-default` vs judgment `mutable-default-argument`;
   static `cryptic-identifier` vs judgment `parameter-abbreviated`; static
   `missing-public-docstring` vs judgment `missing-docstring`), and the static
   tier pins `legacy-typing`, `broad-except`, and `missing-module-docstring` to
   line 1 while the judgment tier gives the true line. So: when both tiers
   report the same issue for the same file (matching on issue category, not on
   line for those pinned rules), keep the judgment finding — it carries the
   precise line and a fix — and drop the static one. Keep a static finding only
   where no judgment finding covers it (the static tier is the gap-filler and
   the source of the snapshot metrics). Then write the report and print a short
   inline summary.

## Report format

Write to `<target>/pythonic-audit-report.md` (fallback: cwd):

1. **Header** — target path, file count, date, ty status.
2. **Conformance snapshot** — files-clean %, counts by severity, a
   violations-by-rule table, and the worst-offender files. The clean % is the
   static (machine-decidable) tier; a file can be static-clean yet still draw a
   judgment finding, so label it as such.
3. **Findings** — merged, grouped by severity (blockers first); each with
   `file:line`, section + rule, a one-line why, and a proposed fix.
4. **By-module rollup** — per-directory finding counts.

## Notes

- The static tier covers what a linter would catch; the reviewers cover the
  judgment rules. The snapshot stands even if ruff and ty never ran on the
  target.
- `ty` is advisory; a non-green target never stops the audit.
- If a reviewer dispatch fails, note which modules went unreviewed.
- This audits whole codebases. For a single diff, use `pythonic-reviewer`
  directly.
