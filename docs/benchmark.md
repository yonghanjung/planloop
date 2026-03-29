# Planloop Benchmark

`planloop` utility should be judged with evidence, not vibe.
This benchmark is a local-first evaluation kit for `plan quality`, `user friction`, `scope control`, and `downstream usefulness`.

## Goal

Compare:

- raw assistant
- generic planning mode
- `planloop`

Core questions:

1. Is the first response intake-first?
2. Is the intake short and bundled?
3. Is user friction low before the approved plan?
4. Is the plan execution-ready?
5. Does the system reduce overengineering, scope drift, and weak verification?

## Starter Benchmark

The starter kit is `Planloop-12`.

- `4` ambiguous coding/refactor tasks
- `4` integration/setup tasks
- `4` operational workflow tasks

This starter set is meant to expand into `Planloop-30` later.

## Files

- cases fixture: [../benchmarks/cases/planloop-12.json](../benchmarks/cases/planloop-12.json)
- results fixture: [../benchmarks/results/example-results.json](../benchmarks/results/example-results.json)
- scorer library: [../src/planloop/benchmark.py](../src/planloop/benchmark.py)
- scorer wrapper: [../scripts/planloop-benchmark](../scripts/planloop-benchmark)

## Result Schema

Each task result records at least:

- `task_id`
- `first_response_mode`
  - `intake_only`
  - `mixed`
  - `plan_first`
- `bundled_intake`
- `asked_outcome`
- `used_why_this_matters`
- `user_turns_to_approved_plan`
- `approved_without_rewrite`
- `downstream_execution_ready`
- `total_tokens` (optional but recommended)
- `failure_tags`
  - `scope_drift`
  - `overengineering`
  - `weak_verification`
  - `unsafe_assumption`
  - `not_intake_first`
  - `other`

## Main Metrics

1. `intake_first_rate`
2. `bundled_intake_rate`
3. `no_outcome_question_rate`
4. `no_why_this_matters_rate`
5. `approval_without_rewrite_rate`
6. `downstream_execution_ready_rate`
7. `median_user_turns_to_approved_plan`
8. failure rates:
   - `scope_drift_rate`
   - `overengineering_rate`
   - `weak_verification_rate`
   - `unsafe_assumption_rate`

## Composite Score

The scorer reports a simple weighted score on `[0, 100]`.

Weights:

- `intake_first_rate`: `0.20`
- `bundled_intake_rate`: `0.10`
- `no_outcome_question_rate`: `0.05`
- `no_why_this_matters_rate`: `0.05`
- `approval_without_rewrite_rate`: `0.20`
- `downstream_execution_ready_rate`: `0.20`
- `scope_control_score`: `0.10`
- `verification_score`: `0.10`

Where:

- `scope_control_score = 1 - max(scope_drift_rate, overengineering_rate)`
- `verification_score = 1 - weak_verification_rate`

The score is a decision tool, not a leaderboard.

## Coverage Interpretation

Coverage matters before the score matters.

- `< 50%`: `demo_only`
- `50% to < 80%`: `provisional`
- `80% to < 100%`: `comparable`
- `100%`: `official`

Do not present a low-coverage score as a release-facing result.

## Recommended Run Protocol

For each system under comparison:

1. run the same task text
2. save the first assistant reply
3. save the final approved plan
4. have a human grader fill the result record
5. score the result file with the CLI

Keep:

- the same tasks
- the same grader rubric
- the same approval bar

## CLI

Validate fixtures:

```bash
./scripts/planloop-benchmark validate-cases \
  --cases benchmarks/cases/planloop-12.json

./scripts/planloop-benchmark validate-results \
  --cases benchmarks/cases/planloop-12.json \
  --results benchmarks/results/example-results.json
```

Score a run:

```bash
./scripts/planloop-benchmark score \
  --cases benchmarks/cases/planloop-12.json \
  --results benchmarks/results/example-results.json
```

## What This Can Prove

- whether `planloop` reduces user friction
- whether `planloop` improves plan usefulness
- whether `planloop` better controls scope and verification quality

## What This Cannot Prove

- actual implementation success without a separate executor benchmark
- universal performance across all domains
- model-agnostic superiority independent of host runtime
