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

### Verify a SHA-256 digest against a wordlist or a live pipe

Check candidates from a file:

```bash
hashcraft verify \
  --algorithm sha256 \
  --hash <64-hex-digest> \
  --wordlist wordlist.txt
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

## A note on SHA-256 and what "no match" means

SHA-256 is a **one-way** cryptographic hash function: there is no
general way to recover an original input from its digest alone. When
`hashcraft verify` reports no match, that means only that **none of
the candidates it was given** produced the target digest -- it does
not mean, and cannot prove, that no plaintext producing that digest
exists. A negative result reflects the limits of the candidate list
and generation options you supplied, not a property of SHA-256 itself.

## Exit codes

| Code | Meaning |
| ---- | ------- |
| `0`  | Successful generation, or a verification match |
| `1`  | Internal / general error |
| `2`  | Invalid command-line arguments |
| `3`  | Invalid input (including a malformed SHA-256 digest or unreadable input) |
| `4`  | Verification completed with no match |
| `5`  | A preflight or runtime resource limit (`--max-combinations` / `--limit`) was exceeded |

## More documentation

- [`CHANGELOG.md`](CHANGELOG.md) -- what changed, release by release.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) -- development setup, running
  tests/lint/type-checks, and the project's core invariants.
- [`SECURITY.md`](SECURITY.md) -- how to report a vulnerability, and
  what's in scope for this project.
- [`LICENSE`](LICENSE) -- MIT.

## License

MIT -- see [`LICENSE`](LICENSE).
