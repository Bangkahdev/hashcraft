# Changelog

All notable changes to Hashcraft are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-09-18

### Added (v2.0.0)

- **Multi-algorithm hashing**: `verify --algorithm` now accepts `md5`, `sha1`, `sha256` (default, unchanged from v1), `sha512`, and `blake2b`, behind a pluggable strategy-pattern registry in `hashing/algorithms.py` (`register_algorithm`, `supported_algorithm_names`, `get_algorithm`) — adding another `lib`-backed algorithm needs no change to `hashing/verifier.py`.
- **Parametrized digest validation**: Digest validation is now parameterized by the selected algorithm's digest length (32 hex chars for md5, 40 for sha1, 64 for sha256, 128 for sha512/blake2b) instead of v1's SHA-256-only hardcoded 64.
- **Parallel verification**: `verify --jobs`/`-j` distributes candidate hashing across multiple worker processes via `multiprocessing.Pool` for large `--wordlist` runs. Uses the *ordered* `Pool.imap` so results are consumed in original candidate order, giving an exact, run-to-run-reproducible `checked_count` while still terminating every worker immediately on the first match (`--jobs` omitted -> `1`, sequential; `--jobs 0` -> auto-detect CPU count via `os.cpu_count()`; `--jobs N` -> N workers).
- **Generalized validators**: `hashing/validators.py`'s `InvalidDigestError` message and `validate_and_normalize_digest` are generalized to any expected hex length rather than being SHA-256-specific in wording.
- **Dynamic info command**: `info` now lists every currently-registered algorithm instead of a hardcoded "sha256".
- **Comprehensive test coverage**: 39 new tests covering known-answer vectors for all five algorithms; per-algorithm digest-length validation; parallel match, no-match, short-circuit termination (proven by checked-candidate count), and exact determinism of `checked_count` across repeated runs; an ad hoc/unregistered `HashAlgorithm` working with `jobs=1` but failing fast with `jobs>1`; and the full `--algorithm` / `--jobs` / `-j` CLI surface.
- **Strict type checking**: `pyproject.toml` updated with `[tool.mypy] strict = true` ensuring zero errors under strict mypy requirements.

### Changed (v2.0.0)

- `hashing.verifier.verify()` gained `jobs` and `chunk_size` keyword parameters (defaulting to `1` and `2000`).
- The `Sha256Algorithm` class from v1 no longer exists as a public symbol; use `get_algorithm("sha256")` instead.

### Not included in this release

- Basic mask/pattern processing (`--mask`, e.g., hashcat-style `?d?d` digit placeholders) remains deferred for future implementation pending pipeline composition design.

---

## [0.1.0] - v1 Baseline

### Added
- **`generate` command**: Deterministic candidate generation from CLI keyword sources (`--names`, `--usernames`, `--pets`, `--cities`, `--vehicles`, `--food`, `--hobbies`, `--organizations`, `--keywords`, `--years`, `--dates`), `--input` files, and `--stdin`, with NFC Unicode normalization by default (`--unicode-normalization`).
- **Canonical generation pipeline**: Ordered token combinations (`--max-words`), case variants (`--case`), bounded leetspeak substitution (`--leet`, `--max-leet-variants`), configurable separators (`--separators`), and prefix/suffix symbol variants (`--symbols`, `--symbols-list`), followed by a Unicode-code-point length filter (`--max-length`) and per-seed structural deduplication.
- **Preflight resource limits**: A two-pass, filter-aware `--max-combinations` ceiling and an independent `--limit` ceiling on emitted candidates, plus `--dry-run`, `--yes`, and `--warn-threshold`-gated interactive confirmations.
- **Atomic file output**: `--output PATH` writes through a sibling temporary file, replaced onto the destination only on success (`--overwrite` required if destination exists).
- **Clean `--stdout` output contract**: Exactly one candidate per line, free of banner, status, or progress output.
- **`verify` command**: Local SHA-256 verification against a `--wordlist PATH` or `--stdin` candidate stream behind a `HashAlgorithm` protocol.
- **CLI Utilities**: `info` and `version` commands.
- **Exit-code contract**: `0` success/match, `1` internal error, `2` invalid arguments, `3` invalid input, `4` verification completed with no match, `5` resource limit hit.
- **Test suite & Packaging**: Complete `tests/` coverage, `pyproject.toml` packaging configuration, MIT License, security policy, contribution guidelines, and GitHub Actions CI workflow running Ruff, mypy, and pytest across Python 3.10–3.13.

[2.0.0]: https://github.com/Bangkahdev/hashcraft/compare/v0.1.0...v2.0.0
[0.1.0]: https://github.com/Bangkahdev/hashcraft/releases/tag/v0.1.0