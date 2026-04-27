# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Pending future iterations.

## [2026-04-27]

### Added

- Initialized Git repository and published the first GitHub version.
- Added repository `README.md` with usage instructions and output isolation rules.
- Added `LICENSE` for open-source reuse.
- Added GitHub issue templates for bug reports and feature requests.

## [2026-04-23]

### Changed

- Isolated dashboard output to `outputs/dashboard`.
- Isolated sandbox validation output to `outputs/sandbox`.
- Isolated default manual script output to `outputs/manual`.

### Added

- `dashboard_runtime_config.json`
- `sandbox_runtime_config.json`
- `run_analysis_sandbox.ps1`
- `run_analysis_manual.ps1`

## [2026-04-20] - [2026-04-22]

### Added

- Multi-horizon recommendation support for `1d`, `4h`, and `1h`.
- Dashboard service with hourly scheduled execution.
- Recommendation scoring, recommendation tiers, and structured JSON output.
- Requirements, design, and plan documents under `docs/codex/v1/`.
