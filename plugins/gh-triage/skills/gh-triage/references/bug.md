# Bug Item Examples

Two examples at different Effort levels. Repro ranges from an exact
reproduction to "can't reliably repro," and Verification should scale
with how much confidence the fix needs.

## ABC-46: Onboarding "Skip" link does nothing on step 3 (S effort)

```markdown
## Symptom
Clicking "Skip" on step 3 of the onboarding walkthrough should close
it; instead nothing happens and the modal stays open.

## Repro
1. Start onboarding as a new user
2. Advance to step 3
3. Click "Skip"

## Verification
- Skip closes the walkthrough from every step, not just 1, 2, 4,
  and 5
```

## ABC-47: Onboarding progress resets for some users after login (L effort)

```markdown
## Symptom
A small share of returning users land back on step 1 of onboarding
despite having completed it previously; a completed onboarding
should never reappear.

## Repro
Intermittent, can't reliably repro locally. Correlates with users
who log in from a new device shortly after finishing onboarding;
support tickets reference resets within about 10 minutes of
completion.

## Verification
- A user who completes onboarding doesn't see it again after
  logging in from any device
- Root cause is identified and covered by a regression test, not
  just a workaround for the reported symptom
```
