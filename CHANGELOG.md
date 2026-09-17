# Changelog

All notable changes to Hashcraft are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (0.2.0 -- v2)

- Multi-algorithm hashing: `verify --algorithm` now accepts `md5`,
  `sha1`, `sha256` (default, unchanged from v1), `sha512`, and
  `blake2b`, behind a pluggable strategy-pattern registry in
  `hashing/algorithms.py` (`register_algorithm`,
  `supported_algorithm_names`, `get_algorithm`) -- adding another
  `hashlib`-backed algorithm needs no change to `hashing/verifier.py`.
- Digest validation is now parametrized by the selected algorithm's
  digest length (32 hex chars for md5, 40 for sha1, 64 for sha256, 128
  for sha512/blake2b) instead of v1's SHA-256-only hardcoded 64.
- Parallel verification: `verify --jobs`/`-j` distributes candidate
  hashing across multiple worker processes via `multiprocessing.Pool`
  for large `--wordlist` runs. Uses the *ordered* `Pool.imap` (not
  `imap_unordered`) so results are consumed in the original candidate
  order, giving an exact, run-to-run-reproducible `checked_count` while
  still terminating every worker immediately on the first match
  (`--jobs` omitted -> `1`, sequential, byte-identical to v1; `--jobs
  0` -> auto-detect CPU count via `os.cpu_count()`; `--jobs N` -> N
  workers).
- `hashing/validators.py`'s `InvalidDigestError` message and
  `validate_and_normalize_digest` are generalized to any expected hex
  length rather than being SHA-256-specific in wording.
- `info` now lists every currently-registered algorithm instead of a
  hardcoded "sha256".
- 39 new tests covering: known-answer vectors for all five algorithms;
  per-algorithm digest-length validation; parallel match, no-match,
  short-circuit termination (proven by checked-candidate count, not
  timing), and exact determinism of `checked_count` across five
  repeated runs; an ad hoc/unregistered `HashAlgorithm` working with
  `jobs=1` but failing fast and clearly with `jobs>1`; and the full
  `--algorithm` / `--jobs` / `-j` surface through the CLI layer.
- `pyproject.toml`: `[tool.mypy] strict = true` (PRD v2's explicit
  "zero errors under mypy strict" requirement); version bumped to
  `0.2.0`.

### Changed (0.2.0 -- v2)

- `hashing.verifier.verify()` gained `jobs` and `chunk_size` keyword
  parameters (both optional, defaulting to `1` and `2000`); every
  existing call site and test that doesn't pass them is unaffected.
- The `Sha256Algorithm` class from v1 no longer exists as a public
  symbol; use `get_algorithm("sha256")` instead (this is what
  `hashing/verifier.py`'s own default now does internally).

### Not included in this release

- Basic mask/pattern processing (`--mask`, e.g. hashcat-style `?d?d`
  digit placeholders) was proposed alongside the v2 features above but
  is **not** implemented here: its exact pattern syntax and how it
  composes with the existing case/leetspeak/separator/symbol pipeline
  needs to be pinned down first, and it wasn't part of the v2
  implementation checklist's five tasks. `generate` is unchanged from
  v1 in this respect.

### Added (0.1.0 -- v1 baseline)

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
- `verify` command: local SHA-256 verification against a `--wordlist
  PATH` or `--stdin` candidate stream, behind a `HashAlgorithm`
  protocol so future algorithms can be added without changing the
  verifier -- extended to multiple algorithms in 0.2.0, above. Digest
  validation happens before any candidate input is read.
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

- Nothing has been tagged/released on GitHub yet, so both the v1
  baseline and the v2 additions above are grouped under a single
  `[Unreleased]` heading; they'll split into their own dated `##
  [0.1.0]` / `## [0.2.0]` sections once each is actually tagged.
- TOML configuration, JSON/CSV output, external transform plugins,
  enhanced progress rendering, checkpoint/resume support, and the
  mask/pattern feature noted above remain deferred to a future release.

[Unreleased]: https://github.com/Bangkahdev/hashcraft/compare/v0.1.0...HEAD
