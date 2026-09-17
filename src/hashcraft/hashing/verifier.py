"""Local candidate verification, sequential and parallel (PRD 7; v2
section B).

Every candidate is encoded with UTF-8 explicitly, hashed locally, and
compared case-insensitively against the normalized target digest
(PRD 7). This module is a standalone, independently callable Python
API (PRD 9): ``verify`` takes an already-open candidate iterator and a
raw target digest, and performs no network access, credential
collection, or online authentication -- consistent with PRD 3's
"operate entirely locally" constraint. That holds for the v2
multiprocessing path too: worker processes only ever hash local
in-memory strings: no IPC target other than this process's own worker
pool, no network, no disk access beyond what the caller already set up
via ``iter_wordlist_file_lines`` / ``iter_stdin_candidate_lines``.

Design decisions inferred where PRD v2 section B underspecifies
``--jobs`` mechanics (flagged for confirmation, in the same spirit as
assumptions already noted and approved elsewhere in this codebase):

* PRD v2 section B's own wording is ambiguous ("Default: 1 ... or
  auto-detect CPU count if ``-j 0`` or flag is omitted depending on
  design"). This implementation resolves it as: ``jobs`` omitted -> 1
  (fully sequential, byte-for-byte the same code path and behavior as
  v1); ``jobs=0`` -> auto-detect (``os.cpu_count()``, resolved by
  ``cli.py`` before calling this module); ``jobs=N>0`` -> exactly N
  worker processes. Sequential remains the default specifically so
  nothing about v1's documented behavior changes for anyone who
  doesn't pass ``--jobs`` at all.
* PRD v2 section B allows *either* "deterministic output order" *or*
  "short-circuit exit behavior" as the termination requirement. This
  implementation gets both at once: candidate chunks are hashed in
  parallel across worker processes, but consumed by the parent process
  via ``multiprocessing.pool.Pool.imap`` (the *ordered* variant, not
  ``imap_unordered``), so results are seen in the same order the
  candidates were submitted in -- making ``checked_count`` exactly
  reproducible across runs -- while still terminating every worker
  (via the pool's context-manager ``__exit__``, which calls
  ``terminate()``) the instant the first match is seen.
* Parallel mode reconstructs the algorithm *by name* inside each
  worker (rather than pickling the ``HashAlgorithm`` object itself),
  since worker processes are started fresh under every platform's
  default start method, including ``spawn`` on Windows and macOS. This
  means parallel mode only works with a *registered* algorithm (see
  ``algorithms.register_algorithm``); an ad hoc, unregistered
  ``HashAlgorithm`` implementation only works with ``jobs=1``.
"""

from __future__ import annotations

import functools
import itertools
import multiprocessing
import os
from dataclasses import dataclass
from typing import Iterable, Iterator, TextIO

from .algorithms import HashAlgorithm, get_algorithm
from .validators import validate_and_normalize_digest

_DEFAULT_ALGORITHM: HashAlgorithm = get_algorithm("sha256")
_DEFAULT_CHUNK_SIZE = 2000


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a ``verify`` run (PRD 7).

    ``matched`` corresponds to CLI exit code 0 (a match) versus exit
    code 4 (fully consumed input, no match) from PRD 8.
    ``checked_count`` is the number of candidates hashed and compared,
    including the matching one when ``matched`` is True -- PRD 7: "On
    a match, print the candidate and number of candidates checked."
    This is exact and reproducible across repeated runs in both modes,
    but its *granularity* differs: sequential mode (``jobs=1``) counts
    per candidate, so it is the exact 1-based position of the match.
    Parallel mode (``jobs>1``) counts whole chunks (see
    ``_verify_parallel``'s ``chunk_size``), so ``checked_count`` there
    is the total size of every chunk consumed up to and including the
    one containing the match -- always >= the sequential count for the
    same input, and reproducible run-to-run, but not necessarily equal
    to it.
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
    with open(path, "r", encoding="utf-8") as handle:
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
    jobs: int = 1,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> VerificationResult:
    """Hash and compare each candidate against ``target_digest`` (PRD 7).

    ``target_digest`` is validated and case-normalized first via
    ``validators.validate_and_normalize_digest`` -- PRD 7: "Invalid
    digests fail before the wordlist is read," so this validation
    happens before ``candidates`` is iterated at all (in either mode),
    and ``InvalidDigestError`` propagates to the caller unchanged.

    Each candidate is encoded as UTF-8 explicitly (PRD 7) before
    hashing. Iteration stops at the first match. On a fully consumed
    ``candidates`` with no match, the returned result has
    ``matched=False`` (PRD 7's exit-code-4 case); no complete candidate
    collection is ever materialized -- candidates are consumed one at
    a time (``jobs=1``) or in small, bounded ``chunk_size`` batches
    (``jobs>1``) from the iterator.

    ``jobs`` (PRD v2 section B): ``1`` (the default) runs the original
    single-process v1 code path unchanged. Any value greater than 1
    hashes candidates in parallel across ``jobs`` worker processes; see
    the module docstring for the ordering/short-circuit and
    algorithm-registration implications of that path. ``jobs`` must be
    a positive integer; resolving a user-facing ``--jobs 0``
    ("auto-detect") to a concrete positive count is ``cli.py``'s job,
    not this function's. ``chunk_size`` (only used when ``jobs>1``)
    must also be a positive integer -- a zero or negative value would
    otherwise make every chunk empty, which silently reports
    ``matched=False`` and ``checked_count=0`` without ever hashing a
    single real candidate, rather than failing loudly.
    """
    if jobs <= 0:
        raise ValueError("jobs must be a positive integer")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")

    normalized_digest = validate_and_normalize_digest(
        target_digest, expected_hex_length=algorithm.digest_hex_length
    )

    if jobs == 1:
        return _verify_sequential(candidates, normalized_digest, algorithm)
    return _verify_parallel(
        candidates, normalized_digest, algorithm.name, jobs, chunk_size=chunk_size
    )


def _verify_sequential(
    candidates: Iterable[str],
    normalized_digest: str,
    algorithm: HashAlgorithm,
) -> VerificationResult:
    """The original v1 single-process scan (PRD 7). Unchanged behavior."""
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


def _chunked(candidates: Iterable[str], size: int) -> Iterator[list[str]]:
    """Yield successive lists of up to ``size`` items, pulled lazily.

    Only ever holds one ``size``-length chunk (plus whatever the pool
    reads ahead internally) in memory at a time -- ``candidates`` is
    never materialized as a whole, keeping the same "no complete
    candidate collection" property the sequential path has.
    """
    iterator = iter(candidates)
    while True:
        chunk = list(itertools.islice(iterator, size))
        if not chunk:
            return
        yield chunk


def _hash_chunk_worker(
    algorithm_name: str, normalized_digest: str, chunk: list[str]
) -> tuple[str | None, int]:
    """Hash one chunk of candidates; runs inside a worker process.

    Must stay a plain module-level function taking only plain,
    picklable arguments (two ``str``\\ s and a ``list[str]``): every
    supported multiprocessing start method -- including ``spawn``, the
    default on Windows and macOS -- pickles the callable and its
    arguments to hand off to a fresh worker process, so a closure, a
    bound method, or a non-picklable payload (e.g. a live
    ``HashAlgorithm`` object or an open file handle) would fail there
    even though it might appear to work under Linux's ``fork``.

    Returns the matching candidate (or ``None``) and the chunk's own
    length, so the parent process can maintain an exact running
    ``checked_count`` purely from the chunks it has consumed so far,
    with no separate bookkeeping needed.
    """
    algorithm = get_algorithm(algorithm_name)
    for candidate in chunk:
        if algorithm.hexdigest(candidate.encode("utf-8")) == normalized_digest:
            return candidate, len(chunk)
    return None, len(chunk)


def _verify_parallel(
    candidates: Iterable[str],
    normalized_digest: str,
    algorithm_name: str,
    jobs: int,
    *,
    chunk_size: int,
) -> VerificationResult:
    """The v2 multiprocessing scan (PRD v2 section B).

    See the module docstring for why ``Pool.imap`` (ordered) is used
    instead of ``imap_unordered``, and why the algorithm is looked up
    by name inside each worker. Exiting the ``with`` block -- whether
    via the ``break`` below on a match, or normally once the iterable
    is exhausted -- calls ``Pool.terminate()``, which is how every
    worker process is stopped immediately once a match is found (PRD
    v2 section B: "stopping all worker processes immediately upon
    finding the first matching candidate").
    """
    try:
        get_algorithm(algorithm_name)
    except ValueError as exc:
        raise ValueError(
            f"parallel verification (jobs={jobs}) requires a registered "
            f"algorithm; {exc}. Use jobs=1 for an unregistered/ad hoc "
            f"HashAlgorithm, or register it first with "
            f"hashing.algorithms.register_algorithm()."
        ) from exc

    worker = functools.partial(_hash_chunk_worker, algorithm_name, normalized_digest)

    checked_count = 0
    matched_candidate: str | None = None
    with multiprocessing.Pool(processes=jobs) as pool:
        for match, chunk_length in pool.imap(worker, _chunked(candidates, chunk_size)):
            checked_count += chunk_length
            if match is not None:
                matched_candidate = match
                break

    return VerificationResult(
        matched=matched_candidate is not None,
        matched_candidate=matched_candidate,
        checked_count=checked_count,
    )