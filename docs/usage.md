# Planloop Usage

`planloop` is the public-facing skill form of a moderated planning workflow.

What users see:

- one short bundled 4-question intake block in simple English
- a clear stage flow: `Clarify -> Draft Plan -> Stress-Test -> Approve`
- one approved plan document at the requested output path

## Quick Start

1. Use the built-in `$skill-installer`.
2. Install the GitHub repo path `skills/planloop`.
3. Restart Codex.
4. Invoke `$planloop`.

Example installer request:

```text
Use $skill-installer to install the skill from GitHub repo <owner>/<repo> path skills/planloop.
```

Default user prompt:

```text
$planloop install telegram-mcp-server
```

The user does not need to mention `Agent M`, `Agent P`, or `Agent C` manually.
The outcome is implicit: `plan` is mandatory.

## Public Flow

1. Install the skill from GitHub.
2. Invoke `$planloop <task>`.
3. Receive one short bundled intake block that covers:
   - `Success`
   - `Failure`
   - `Safety and approvals`
   - `Workspace and output`
4. Answer in one compact message or in your own words.
5. Review the approved plan when the moderator finishes.

Expected first-response behavior:

- if I only gave the task, ask the bundled intake first
- if I explicitly invoke `$planloop`, do not skip intake just because I also asked for review, refactor, or implementation
- do not jump straight to a plan or recommendation
- ask `Workspace` and final output path in the same intake round
- do not ask `Outcome` unless the user explicitly wants to override the default plan-only contract

## Internal Mapping

Internally the skill still uses:

- `Agent M` (`Moderator`)
- `Agent P` (`Planner`)
- `Agent C` (`Critic`)

But the public user-facing stages are:

- `Clarify`
- `Draft Plan`
- `Stress-Test`
- `Approve`

## Capability Truth

Current public claim:

- honest v1: prompt-driven multi-role planning skill
- the public contract is the skill behavior, not the local runner

Do not describe this as true model-backed orchestration unless that runtime is actually shipped and tested end to end.

## Demo Artifacts

- transcript: [../examples/demo.md](../examples/demo.md)
- sample final plan: [../examples/final-plan.md](../examples/final-plan.md)
- benchmark kit: [benchmark.md](benchmark.md)

## Optional Local CLI

This repo also ships a local CLI for deterministic drafting and benchmarking.

Run the local workflow:

```bash
./scripts/planloop run --task-text "Install telegram-mcp-server."
```

Run the benchmark scorer:

```bash
./scripts/planloop-benchmark score \
  --cases benchmarks/cases/planloop-12.json \
  --results benchmarks/results/example-results.json
```

The CLI is development tooling. The primary public onboarding path is still the Codex skill.
