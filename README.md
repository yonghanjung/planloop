# Planloop

`planloop` is a public Codex skill for protected planning.

It turns a vague request into a reviewable plan by using a short guided intake, a minimal planner, an adversarial critic, and a final moderator approval gate.

## Install the Skill

Use Codex's built-in skill installer:

```text
Use $skill-installer to install the skill from GitHub repo <owner>/<repo> path skills/planloop.
```

Then restart Codex and invoke:

```text
$planloop install telegram-mcp-server
```

Claude Code also supports the same skill package, but not through Codex's GitHub installer flow.
Install it by cloning this repo and using the helper script in this repo.
The helper links the skill into `~/.claude/skills/planloop` for personal use or `<project>/.claude/skills/planloop` for project-local use.

Personal install across projects:

```bash
git clone https://github.com/yonghanjung/planloop.git
cd planloop
./scripts/install-claude-skill --personal
```

Project-local install from inside an existing project:

```bash
git clone https://github.com/yonghanjung/planloop.git
cd planloop
./scripts/install-claude-skill --project /path/to/target-project
```

Then start or restart Claude Code and invoke:

```text
/planloop install telegram-mcp-server
```

## Support Matrix

| Host | Install path | Invoke | Current verification |
| --- | --- | --- | --- |
| Codex | GitHub repo path via `$skill-installer` | `$planloop <task>` | GitHub installer packaging verified on a clean temp destination; `git` install path succeeded; current authenticated `codex exec` runtime first response verified from the public repo source; direct-download path hit a local SSL trust issue on this machine |
| Claude Code | `./scripts/install-claude-skill --personal` or `--project /path/to/target-project` | `/planloop <task>` | Fresh GitHub clone helper install verified; project-local runtime first response verified with `claude -p`; fully clean temp `HOME` install still needs `claude /login` before runtime use |

## What the User Sees

- one short bundled 4-question intake block in simple English
- a clear stage flow: `Clarify -> Draft Plan -> Stress-Test -> Approve`
- one approved plan document at the requested output path

The user does not need to mention `Agent M`, `Agent P`, or `Agent C`.
The outcome is implicit: `plan` is mandatory.

## Local CLI

This repo also ships a small local runner and benchmark CLI.

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

Example output:

```text
Benchmark: Planloop-12 v0.1
System: planloop (example-local-run)
Coverage: 4/12 (33.33%)
Coverage status: demo_only
Composite score: 77.50/100
```

## Repo Layout

- `skills/planloop/`: installable skill package
- `src/planloop/`: local runner and benchmark library
- `scripts/`: local convenience entrypoints
- `docs/usage.md`: public usage guide
- `docs/benchmark.md`: benchmark definition and scoring rules
- `examples/`: demo transcript and sample final plan
- `benchmarks/`: starter cases and example results
- `tests/`: regression tests

## Benchmark Shape

The starter benchmark is not limited to coding tasks.
It also includes a harder conflicting-constraints decision case, designed to test whether `planloop` still asks the right short intake before committing to a plan.

## MVP Scope

Current public claim:

- prompt-driven multi-role planning skill
- local benchmark kit included
- local runner included for development and deterministic drafting

Not yet shipped:

- true model-backed orchestration
- richer benchmark suite beyond the starter `Planloop-12`

## License

MIT. See [LICENSE](LICENSE).
