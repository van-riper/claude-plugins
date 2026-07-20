# Story Item Examples

Two examples at different Effort levels, showing how much the
Approach section should carry as scope grows. Trivial stories can
skip it entirely.

## ABC-42: Add "skip tutorial" link to onboarding (S effort)

```markdown
## Objective
New users can dismiss the onboarding walkthrough after the first
step instead of clicking through all five.

## Acceptance Criteria
- A "Skip" link appears on steps 2-5 of the walkthrough
- Clicking Skip closes the walkthrough and marks onboarding complete
```

## ABC-43: Rework onboarding into a guided checklist (L effort)

```markdown
## Objective
Replace the five-step walkthrough modal with a persistent checklist
users can complete at their own pace, so onboarding no longer blocks
the rest of the app while it's in progress.

## Approach
Move onboarding state out of session storage and into the same
per-user settings table used for feature flags, so the checklist
survives across devices and reloads. New users get a small "Setup"
panel in the sidebar instead of a blocking modal.

## Acceptance Criteria
- Sidebar panel lists all five onboarding steps, each with a
  completion checkbox
- A step is marked done by completing it server-side, not just by
  closing a modal
- Users can reach the app's core actions before finishing onboarding
- Users mid-walkthrough at launch are migrated to the checklist
  without losing progress
```
