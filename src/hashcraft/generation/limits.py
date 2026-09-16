"""Resource-limit configuration and enforcement (PRD 5).

This module owns the *mechanism* for the two independent hard ceilings
described in PRD 5:

* ``--max-combinations`` -- a preflight ceiling on the filter-aware
  candidate count (enforced via ``generation.estimate``, using
  ``ResourceLimits.max_combinations`` as the ceiling value).
* ``--limit`` -- an independent hard ceiling on candidates *actually
  emitted* (enforced here, via ``enforce_emission_limit``).

Per PRD 9 ("The generator, verifier, sources, and output writer must
be independently callable Python APIs. The CLI is an adapter over
those APIs."), this module raises plain exceptions rather than calling
``sys.exit`` itself; mapping ``PreflightLimitExceeded`` /
``EmissionLimitExceeded`` to CLI exit code 5 (PRD 8) is ``cli.py``'s
job.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

DEFAULT_MAX_COMBINATIONS = 500_000
DEFAULT_LIMIT = 100_000


@dataclass(frozen=True)
class ResourceLimits:
    """The two independent hard ceilings from PRD 5.

    Both default per PRD 5: ``max_combinations`` (preflight ceiling)
    defaults to 500,000; ``limit`` (emission ceiling) defaults to
    100,000. Both must be positive integers.
    """

    max_combinations: int = DEFAULT_MAX_COMBINATIONS
    limit: int = DEFAULT_LIMIT

    def __post_init__(self) -> None:
        if self.max_combinations <= 0:
            raise ValueError("max_combinations must be a positive integer")
        if self.limit <= 0:
            raise ValueError("limit must be a positive integer")


class PreflightLimitExceeded(RuntimeError):
    """The filter-aware preflight count exceeds ``--max-combinations``.

    Raised by ``generation.estimate``, not by this module directly;
    defined here so it lives alongside ``EmissionLimitExceeded`` and
    ``ResourceLimits``. Maps to CLI exit code 5 (PRD 8): "The
    application rejects an estimate above ``--max-combinations`` with
    exit code 5 before emitting output."
    """

    def __init__(self, max_combinations: int):
        super().__init__(
            f"filter-aware candidate estimate exceeds "
            f"--max-combinations={max_combinations}"
        )
        self.max_combinations = max_combinations


class EmissionLimitExceeded(RuntimeError):
    """The number of candidates to emit would exceed ``--limit``.

    Maps to CLI exit code 5 (PRD 8): "If the emitted-candidate limit
    would be exceeded, generation stops with exit code 5."
    """

    def __init__(self, limit: int):
        super().__init__(f"number of candidates to emit exceeds --limit={limit}")
        self.limit = limit


def enforce_emission_limit(
    candidates: Iterable[str],
    limit: int,
) -> Iterator[str]:
    """Wrap a candidate stream, enforcing the ``--limit`` emission ceiling.

    Yields candidates lazily, exactly as they arrive from
    ``candidates``. Up to ``limit`` candidates are yielded normally;
    the moment a ``(limit + 1)``-th candidate would be yielded,
    ``EmissionLimitExceeded`` is raised instead. This matches PRD 5's
    description of the failure mode: a caller streaming yielded
    candidates straight to stdout will already have written the first
    ``limit`` of them by the time the error fires ("Standard output
    may already contain earlier candidates when this error occurs, so
    scripts must treat exit status as authoritative"). For file
    output, the caller is responsible for the atomic
    write-to-temp-then-replace behavior described in PRD 5; this
    function only enforces the count.
    """
    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    emitted = 0
    for candidate in candidates:
        if emitted >= limit:
            raise EmissionLimitExceeded(limit)
        yield candidate
        emitted += 1
