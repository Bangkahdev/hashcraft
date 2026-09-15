# PRD — Hashcraft

**Status:** v0.1 implementation-ready revision  
**Target:** Open-source / public GitHub  
**Platform:** Linux, Windows, macOS  
**Language:** Python 3.10+  
**License:** MIT  
**Interface:** CLI  
**Packaging:** PyPI-ready

## 1. Product statement

Hashcraft is a local-first CLI that deterministically generates candidate strings from user-supplied keywords and can compare their UTF-8 SHA-256 digests with a supplied digest. It is intended for authorized security research, password auditing, CTFs, and cryptographic education.

It does not decrypt hashes, collect OSINT automatically, access accounts, attempt online authentication, or claim universal password recovery.

## 2. v0.1 outcome

The release is complete when `pip install .` exposes `hashcraft`, and the package provides:

- `generate` for deterministic, streaming candidate generation;
- `verify` for local SHA-256 candidate verification;
- CLI argument, file, and standard-input sources;
- case variants, ordered word combinations, separators, optional symbols, and bounded leetspeak;
- preflight estimation plus explicit resource limits;
- text-file and standard-output destinations;
- type hints, tests, linting, type checking, GitHub Actions, README, SECURITY.md, CONTRIBUTING.md, CHANGELOG.md, and MIT license.

TOML configuration, multiple digest algorithms, JSON/CSV, external transform plugins, and enhanced progress rendering are deferred to v0.2+.

## 3. Authorized use and privacy

The tool must operate entirely locally. It must contain no telemetry, analytics, remote candidate submission, external API requirement, credential collection, online authentication attempts, or automated scraping.

The README must include an **Authorized Use Only** section: use is limited to systems and hashes the user owns or is explicitly authorized to test, CTFs, laboratory work, lawful research, and permitted penetration tests.

The README must also state that SHA-256 is a one-way cryptographic hash function. A failed verification means only that none of the generated candidates matched the supplied digest; it does not establish that an original plaintext does not exist.

## 4. Canonical generation contract

For a fixed program version, normalized inputs, and configuration, output candidates and their order must be identical across supported platforms.

The v0.1 pipeline is normative:

```text
sources → normalized tokens → ordered combinations → case variants
        → leetspeak variants → separators → symbol variants
        → length filter → structural deduplication → emit
```

All stages are iterators. The implementation must not materialize the complete candidate space with `list(...)`, a set, or an equivalent whole-dataset collection.

### 4.1 Sources and normalization

Supported comma-separated options are `--names`, `--usernames`, `--pets`, `--cities`, `--vehicles`, `--food`, `--hobbies`, `--organizations`, `--keywords`, `--years`, and `--dates`. `--input PATH` accepts one token per line; `--stdin` accepts one token per line from standard input.

Tokens are read in CLI-option order, then input-file order, then stdin order. Whitespace surrounding a token is stripped; empty tokens are discarded. Categories are metadata only in v0.1 and do not alter generation or ordering. Input is decoded as UTF-8.

Before any transformation, every token is normalized with Unicode NFC. NFC makes canonically equivalent input (for example a precomposed `é` and `e` plus a combining acute accent) produce the same candidate while preserving compatibility distinctions. The tool must not use NFKC by default: compatibility normalization can alter user-intended text and blur security-relevant confusables. `--unicode-normalization nfc|none` is provided for explicit control, defaults to `nfc`, and is included in dry-run output and reproducibility documentation. Case and length processing occur after normalization; `--max-length` is applied to the final normalized candidate.

### 4.2 Combinations

For `n` normalized tokens and `--max-words D`, emit every ordered permutation without token reuse for lengths 1 through `min(D, n)`. Therefore `atha_bangkah` and `bangkah_atha` are different, while `atha_atha` is not generated from a single occurrence of `atha`.

The default depth is 2. `--max-words` must be a positive integer and may not exceed the hard limit configured for the invocation. Each ordered token sequence subsequently receives each configured separator between all adjacent words; an empty separator is valid.

### 4.3 Transformations

`--case` accepts `lower`, `upper`, `capitalize`, or `all` (default). `all` emits exactly that sequence after removing variants that are identical within the same input candidate.

Default separators are `""`, `_`, `.`, and `-`; `--separators` supplies a comma-separated replacement list in the supplied order.

Symbols are disabled unless `--symbols` is supplied. When enabled, each configured symbol produces a prefix variant and a suffix variant. The default symbol list is `!`, `@`, `#`, `$`, `_`, `-`; `--symbols-list` replaces it in supplied order. `--no-symbols` is accepted only to override a future config default.

`--leet` enables substitutions `a→@`, `e→3`, `i→1`, `o→0`, `s→$`, and `t→7`. It generates the unmodified candidate followed by replacement combinations in deterministic left-to-right position order. Leetspeak generation is bounded by `--max-leet-variants`, default 64, and stops producing further variants for that candidate at the bound.

### 4.4 Filtering and deduplication

`--max-length` defaults to 32 and is measured in Unicode code points, not UTF-8 bytes. Candidates longer than the limit are not emitted.

Structural deduplication is precisely defined as follows: for one ordered token sequence and one separator, the generator maintains a small insertion-ordered set of the candidate variants derived from that seed. A value is emitted once at its first occurrence and the set is discarded before the next seed. This removes repetitions caused by case, leetspeak, or symbol transforms in that seed, such as `123` under lower/upper/capitalize. Its memory is bounded by the per-seed transform caps, not by the total stream.

v0.1 does not promise global deduplication across distinct seeds or source duplicates, because exact global deduplication has unbounded memory cost. This distinction, including examples, must appear in the CLI reference and tests.

## 5. Limits and preflight

`--max-combinations` is a preflight hard ceiling on a filter-aware candidate count. The preflight runs the same streaming pipeline with output disabled, applies normalization, final-length filtering, and per-seed structural deduplication, and counts until the ceiling plus one. It retains no complete candidate collection. This gives the exact number of candidates that v0.1 would emit (or proves it exceeds the ceiling), avoiding false rejection from an intentionally oversized Cartesian-product estimate. Generation then runs the identical deterministic pipeline a second time.

Dry-run reports both a cheap raw upper bound and the filter-aware count; only the latter is used for the hard preflight decision. The cost of this two-pass planning behavior must be documented. It trades additional CPU time for predictable limits and no false-positive limit error.

`--limit` is an independent hard ceiling on candidates actually emitted. Its default is 100,000. `--max-combinations` defaults to 500,000. Both values must be positive integers. The application rejects an estimate above `--max-combinations` with exit code 5 before emitting output.

If the emitted-candidate limit would be exceeded, generation stops with exit code 5. For file output, write to a sibling temporary file and atomically replace the destination only after successful completion; discard the temporary file on failure. Standard output may already contain earlier candidates when this error occurs, so scripts must treat exit status as authoritative.

`--dry-run` prints only the inputs, active options, conservative estimate, configured ceilings, and an approximate output size; it never creates an output file. If the estimate is below the hard ceiling but above a configurable warning threshold, interactive terminals require confirmation unless `--yes` is supplied. `--yes` never bypasses a hard limit.

`--overwrite` alone authorizes replacement of an existing output file. It is deliberately distinct from `--yes`.

## 6. CLI

```text
hashcraft generate [SOURCE OPTIONS] [GENERATION OPTIONS] [OUTPUT OPTIONS]
hashcraft verify --algorithm sha256 --hash DIGEST (--wordlist PATH | --stdin)
hashcraft info
hashcraft version
```

Examples:

```bash
hashcraft generate --names atha,bangkah --cities lhokseumawe \
  --years 2025,2026 --max-words 3 --output wordlist.txt

hashcraft generate --names atha --stdout | \
  hashcraft verify --algorithm sha256 --hash <64-hex-digest> --stdin

hashcraft generate --keywords atha,bangkah --leet --symbols --dry-run
```

`generate --stdout` emits one candidate followed by `\n` per line and nothing else on standard output: no banner, preflight report, warning, progress, or color-control sequence. Status, warnings, preflight reports, progress, and errors use `stderr`. Progress is disabled automatically when candidate output is piped, and `--quiet` additionally suppresses non-error status on `stderr`; it never suppresses errors or changes exit codes. A separate `--raw` flag is unnecessary because `--stdout` already defines the stable machine-readable text contract.

## 7. Verification

v0.1 supports `sha256` only, using an implementation behind a `HashAlgorithm` protocol so later algorithms can be added without changing the verifier.

Every candidate is encoded with UTF-8 explicitly, hashed locally, and compared case-insensitively against the normalized target digest. A SHA-256 digest must contain exactly 64 hexadecimal characters. Invalid digests fail before the wordlist is read.

On a match, print the candidate and number of candidates checked, then return exit code 0. A fully consumed input with no match returns exit code 4. `verify --stdin` reads one UTF-8 candidate per line and is suitable for a `generate --stdout` pipeline.

## 8. Errors and exit codes

Normal CLI errors must be concise, actionable, and traceback-free. `--debug` may add diagnostic detail.

```text
0  successful generation or a verification match
1  internal/general error
2  invalid command-line arguments
3  invalid input (including malformed SHA-256 digest or unreadable input)
4  verification completed with no match
5  preflight or runtime resource limit exceeded
```

## 9. Architecture

```text
src/hashcraft/
  cli.py                 command parsing and exit-code mapping
  models.py              typed immutable configuration models
  sources/text.py        UTF-8 CLI/file/stdin token iterators
  generation/combinations.py
  generation/estimate.py
  generation/generator.py
  generation/limits.py
  transforms/case.py
  transforms/leetspeak.py
  transforms/symbols.py
  hashing/algorithms.py
  hashing/validators.py
  hashing/verifier.py
  output/text.py
```

The generator, verifier, sources, and output writer must be independently callable Python APIs. The CLI is an adapter over those APIs.

## 10. Test and release gates

Tests must cover known SHA-256 vectors for `""`, `"hello"`, and `"password123"`; digest validation; all transformations; leetspeak cap; empty and duplicate inputs; combination depth and order; deterministic output; UTF-8 handling; maximum length; preflight and runtime limits; atomic file behavior; stdin/stdout piping; and every documented exit code.

CI runs Ruff, mypy, and pytest on Python 3.10, 3.11, 3.12, and 3.13. Packaging validation must build the distributable and install it in a clean environment before release.

## 11. Non-goals

v0.1 excludes automated OSINT or social-media collection, username or birthday discovery, external wordlist integration, GPU/distributed generation, online authentication testing, credential stuffing, application-specific password-storage formats, salts, advanced KDFs, and integrations with password-cracking tools.

Checkpointing and persistent resume are deferred to v0.2. A correct resume format must bind its checkpoint to the program version, complete normalized input/configuration fingerprint, pipeline ordering, and output destination, and must specify behavior for a changed source file. v0.1 may add `--skip N` only if needed: it deterministically discards the first `N` would-be-emitted candidates without storing state, but is deliberately not presented as an efficient resume mechanism.

## 12. Positioning

> A deterministic candidate-generation and cryptographic digest-verification CLI for authorized security research, password auditing, CTFs, and security education.

It is not a password cracker or a SHA-256 decryptor.
