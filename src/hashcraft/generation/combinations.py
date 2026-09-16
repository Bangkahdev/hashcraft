"""Ordered token combinations and separator joining (PRD 4.2).

For ``n`` normalized tokens and ``--max-words D``, PRD 4.2 requires:
"emit every ordered permutation without token reuse for lengths 1
through ``min(D, n)``." "Without token reuse" is per-occurrence, not
per-value: two separate token occurrences that happen to share a
string value (e.g. the token ``"atha"`` supplied twice, from two
different sources) may still appear together in one combination -- the
PRD's own example implies this ("``atha_atha`` is not generated *from
a single occurrence* of ``atha``", i.e. it *would* be generated from
two occurrences). ``itertools.permutations`` already implements
exactly this: it selects by input position, not by value, so
duplicate-valued tokens at different positions combine correctly
without any special-casing here.

Every ordered token sequence subsequently receives each configured
separator between all adjacent words (an empty separator is valid).
That joining step is provided here too, since PRD 4.2 describes it as
part of the combinations stage. *Where* it fires relative to the case
and leetspeak stages is decided by ``generation/generator.py``'s
pipeline orchestration -- see that module's docstring for the
reasoning.
"""

from __future__ import annotations

import itertools
from typing import Iterator, Sequence

# Default separators (PRD 4.3): "", "_", ".", "-", in this order.
DEFAULT_SEPARATORS: tuple[str, ...] = ("", "_", ".", "-")


def iter_token_sequences(
    tokens: Sequence[str],
    max_words: int,
) -> Iterator[tuple[str, ...]]:
    """Yield every ordered permutation of ``tokens``, lengths 1..min(max_words, n).

    ``tokens`` is the small, finite, user-supplied keyword list
    (already sourced and normalized per PRD 4.1). Requiring it as a
    ``Sequence`` (indexable, has a length) is unavoidable for computing
    permutations and is unrelated to the "no complete candidate space"
    prohibition in PRD 4, which targets the potentially enormous
    combinatorial *output*, not this bounded input. ``itertools.permutations``
    is itself lazy per length: it does not precompute or buffer the
    full output for a given length before the first value is yielded.
    """
    if max_words <= 0:
        raise ValueError("max_words must be a positive integer")

    token_count = len(tokens)
    depth = min(max_words, token_count)
    for length in range(1, depth + 1):
        yield from itertools.permutations(tokens, length)


def iter_separated_candidates(
    sequence: Sequence[str],
    separators: Sequence[str] = DEFAULT_SEPARATORS,
) -> Iterator[str]:
    """Join one already-transformed token sequence with each separator.

    Per PRD 4.2: "Each ordered token sequence subsequently receives
    each configured separator between all adjacent words; an empty
    separator is valid." Separators are yielded in the supplied order,
    matching ``--separators``' documented replacement-list ordering
    (PRD 4.3).
    """
    if not separators:
        raise ValueError("at least one separator must be configured")

    for separator in separators:
        yield separator.join(sequence)
