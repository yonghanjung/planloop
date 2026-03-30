# Changelog

## v0.1.0 - 2026-03-30

First public MVP release of `planloop`.

### Added

- installable Codex skill package at `skills/planloop`
- Claude Code helper installer at `scripts/install-claude-skill`
- local deterministic runner and benchmark CLI
- starter benchmark suite `Planloop-12`
- public usage docs, demo transcript, and sample final plan

### Changed

- standardized the public skill name to `planloop`
- reduced the moderator intake to one bundled 4-question block
- made `plan` the implicit mandatory outcome
- aligned README and docs around `Clarify -> Draft Plan -> Stress-Test -> Approve`

### Fixed

- prevented invalid moderator approvals from persisting a review artifact
- unified `Discovery -> PRD` synthesis so guided intake and `auto_finish` produce the same PRD
- synced the canonical runner fixes into the public repo

### Verification

- `python3 -m unittest tests.test_skill_package tests.test_benchmark tests.test_runner tests.test_claude_install`
- Codex GitHub installer packaging validated from the public repo
- Codex runtime first response validated with `$planloop install telegram-mcp-server`
- Claude Code helper install validated from a fresh GitHub clone
