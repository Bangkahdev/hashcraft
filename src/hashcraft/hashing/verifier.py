"""Local SHA-256 candidate verification (PRD 7).

Every candidate is encoded with UTF-8 explicitly, hashed locally, and
compared case-insensitively against the normalized target digest
(PRD 7). This module is a standalone, independently callable Python
API (PRD 9): ``verify`` takes an already-open candidate iterator and a
raw target digest, and performs no network access, credential
collection, or online authentication -- consistent with PRD 3's
"operate entirely locally" constraint.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import TextIO

from .algorithms import HashAlgorithm, Sha256Algorithm
from .validators import validate_and_normalize_digest

_DEFAULT_ALGORITHM: HashAlgorithm = Sha256Algorithm()


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a ``verify`` run (PRD 7).

    ``matched`` corresponds to CLI exit code 0 (a match) versus exit
    code 4 (fully consumed input, no match) from PRD 8.
    ``checked_count`` is the number of candidates hashed and compared,
    including the matching one when ``matched`` is True -- PRD 7: "On
    a match, print the candidate and number of candidates checked."
    """

    matched: bool
    matched_candidate: str | None
    checked_count: int


def iter_wordlist_file_lines(path: str | os.PathLike[str]) -> Iterator[str]:
    """Stream one UTF-8 candidate per line from a ``--wordlist PATH`` file.

    Unlike ``sources.text``'s token readers (which strip *all*
    surrounding whitespace -- appropriate for short, user-typed
    keywords), this strips only the trailing newline. A wordlist
    candidate must round-trip exactly through hashing: stripping
    incidental leading/trailing whitespace here could silently turn a
    real match into a miss.
    """
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            yield line.rstrip("\n")


def iter_stdin_candidate_lines(stream: TextIO) -> Iterator[str]:
    """Stream one UTF-8 candidate per line from ``--stdin``.

    Suitable for a ``generate --stdout`` pipeline (PRD 6, 7):
    ``generate --stdout`` emits exactly one candidate followed by
    ``\\n`` per line and nothing else (PRD 6), so reading lines here
    and stripping only the trailing newline round-trips each candidate
    exactly, with no re-normalization.
    """
    for line in stream:
        yield line.rstrip("\n")


def verify(
    candidates: Iterable[str],
    target_digest: str,
    *,
    algorithm: HashAlgorithm = _DEFAULT_ALGORITHM,
) -> VerificationResult:
    """Hash and compare each candidate against ``target_digest`` (PRD 7).

    ``target_digest`` is validated and case-normalized first via
    ``validators.validate_and_normalize_digest`` -- PRD 7: "Invalid
    digests fail before the wordlist is read," so this validation
    happens before ``candidates`` is iterated at all, and
    ``InvalidDigestError`` propagates to the caller unchanged.

    Each candidate is encoded as UTF-8 explicitly (PRD 7) before
    hashing. Iteration stops at the first match. On a fully consumed
    ``candidates`` with no match, the returned result has
    ``matched=False`` (PRD 7's exit-code-4 case); no complete candidate
    collection is ever materialized -- candidates are consumed one at
    a time from the iterator.
    """
    normalized_digest = validate_and_normalize_digest(target_digest)

    checked_count = 0
    for candidate in candidates:
        checked_count += 1
        digest = algorithm.hexdigest(candidate.encode("utf-8"))
        if digest == normalized_digest:
            return VerificationResult(
                matched=True,
                matched_candidate=candidate,
                checked_count=checked_count,
            )

    return VerificationResult(
        matched=False,
        matched_candidate=None,
        checked_count=checked_count,
    )
