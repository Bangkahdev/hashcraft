"""Pipeline orchestration: the canonical generation contract (PRD 4).

Assembles the normative pipeline from PRD section 4:

    normalized tokens -> ordered combinations -> case variants
        -> leetspeak variants -> separators -> symbol variants
        -> length filter -> structural deduplication -> emit

``sources.text`` produces normalized tokens; this module owns
everything from "ordered combinations" onward. Every stage here is a
generator; per PRD 4, the complete candidate space is never
materialized with ``list(...)``, a ``set``, or an equivalent
whole-dataset collection.

Design decisions inferred where PRD 4 does not fully specify multi-word
behavior (flagged here for confirmation, same as the assumptions
already noted and approved in ``transforms/leetspeak.py`` and
``transforms/symbols.py``):

* Case and leetspeak variants are computed **per token**, before the
  tokens in a sequence are joined by a separator -- matching the
  pipeline order, where these two stages precede "separators". For a
  multi-word sequence (``--max-words`` > 1), each token's variant set
  is computed independently; the sequence's overall variant set is
  their Cartesian product, taken in token order. Symbol variants are
  then computed on the *joined* candidate string, matching "symbol
  variants" coming after "separators" in the pipeline diagram.
* Per-token case/leetspeak variant pools are small and bounded (at
  most 3 case variants, at most ``--max-leet-variants`` leetspeak
  variants per token), so materializing *those* pools -- unlike the
  full candidate space -- is consistent with PRD 4.4's own per-seed
  structural-deduplication set being explicitly "small" and "bounded
  by the per-seed transform caps, not by the total stream."
* "One seed" for structural deduplication (PRD 4.4) is one (ordered
  token sequence, separator) pair: the per-seed insertion-ordered
  dedup set spans every case/leetspeak/symbol variant produced for
  that sequence+separator, and is discarded before the next separator
  (or the next token sequence) begins.

Flag these three points for explicit PRD confirmation before treating
multi-word (``--max-words`` > 1) output as final/normative.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Iterator, Sequence

from .combinations import DEFAULT_SEPARATORS, iter_token_sequences
from ..transforms.case import CaseMode, apply_case_variants
from ..transforms.leetspeak import (
    DEFAULT_MAX_LEET_VARIANTS,
    generate_leetspeak_variants,
)
from ..transforms.symbols import DEFAULT_SYMBOLS, generate_symbol_variants


@dataclass(frozen=True)
class GenerationConfig:
    """Generation-stage options (PRD 4.2-4.4), with PRD-specified defaults.

    NOTE: this is intentionally scoped to generation-stage options
    only (not sources or output). It will likely be folded into the
    broader typed, immutable configuration models described in PRD
    section 9 (``models.py``) once source and output options are
    wired up alongside it; for this step, only the generation modules
    were requested, so it is kept local to ``generator.py``.
    """

    max_words: int = 2
    case_mode: CaseMode = "all"
    leet_enabled: bool = False
    max_leet_variants: int = DEFAULT_MAX_LEET_VARIANTS
    separators: tuple[str, ...] = DEFAULT_SEPARATORS
    symbols_enabled: bool = False
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    max_length: int = 32

    def __post_init__(self) -> None:
        if self.max_words <= 0:
            raise ValueError("max_words must be a positive integer")
        if self.max_leet_variants <= 0:
            raise ValueError("max_leet_variants must be a positive integer")
        if self.max_length <= 0:
            raise ValueError("max_length must be a positive integer")
        if not self.separators:
            raise ValueError("at least one separator must be configured")


def _token_variants(token: str, config: GenerationConfig) -> tuple[str, ...]:
    """Case, then (optionally) leetspeak, variants of a single token.

    Materializing this into a tuple is deliberate and bounded -- at
    most 3 case variants, each expanding to at most
    ``config.max_leet_variants`` leetspeak variants -- see the module
    docstring's second design-decision note.
    """
    variants: list[str] = []
    for case_variant in apply_case_variants(token, config.case_mode):
        if not config.leet_enabled:
            variants.append(case_variant)
            continue
        variants.extend(
            generate_leetspeak_variants(
                case_variant, max_variants=config.max_leet_variants
            )
        )
    return tuple(variants)


def iter_candidates(
    tokens: Sequence[str],
    config: GenerationConfig,
) -> Iterator[str]:
    """Run the full PRD-4 pipeline, from ordered combinations through emit.

    ``tokens`` must already be sourced and normalized (PRD 4.1) --
    this function starts at "ordered combinations". The returned
    iterator yields deduplicated, length-filtered candidates in the
    pipeline's deterministic order; nothing is buffered beyond the
    small, bounded per-token and per-seed pools described in the
    module docstring.

    This same function is used for both the filter-aware preflight
    count (``generation.estimate``, whose caller counts and discards
    this output) and the real generation pass: calling it twice with
    identical ``tokens``/``config`` reproduces the identical
    deterministic stream, per PRD 5 ("Generation then runs the
    identical deterministic pipeline a second time").
    """
    for sequence in iter_token_sequences(tokens, config.max_words):
        per_token_pools = tuple(_token_variants(token, config) for token in sequence)

        for separator in config.separators:
            seen: set[str] = set()  # one structural-dedup seed (PRD 4.4)

            for combo in itertools.product(*per_token_pools):
                joined = separator.join(combo)

                for candidate in generate_symbol_variants(
                    joined, config.symbols, enabled=config.symbols_enabled
                ):
                    # Unicode code points, not UTF-8 bytes (PRD 4.4).
                    # Python's len() on str is already a code-point
                    # count, so no manual counting is needed here.
                    if len(candidate) > config.max_length:
                        continue
                    if candidate in seen:
                        continue
                    seen.add(candidate)
                    yield candidate
