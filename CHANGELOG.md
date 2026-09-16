# Changelog

All notable changes to Hashcraft are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `generate` command: deterministic candidate generation from CLI
  keyword sources (`--names`, `--usernames`, `--pets`, `--cities`,
  `--vehicles`, `--food`, `--hobbies`, `--organizations`, `--keywords`,
  `--years`, `--dates`), `--input` files, and `--stdin`, with NFC
  Unicode normalization by default (`--unicode-normalization`).
- Canonical generation pipeline: ordered token combinations
  (`--max-words`), case variants (`--case`), bounded leetspeak
  substitution (`--leet`, `--max-leet-variants`), configurable
  separators (`--separators`), and prefix/suffix symbol variants
  (`--symbols`, `--symbols-list`), followed by a Unicode-code-point
  length filter (`--max-length`) and per-seed structural
  deduplication. Every stage is a generator; the complete candidate
  space is never materialized.
- Preflight resource limits: a two-pass, filter-aware
  `--max-combinations` ceiling (exact up to the ceiling, without
  buffering the full candidate collection) and an independent
  `--limit` ceiling on candidates actually emitted, plus `--dry-run`,
  `--yes`, and a `--warn-threshold`-gated interactive confirmation for
  large runs.
- Atomic file output: `--output PATH` writes through a sibling
  temporary file, replaced onto the destination only on success
  (`--overwrite` required to replace an existing file); temp files are
  discarded on any failure, including a `--limit` overrun.
- Clean `--stdout` output contract: exactly one candidate per line,
  with no banner, status, or progress output mixed in.
- `verify` command: local SHA-256 verification (`--algorithm sha256`)
  against a `--wordlist PATH` or `--stdin` candidate stream, behind a
  `HashAlgorithm` protocol so future algorithms can be added without
  changing the verifier. Digest validation (exactly 64 hex characters,
  case-insensitive comparison) happens before any candidate input is
  read.
- `info` and `version` commands.
- Exit-code contract: `0` success/match, `1` internal error, `2`
  invalid arguments, `3` invalid input, `4` verification completed
  with no match, `5` a resource limit was hit.
- Full test suite (`tests/`) covering the SHA-256 known-answer vectors
  for `""`, `"hello"`, and `"password123"`; digest validation; every
  transformation (case, leetspeak, symbols); the leetspeak variant
  cap; per-seed structural deduplication (including its documented
  non-global-dedup behavior); preflight and runtime resource limits;
  atomic file-write behavior; the stdin/stdout pipeline; and every
  documented exit code.
- Packaging (`pyproject.toml`), `LICENSE` (MIT), `SECURITY.md`,
  `CONTRIBUTING.md`, and a GitHub Actions CI workflow running Ruff,
  mypy, and pytest across Python 3.10-3.13 and Linux/Windows/macOS,
  plus a packaging validation job that builds the distributable and
  installs it into a clean environment.

### Notes

- This project has not yet had a `0.1.0` tagged release; entries above
  will move under a `## [0.1.0]` heading with a date once it is cut.
- TOML configuration, additional digest algorithms, JSON/CSV output,
  external transform plugins, enhanced progress rendering, and
  checkpoint/resume support are intentionally deferred to a future
  `0.2.0` (see the PRD's section 2 and section 11).

[Unreleased]: https://github.com/Bangkahdev/hashcraft/compare/v0.1.0...HEAD
