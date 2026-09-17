# Hashcraft

[![CI](https://github.com/Bangkahdev/hashcraft/actions/workflows/ci.yml/badge.svg)](https://github.com/Bangkahdev/hashcraft/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A deterministic candidate-generation and cryptographic
digest-verification CLI for authorized security research, password
auditing, CTFs, and security education.

Repository: <https://github.com/Bangkahdev/hashcraft>

Hashcraft is **not** a password cracker or a SHA-256 decryptor. It
does not decrypt hashes, collect OSINT automatically, access accounts,
or attempt online authentication.

## Authorized Use Only

Use this tool **only** against systems, accounts, and hashes that you
own, or that you are explicitly authorized to test:

- Capture-the-flag (CTF) competitions
- Laboratory / training environments you control
- Lawful, sanctioned security research
- Penetration tests you have written authorization to perform

Using Hashcraft against systems or credentials you do not own and are
not explicitly authorized to test may be illegal in your jurisdiction.
You are solely responsible for how you use this tool.

## 100% local, no telemetry

Hashcraft operates **entirely on your own machine**. It contains:

- no telemetry or analytics of any kind
- no remote candidate submission
- no external API requirement
- no credential collection
- no online authentication attempts
- no automated scraping

Everything -- candidate generation and digest verification alike --
happens locally, offline, in this process.

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/Bangkahdev/hashcraft.git
cd hashcraft
pip install .
```

This exposes the `hashcraft` command on your `PATH`. To confirm it
installed correctly:

```bash
hashcraft version
hashcraft info
```

For development (editable install plus test/lint/type-check tooling),
see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Quick start

### Generate a wordlist to a file

```bash
hashcraft generate \
  --names atha,bangkah \
  --cities lhokseumawe \
  --years 2025,2026 \
  --max-words 3 \
  --output wordlist.txt
```

Every stage of generation -- source tokens, ordered word combinations,
case variants, optional leetspeak, separators, and optional
prefix/suffix symbols -- is deterministic: the same inputs and
options always produce the same candidates in the same order, on
Linux, Windows, and macOS alike.

### Preview a run without generating anything (`--dry-run`)

Before committing to a large run, `--dry-run` reports the inputs,
active options, a conservative size estimate, the configured
`--max-combinations` / `--limit` ceilings, and the exact filter-aware
candidate count -- without ever creating an output file:

```bash
hashcraft generate \
  --keywords atha,bangkah \
  --leet --symbols \
  --max-words 2 \
  --dry-run
```

### Verify a digest against a wordlist or a live pipe

Hashcraft supports `sha256` (the default), `md5`, `sha1`, `sha512`,
and `blake2b`:

```bash
hashcraft verify \
  --algorithm sha256 \
  --hash <64-hex-digest> \
  --wordlist wordlist.txt
```

```bash
hashcraft verify --algorithm md5 --hash <32-hex-digest> --wordlist wordlist.txt
```

Or pipe `generate` straight into `verify` without writing anything to
disk, via `--stdout` / `--stdin`:

```bash
hashcraft generate --names atha --stdout | \
  hashcraft verify --algorithm sha256 --hash <64-hex-digest> --stdin
```

`generate --stdout` emits exactly one candidate per line and nothing
else on standard output, so it composes cleanly with `verify --stdin`
or any other tool in a pipeline. On a match, `verify` prints the
matching candidate and exits `0`; if the entire input is consumed
with no match, it exits `4`. See `hashcraft generate --help` and
`hashcraft verify --help` for the full set of options (source
selection, `--case`, `--separators`, `--max-length`,
`--max-combinations`, `--limit`, `--overwrite`, and more).

### Speed up large wordlists with `--jobs` / `-j`

For a big `--wordlist`, spread the hashing work across multiple CPU
cores:

```bash
hashcraft verify --algorithm sha256 --hash <digest> \
  --wordlist large_wordlist.txt --jobs 4
```

`--jobs` (or `-j`) defaults to `1` (single-process, identical to
running with no flag at all). `--jobs 0` auto-detects your CPU count.
Whatever value you pick, every worker process stops immediately the
moment a match is found -- Hashcraft never keeps hashing in the
background after it already has an answer.

**Resource note:** each unit of `--jobs` is a full worker process, not
a lightweight thread. Setting it far above your machine's CPU count
doesn't speed anything up and just adds process-creation overhead and
memory pressure; `--jobs 0` (auto-detect) or a small explicit number
close to your core count is almost always the right choice. This is a
local resource-usage concern, not a network-facing one -- see
[`SECURITY.md`](SECURITY.md) for how it's scoped there.

## A note on one-way hash functions and what "no match" means

Every algorithm Hashcraft supports (SHA-256, MD5, SHA-1, SHA-512,
BLAKE2b) is a **one-way** cryptographic hash function: there is no
general way to recover an original input from its digest alone. When
`hashcraft verify` reports no match, that means only that **none of
the candidates it was given** produced the target digest -- it does
not mean, and cannot prove, that no plaintext producing that digest
exists. A negative result reflects the limits of the candidate list
and generation options you supplied, not a property of the hash
algorithm itself.

MD5 and SHA-1 are also considered cryptographically broken for
collision resistance (unrelated inputs can be made to produce the
same digest) -- that doesn't change what a Hashcraft match or
non-match tells you here, but don't rely on either algorithm anywhere
collision resistance actually matters.

## Exit codes

| Code | Meaning |
| ---- | ------- |
| `0`  | Successful generation, or a verification match |
| `1`  | Internal / general error |
| `2`  | Invalid command-line arguments |
| `3`  | Invalid input (including a malformed digest or unreadable input) |
| `4`  | Verification completed with no match |
| `5`  | A preflight or runtime resource limit (`--max-combinations` / `--limit`) was exceeded |

## What's new in v2

- **Multiple digest algorithms**: `--algorithm` now accepts `md5`,
  `sha1`, `sha256` (default), `sha512`, and `blake2b`, behind a
  pluggable registry (`hashing/algorithms.py`) -- adding another
  `hashlib`-backed algorithm doesn't require touching the verifier.
- **Parallel verification**: `verify --jobs`/`-j` distributes
  candidate hashing across multiple CPU-core worker processes for
  large wordlists, while still guaranteeing an exact, reproducible
  `checked_count` and immediate termination of every worker as soon
  as a match is found.
- **Not yet implemented**: mask/pattern-based candidate generation
  (`--mask`, e.g. hashcat-style `?d?d` placeholders) is part of the
  broader v2 proposal but is intentionally **not** included in this
  release -- its exact pattern syntax needs to be pinned down first.
  `generate` still covers case, leetspeak, separators, and symbol
  variants as in v1.

See [`CHANGELOG.md`](CHANGELOG.md) for the full, itemized history.

## More documentation

- [`CHANGELOG.md`](CHANGELOG.md) -- what changed, release by release.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) -- development setup, running
  tests/lint/type-checks, and the project's core invariants.
- [`SECURITY.md`](SECURITY.md) -- how to report a vulnerability, and
  what's in scope for this project.
- [`LICENSE`](LICENSE) -- MIT.

## License

MIT -- see [`LICENSE`](LICENSE).