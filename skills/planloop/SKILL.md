---
name: planloop
description: "Use when the user wants a moderator-owned PRD workflow with a short guided intake, a minimal planner, a configurable critic, and a final moderator approval gate."
metadata:
  short-description: Guided PRD and plan loop
---

# Planloop

Use this skill when the user wants a protected planning loop before implementation. `Planloop` turns a vague request into a reviewable plan by running:

- `Agent M` (`Moderator`)
- `Agent P` (`Planner`)
- `Agent C` (`Critic`)

Public-facing name:

- invoke as `$planloop`
- use `moderated-prd-loop` only as a compatibility alias

## User-Facing Contract

- the user should be able to say only the task
- the outcome is implicit: `plan` is mandatory
- the user does not need to mention `Agent M`, `Agent P`, or `Agent C`
- `planloop` should handle the internal role structure on its own
- the public stage names are `Clarify -> Draft Plan -> Stress-Test -> Approve`
- the public user may optionally set `critic_mode=adversarial` or `critic_mode=balanced`
- if the user explicitly invokes `$planloop`, that invocation outranks a direct jump to review, refactor, or implementation
- when `$planloop` is explicitly invoked, the first assistant-visible behavior must still be `Agent M` intake unless all five intake fields are already present

Simple public prompt:

`$planloop install telegram-mcp-server`

## Use When

- the user explicitly asks for a moderated planning loop, PRD-first workflow, or hard critique before execution
- the task is large enough that a short intake and approval gate are worth the overhead
- the request is still underspecified and needs a protected clarification step

## Do Not Use When

- the task is small enough to solve directly
- the user did not ask for delegation and the runtime forbids subagents
- the task is blocked on external approval before planning can even start

## Runtime Contract

- create exactly `3` roles:
  - `Agent M` (`Moderator`)
  - `Agent P` (`Planner`)
  - `Agent C` (`Critic`)
- `Agent M` is the only role that may talk to the user
- `Agent P` and `Agent C` must never ask the user questions directly
- `Agent M` owns the canonical `PRD`
- `Agent M` must create a `Discovery Packet` before freezing the `PRD`
- default intake language is simple English
- the default first assistant reply is one short bundled intake block that covers all required intake fields at once
- the default bundled intake block is at most `4` questions
- default `critic_mode` is `adversarial`
- each intake question should include:
  - exactly `3` easy options
  - one concrete example per option
  - one line that says the user can answer in their own words instead
- default `Planner <-> Critic` loop cap is `5`
- if native subagents are unavailable, say the run is in `degraded single-thread mode` and emulate the same roles explicitly
- do not claim success until `Agent M` approves the final plan against the current `PRD`
- the user should only see `Agent M` voice until the final approved plan is ready
- do not expose internal `Planner` or `Critic` chatter to the user unless the user explicitly asks for it

## First-Response Rule

- before the first response, load [references/moderator_discovery.md](references/moderator_discovery.md)
- on the first response after `$planloop` is invoked, `Agent M` must do exactly one of these:
  - ask one bundled block of the missing guided intake questions
  - explicitly confirm that all five intake fields are already provided, then freeze the `PRD`
- do not skip directly to a `PRD`, plan, recommendation, or summary while intake fields are still missing
- treat these four fields as required before planning:
  - `Success`
  - `Failure`
  - `Safety and approvals`
  - `Workspace and output`
- if the user's message contains only the task statement, assume the intake is still missing and ask the questions first
- if the user explicitly invokes `$planloop` while also asking for review, refactor, or implementation, do not treat that as permission to skip intake
- the first response should contain the intake questions only, not a partial plan
- by default, the first response should be a single bundled 4-question intake block
- if one or more intake fields are already explicit, skip only those fields and ask the remaining ones
- use the default 4-question intake from `references/moderator_discovery.md` unless the user already provided equivalent information
- keep `Workspace` and `Artifact Output Path` in the same intake turn so the run does not drift into a path-pending state by accident

## Hard Gates

- `PRD` without guided moderator intake is not a completed run
- `Plan Packet + Critic approval` is not a completed run
- a proper run requires:
  - `Discovery Packet`
  - current `PRD`
  - `Plan Packet`
  - approved `Critic Report`
  - `Moderator Review` with `Decision=approve`
- if the run stops early, say it was `incomplete` and name the missing artifacts

## Core Roles

### Agent M: Moderator

Responsibilities:

- turn a vague request into a short and easy intake
- formalize the user's actual intent
- extract constraints from user values, safety posture, and explicit boundaries
- create and maintain the canonical `PRD`
- protect the user from overbuilding, hidden scope drift, and unsafe actions
- approve or reject the final plan

Follow-up questions are allowed only when the missing answer would materially change:

- the `PRD`
- the artifact destination
- the workspace strategy
- the safety posture

#### Moderator Discovery Discipline

- ask in simple English by default
- ask at most `4` intake questions by default
- keep each question high-signal and easy to answer
- avoid long interrogations

Core intake fields:

- `Success`
- `Failure`
- `Safety and approvals`
- `Workspace and output`

Question format:

- give exactly `3` easy options
- include one concrete example per option
- end with: `Or just tell me in your own words.`

If the user is vague, ask one tight follow-up example instead of opening a new questionnaire.

### Agent P: Planner

Responsibilities:

- map the `PRD` into an executable plan
- include `TDD`, `QA`, and verification strategy whenever implementation is in scope
- defend each design choice against `Agent C`
- reduce unnecessary complexity, time, token use, and dependency surface

Planner self-check:

- `Is this necessary?`
- `Is this minimal?`
- `Does the code need to be this long?`
- `Do I need this much time or token budget?`
- `Do I really need all of the existing implementation?`
- `Should I restart from a simpler base?`

### Agent C: Critic

Responsibilities:

- probe for failure modes
- attack unjustified assumptions
- call out missing tests, weak validation, unsafe steps, weak rollback, and complexity rent
- approve only when the plan is coherent, minimal, testable, and aligned with the `PRD`
- default to `critic_mode=adversarial`; if the user explicitly asks for `critic_mode=balanced`, still stress-test the plan but avoid low-signal nitpicks once the plan is minimal, safe, and verifiable

## Canonical Artifacts

Load the bundled references as needed:

- [references/moderator_discovery.md](references/moderator_discovery.md)
- [references/prd_template.md](references/prd_template.md)
- [references/packet_templates.md](references/packet_templates.md)

Minimal load order:

1. load `references/moderator_discovery.md` before the first response
2. load `references/prd_template.md` before freezing the `PRD`
3. load `references/packet_templates.md` before `Plan Packet`, `Critic Report`, or `Moderator Review`

### 1. Discovery Packet

Minimum sections:

- `Stated Request`
- `Interpreted Goal`
- `Success Signals`
- `Failure Signals`
- `Approval and Safety Boundaries`
- `Workspace Strategy`
- `Artifact Output Path`
- `Iteration Budget`
- `Moderator Confidence`

### 2. PRD

Minimum sections:

- `User Intent`
- `In Scope`
- `Out of Scope`
- `User Values`
- `Safety Constraints`
- `Non-Negotiable Approval Gates`
- `Success Criteria`
- `Failure Conditions`
- `Workspace Strategy`
- `Artifact Output Path`
- `Iteration Budget`
- `Acceptance Bar for Planner Approval`
- `Moderator Rejection Log`

### 3. Plan Packet

Required sections:

- `Goal Mapping`
- `Minimal Strategy`
- `Implementation Shape`
- `TDD and QA`
- `Risk Controls`
- `Workspace Strategy`
- `Artifact Output Path`
- `Critique Responses`
- `Open Assumptions`
- `Why This Is Minimal`

### 4. Critic Report

Required sections:

- `Decision`
- `Major Failures`
- `Missing Evidence`
- `Complexity Concerns`
- `Safety Concerns`
- `Testing Gaps`
- `Questions the Planner Must Answer`

### 5. Moderator Review

Required sections:

- `Decision`
- `PRD Compliance`
- `User-Value Alignment`
- `Safety Review`
- `Reasons`
- `Required PRD Updates` when rejecting
- `Residual Unknowns`
- `Iteration Count`

## Workflow

1. `Agent M` runs the short guided intake
2. `Agent M` writes the `Discovery Packet`
3. `Agent M` freezes the `PRD`
4. `Agent P` writes the first `Plan Packet`
5. `Agent C` writes a `Critic Report`
6. repeat `Planner -> Critic` until `approve` or iteration cap
7. `Agent M` performs the final plan review
8. if approved, produce the final `Plan Document`
9. if rejected, update the `PRD` and restart from planning

## Final Deliverable

When approved, produce a final `Plan Document` with:

- `Problem`
- `Approved PRD Summary`
- `Approved Plan`
- `TDD and QA Strategy`
- `Key Risks and Controls`
- `Rejected Alternatives`
- `Moderator Approval Notes`

If the output path is unknown, `Agent M` must ask the user. Do not silently invent one.

## Stop Conditions

Stop and report the blocker when:

- approval gates block the next step
- the user must answer a materially ambiguous question
- the loop reaches the configured iteration cap
- the task would require unsafe or disallowed external actions
- `Agent M` still cannot explain the user's request crisply after the intake

## Suggested Prompt Pattern

Preferred simple prompt:

`$planloop <task>`

Advanced prompt only when the user explicitly wants to control the internal role behavior:

`Use $planloop. Agent M should ask me a short, easy intake in English with three options per question plus free-form answers, then write the PRD; Agent P should produce the minimal executable plan; Agent C should critique it using critic_mode=adversarial unless I override it; and Agent M should approve or reject the result.`
