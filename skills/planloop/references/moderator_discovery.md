# Moderator Discovery Template

Use this template when `Agent M` interviews the user before freezing the `PRD`.

## Operating Rule

- `Agent M` should drive a short, user-friendly intake
- the outcome is implicit: produce a plan
- the goal is to extract the user's objective, constraints, approval boundaries, and workspace or output setup
- if a field remains unknown, mark it explicitly instead of guessing
- ask in simple English by default
- ask at most `4` intake questions by default
- ask the default first response as one bundled intake block unless equivalent fields are already present
- each question should include exactly `3` easy options and one free-form fallback

## Discovery Packet Template

```md
# Discovery Packet

## 1. Stated Request
- What the user literally asked for

## 2. Interpreted Goal
- What Agent M believes the user actually wants

## 3. Desired End State
- What should be true when the work is done

## 4. Success Signals
- Observable indicators of success

## 5. Failure Signals
- What would make the user say the result missed the mark

## 6. Approval and Safety Boundaries
- External side effects
- Approval-gated actions
- Irreversible steps

## 7. Workspace Strategy
- Work in place
- Use a branch
- Use a worktree

## 8. Artifact Output Path
- Where the final plan document should be saved

## 9. Iteration Budget
- Default is 5
- Custom value if the user wants one

## 10. Moderator Confidence
- High / Medium / Low
- Why
```

## Default Bundled 4-Question Intake

Use this as the default first assistant response when the user gave only the task or left one or more intake fields unspecified.

```text
I’ll produce a plan. I just need four quick preferences first.

1. Success
  A. Reviewable plan is enough. Example: I can read it and approve it quickly.
  B. Tests, checks, or commands should be included. Example: Add concrete validation steps.
  C. Recommendation plus verification should be included. Example: Recommend one approach and explain how to verify it.
  Or just tell me in your own words.

2. Failure
  A. Overengineering is failure. Example: Too many files, abstractions, or extra work.
  B. Weak verification is failure. Example: No tests, checks, or clear proof.
  C. Scope drift is failure. Example: It changes unrelated systems or adds extras I did not ask for.
  Or just tell me in your own words.

3. Safety and approvals
  A. Planning only, no changes. Example: Analyze and plan, but do not edit anything.
  B. Local changes are okay, but no external side effects. Example: Edit local files, but do not send, deploy, or touch third-party systems.
  C. Normal local workflow is okay, but pause at risky steps. Example: Work locally, but ask before anything irreversible or unclear.
  Or just tell me in your own words.

4. Workspace and output
  A. Work in place. Example: Stay in the current workspace and save the plan where I specify.
  B. Use a branch. Example: Keep this workspace, but use a dedicated git branch.
  C. Use a worktree. Example: Create an isolated worktree for safer larger changes.
  Also tell me where I should save the final plan document. Example: /absolute/path/plan.md
  Or just tell me in your own words.
```
