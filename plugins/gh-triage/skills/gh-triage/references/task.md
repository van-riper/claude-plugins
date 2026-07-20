# Task Item Examples

Two examples at different Effort levels. The shape (Objective plus
Acceptance Criteria) stays the same; only how much each section
carries changes.

## ABC-44: Update onboarding walkthrough screenshots (S effort)

```markdown
## Objective
The onboarding screenshots still show the old nav bar; replace them
with current ones so new users aren't confused by mismatched UI.

## Acceptance Criteria
- All five walkthrough screenshots reflect the current nav bar
```

## ABC-45: Migrate onboarding state off session storage (L effort)

```markdown
## Objective
Onboarding progress lives in sessionStorage today and resets on
every new device or private window; move it server-side so it
persists per-user like the rest of app state.

## Acceptance Criteria
- Onboarding progress is read from and written to the user settings
  table, not sessionStorage
- Existing sessionStorage progress is migrated on next login, not
  silently discarded
- Onboarding UI itself is unchanged; this is a storage swap only
```
