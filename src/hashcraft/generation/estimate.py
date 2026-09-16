"""Preflight, filter-aware candidate counting (PRD 5).

Implements the two estimates PRD 5 calls for:

* A **filter-aware count**: the preflight runs the identical streaming
  pipeline used for real generation (``generation.generator.iter_candidates``),
  with its output simply counted and discarded, up to
  ``max_combinations + 1``. This is the *only* number PRD 5 permits to
  drive the hard ``--max-combinations`` decision: "This gives the
  exact number of candidates that v0.1 would emit (or proves it
  exceeds the ceiling)." It never materializes or retains the complete
  candidate collection -- only a running integer count is kept (PRD 5:
  "It retains no complete candidate collection").
* A **cheap raw upper bound**: a closed-form, deliberately loose
  estimate computed *without* running the pipeline at all, for
  ``--dry-run`` display only. PRD 5 is explicit that this number must
  never gate the hard decision: "Dry-run reports both a cheap raw
  upper bound and the filter-aware count; only the latter is used for
  the hard preflight decision."

Two-pass design (PRD 5): callers first pass a fresh
``iter_candidates(tokens, config)`` stream through ``filter_aware_count``
(or the ``run_filter_aware_preflight`` convenience wrapper below) with
output disabled; only once that count clears ``max_combinations`` does
the caller build a second, independent ``iter_candidates(tokens, config)``
stream for the real, output-producing pass. Because ``iter_candidates``
is a pure function of ``tokens`` and ``config`` with no shared mutable
state between calls, the two passes are guaranteed to reproduce the
identical deterministic sequence (PRD 5: "Generation then runs the
identical deterministic pipeline a second time").
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from .generator import GenerationConfig, iter_candidates


@dataclass(frozen=True)
class PreflightResult:
    """Outcome of the filter-aware preflight count (PRD 5).

    ``count`` is the exact number of candidates counted, capped at
    ``max_combinations + 1`` -- it is not necessarily the *true* total
    when ``exceeds_ceiling`` is True, since counting deliberately stops
    early once the ceiling is provably exceeded.
    """

    count: int
    max_combinations: int

    @property
    def exceeds_ceiling(self) -> bool:
        """True precisely when the exact filter-aware output size is
        more than ``max_combinations`` (PRD 5's hard-limit condition).
        """
        return self.count > self.max_combinations


def filter_aware_count(
    candidates: Iterable[str],
    max_combinations: int,
) -> PreflightResult:
    """Count an already-assembled pipeline stream, stopping early at the ceiling.

    ``candidates`` must come from the same pipeline used for real
    generation (normalization, ordered combinations, case/leetspeak,
    separators, symbols, length filter, and per-seed structural dedup
    already applied) -- typically ``generator.iter_candidates(tokens, config)``
    called with output disabled. Counting stops as soon as
    ``max_combinations + 1`` is reached, so this stays cheap even when
    the true total would be enormous.
    """
    if max_combinations <= 0:
        raise ValueError("max_combinations must be a positive integer")

    ceiling_plus_one = max_combinations + 1
    count = 0
    for _ in candidates:
        count += 1
        if count >= ceiling_plus_one:
            break
    return PreflightResult(count=count, max_combinations=max_combinations)


def run_filter_aware_preflight(
    tokens: Sequence[str],
    config: GenerationConfig,
    max_combinations: int,
) -> PreflightResult:
    """Convenience wrapper: build a fresh pipeline stream, then count it.

    Building a brand-new ``iter_candidates`` generator here (rather
    than accepting a pre-built one) guarantees this preflight pass
    cannot accidentally share or exhaust state with a later real
    generation pass -- each call to ``iter_candidates(tokens, config)``
    is independent, so running it once here for counting and again
    later for real emission reproduces the identical deterministic
    sequence, per PRD 5's two-pass design.
    """
    return filter_aware_count(iter_candidates(tokens, config), max_combinations)


def raw_upper_bound(token_count: int, config: GenerationConfig) -> int:
    """Cheap, closed-form, deliberately loose Cartesian-product estimate (PRD 5).

    This intentionally over-counts: it ignores the final-length filter
    and the per-seed structural deduplication that ``filter_aware_count``
    applies, and assumes every token hits the worst-case transform
    multiplier (e.g. every character in every token is leet-substitutable)
    rather than each token's actual substitutable-character count. It is
    used only for the informational ``--dry-run`` display -- per PRD 5,
    never for the hard preflight decision -- so this looseness is by
    design: it exists precisely to avoid "false rejection from an
    intentionally oversized Cartesian-product estimate."

    Computed as: for each sequence length ``r`` from 1 to
    ``min(max_words, token_count)``, the number of ordered permutations
    of length ``r`` (``nPr``), times the worst-case per-token
    case/leetspeak transform multiplier raised to the ``r``-th power,
    summed over all lengths, then scaled by the number of configured
    separators and the worst-case symbol-variant multiplier.
    """
    if token_count <= 0:
        return 0

    depth = min(config.max_words, token_count)

    case_multiplier = 3 if config.case_mode == "all" else 1
    leet_multiplier = config.max_leet_variants if config.leet_enabled else 1
    per_token_multiplier = case_multiplier * leet_multiplier

    separator_multiplier = len(config.separators)
    symbol_multiplier = 1 + 2 * len(config.symbols) if config.symbols_enabled else 1

    total = 0
    for length in range(1, depth + 1):
        total += math.perm(token_count, length) * (per_token_multiplier**length)

    return total * separator_multiplier * symbol_multiplier
