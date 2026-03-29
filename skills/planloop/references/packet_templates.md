# Packet Templates

Use these templates to keep the planner loop disciplined.

## Plan Packet

```md
# Plan Packet

## 1. Goal Mapping
- PRD requirement -> planned step

## 2. Minimal Strategy
- Smallest credible path
- Why larger options were rejected

## 3. Implementation Shape
- Files
- Modules
- Systems touched

## 4. TDD and QA
- Tests to add or run
- Verification sequence
- Demo evidence expected at the end

## 5. Risk Controls
- Rollback
- Containment
- Safety checks

## 6. Workspace Strategy
- In place / branch / worktree

## 7. Artifact Output Path
- Final document destination

## 8. Critique Responses
- Critic issue -> planner response

## 9. Open Assumptions
- What is still assumed

## 10. Why This Is Minimal
- Explicit defense against overbuilding
```

## Critic Report

```md
# Critic Report

## Decision
- approve / revise

## Iteration Count
- Current loop number

## Major Failures
- Structural problems

## Missing Evidence
- Claims without proof

## Complexity Concerns
- Unnecessary code, abstractions, or dependencies

## Safety Concerns
- Approval, data, or execution risks

## Testing Gaps
- Missing verification

## Questions the Planner Must Answer
- Direct, adversarial prompts
```

## Moderator Review

```md
# Moderator Review

## Decision
- approve / reject

## Iteration Count
- Current loop number

## PRD Compliance
- Which requirements were satisfied or missed

## User-Value Alignment
- Does the plan match the user's actual preferences

## Safety Review
- Are safety boundaries still respected

## Reasons
- Why this decision was made

## Required PRD Updates
- Only when rejecting

## Residual Unknowns
- Any remaining uncertainty accepted by the moderator
```
