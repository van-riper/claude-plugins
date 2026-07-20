# Spike Item Examples

Two examples at different Effort levels. Investigation should carry
a timebox once a spike is big enough to otherwise run indefinitely.

## ABC-48: Decide onboarding "Skip" link wording (S effort)

```markdown
## Question
Should the skip control read "Skip", "Skip tutorial", or "Skip for
now"? Copy needs to be settled before the story implementing it can
close.

## Investigation
Check the existing copy deck for precedent; if there's none, draft
two candidate options for design to react to.

## Output
One agreed-on wording, added to the copy deck and referenced from
the implementing story's Objective.
```

## ABC-49: Decide per-user vs per-device onboarding state (L effort)

```markdown
## Question
ABC-45 assumes onboarding progress should follow the user across
devices; that needs confirming before the migration starts: is a
fresh onboarding per device intentional, or is it the bug ABC-45
should fix?

## Investigation
Look at support tickets and analytics for how often users onboard on
a second device, and ask support whether repeat onboarding on a new
device draws complaints. Timebox to 2 days; this blocks ABC-45.

## Output
A written recommendation (per-user vs per-device), posted on the
onboarding-rework epic, with ABC-45 updated or split to match.
```
