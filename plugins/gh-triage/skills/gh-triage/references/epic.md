# Epic Item Examples

Two examples at different Effort levels, showing how Scope and
Acceptance Criteria should grow with the initiative's size, not just
get longer.

## ABC-50: Onboarding copy refresh (S effort)

```markdown
Slug: onboarding-copy-refresh

## Objective
Refresh onboarding wording sitewide for tone consistency; no new
onboarding functionality.

## Scope
- In: rewriting the walkthrough's existing step copy
- Out: sequencing, layout, or state changes. Those roll up under
  `onboarding-rework` instead

## Acceptance Criteria
- Every onboarding string is audited and confirmed on-brand, or
  replaced
```

## ABC-1: Onboarding rework (L effort)

```markdown
Slug: onboarding-rework

## Objective
Replace the blocking five-step onboarding modal with a persistent,
resumable flow that doesn't gate access to the rest of the app.

## Scope
- In: onboarding state, the walkthrough UI, and its copy
- Out: the signup flow itself and post-onboarding lifecycle emails.
  Those are tracked separately

## Acceptance Criteria
- New users can reach and use the app's core actions before
  finishing onboarding
- Onboarding progress persists across devices and sessions
- Every child item under this epic is Done or explicitly descoped
```
