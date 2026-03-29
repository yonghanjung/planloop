# PRD Template

Use this template after `Agent M` completes discovery.

```md
# PRD

## 1. User Intent
- Crisp statement of the actual user goal

## 2. Problem Statement
- Current blockage
- Why the current state is insufficient

## 3. In Scope
- Work explicitly included

## 4. Out of Scope
- Work explicitly excluded

## 5. User Values
- What the user is optimizing for
- What tradeoffs the user prefers

## 6. Safety Constraints
- Data sensitivity
- Approval gates
- Irreversible actions
- Technical boundaries

## 7. Non-Negotiable Constraints
- Must-haves
- Must-not-haves

## 8. Success Criteria
- Measurable or observable completion checks

## 9. Failure Conditions
- Conditions that invalidate an otherwise plausible plan

## 10. Workspace Strategy
- In place / branch / worktree
- Why this mode was chosen

## 11. Artifact Output Path
- Where the final plan document should be saved

## 12. Iteration Budget
- Default 5
- Custom value if explicitly requested

## 13. Acceptance Bar for Planner Approval
- What Agent C must see before approving
- What Agent M must see before approving

## 14. Residual Unknowns
- Known gaps allowed to remain open

## 15. Moderator Rejection Log
- Date / iteration
- Reason for rejection
- PRD changes introduced by the rejection
```

## Rule

- the `PRD` should be stricter than the conversation summary
- if the user's real goal is still unclear, do not freeze the `PRD` yet
- if the artifact output path is unknown, say `Path pending user answer` rather than inventing one
