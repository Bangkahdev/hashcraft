# Security Policy

## Scope

Hashcraft is a local-first CLI (PRD section 3): it generates candidate
strings and verifies digests (SHA-256, MD5, SHA-1, SHA-512, BLAKE2b --
PRD v2 section A) entirely on the machine it runs on. It performs no
network access, telemetry, remote candidate submission, credential
collection, or online authentication attempts. Because of that scope,
most classes of "remote" vulnerability (data exfiltration to a third
party, remote code execution over a network protocol, etc.) do not
apply to this tool by construction. Security
reports for this project are about bugs in Hashcraft's own code that
could:

- cause it to read, write, or delete files outside the paths the user
  explicitly requested (for example, a path-traversal or
  symlink-following bug in `--output` / `--input` / `--wordlist`
  handling);
- corrupt or silently truncate output in a way that could hide a
  successful match or a failed run as if it had succeeded (undermining
  the atomic-write and exit-code guarantees in PRD sections 5 and 8);
- cause a denial of service on the local machine well beyond what the
  documented `--max-combinations` / `--limit` ceilings (PRD section 5)
  are supposed to prevent, including via `verify --jobs` spawning
  worker processes (PRD v2 section B);
- misrepresent what a match or non-match from `verify` means in a way
  that could mislead a user (PRD section 7), for any supported
  algorithm.

Reports about the *inherent* limitations of brute-force/dictionary
candidate generation, or of the supported hash algorithms themselves
(they are fast, unsalted hashes -- this is well known and is not a
Hashcraft vulnerability; MD5 and SHA-1 are additionally known to be
collision-broken, which is exactly why Hashcraft is not the right tool
for anything that needs collision resistance), are out of scope; the
README's "Authorized Use Only" section and PRD section 7's one-way-hash
caveat already document these limitations.

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |
| < 0.1   | No (pre-release) |

Once later minor/major versions are released, only the most recent
minor version will receive security fixes unless stated otherwise
here.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for a suspected security
vulnerability.

Instead, please report it privately using GitHub's "Report a
vulnerability" button under this repository's **Security** tab, or go
directly to
<https://github.com/Bangkahdev/hashcraft/security/advisories/new>.
This opens a private draft advisory visible only to maintainers until
a fix is ready.

<!--
TODO(maintainer): if you would prefer an email-based reporting
channel in addition to GitHub Security Advisories, replace this note
with a real, monitored security contact address. An unverified,
placeholder address is deliberately not included here.
-->

When reporting, please include:

- the Hashcraft version (`hashcraft version`) and Python version;
- the operating system;
- the exact command line (or API call, if you're using Hashcraft as a
  library) that reproduces the issue;
- what you expected to happen, and what happened instead;
- if relevant, whether the issue involves `--output` file handling,
  `--limit`/`--max-combinations` enforcement, or digest verification,
  since those are the areas listed in "Scope" above.

### What to expect

- Acknowledgement of a new report: within 5 business days.
- An initial assessment (confirmed, needs more information, or not a
  security issue): within 14 days of acknowledgement.
- If confirmed, we aim to publish a fix and a coordinated disclosure
  (a GitHub Security Advisory with credit to the reporter, unless you
  prefer to remain anonymous) as soon as reasonably possible; complex
  fixes may take longer, and we'll keep you updated on the advisory
  thread.

We ask that you give us a reasonable opportunity to fix a
confirmed issue before any public disclosure.

## Non-Security Bugs

For anything that doesn't fit the "Scope" section above -- incorrect
CLI behavior, unexpected exit codes, generation logic that doesn't
match the documented pipeline, etc. -- please use a regular public
GitHub issue instead of this security process. See `CONTRIBUTING.md`
for how to file and (optionally) fix those.
