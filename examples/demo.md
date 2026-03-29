# Planloop Demo Transcript

This transcript shows the intended public flow for a first-time user.

## Install

User:

```text
Use $skill-installer to install the skill from GitHub repo <owner>/<repo> path skills/planloop.
```

Assistant:

```text
Installed `planloop`.
Restart Codex to load the new skill.
```

## Invoke

User:

```text
$planloop install telegram-mcp-server
```

The user does not need to mention internal `Agent M`, `Agent P`, or `Agent C`.

Assistant:

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

User:

```text
Success: C
Failure: B and C
Safety and approvals: A
Workspace and output: Work in place. Save the final plan to /absolute/path/telegram-plan.md
```

Assistant:

```text
Thanks. I have enough to freeze the discovery packet and PRD. I’ll stay in Agent M voice until the approved plan is ready.
```

## Expected End State

Later:

```text
Moderator approved. The final plan document is ready at /absolute/path/telegram-plan.md.
```
