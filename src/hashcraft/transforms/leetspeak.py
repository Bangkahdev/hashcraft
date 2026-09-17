"""Bounded leetspeak substitution (PRD 4.3, ``--leet``).

``--leet`` enables the substitutions ``a->@``, ``e->3``, ``i->1``,
``o->0``, ``s->$``, ``t->7``. It generates the unmodified candidate
followed by replacement combinations in deterministic left-to-right
position order, bounded by ``--max-leet-variants`` (default 64): the
generator stops producing further variants for that candidate once the
bound is reached.

Implementation note (assumption, not stated explicitly in PRD 4.3):
matching against the substitution map is case-insensitive (``'A'`` is
treated the same as ``'a'``), since a substitutable character's case
may already have been changed by an upstream case-variant stage.
Characters that are *not* substituted keep their original case; only
the position's original character is replaced, with the fixed
(case-less) symbol from the map. This keeps case variants and
leetspeak variants orthogonal, matching the pipeline order in PRD 4
where case variants run before leetspeak variants. Flag this for
explicit PRD confirmation if a stricter, case-sensitive reading of the
substitution table is intended instead.
"""

from __future__ import annotations

from typing import Iterator, Mapping, Sequence

LEET_MAP: Mapping[str, str] = {
    "a": "@",
    "e": "3",
    "i": "1",
    "o": "0",
    "s": "$",
    "t": "7",
}

DEFAULT_MAX_LEET_VARIANTS = 64


def _substitutable_positions(candidate: str) -> list[int]:
    """Indices (left to right) of characters that have a leet substitute."""
    return [index for index, char in enumerate(candidate) if char.lower() in LEET_MAP]


def _apply_mask(candidate: str, positions: Sequence[int], mask: int) -> str:
    """Render one substitution combination.

    ``positions`` are the substitutable indices, left to right. Bit
    ``i`` of ``mask`` (least-significant first) controls whether
    ``positions[i]`` is substituted. Enumerating masks in increasing
    numeric order therefore varies the leftmost substitutable position
    first, giving the deterministic left-to-right ordering required by
    PRD 4.3.
    """
    chars = list(candidate)
    for bit_index, position in enumerate(positions):
        if mask & (1 << bit_index):
            chars[position] = LEET_MAP[chars[position].lower()]
    return "".join(chars)


def generate_leetspeak_variants(
    candidate: str,
    *,
    max_variants: int = DEFAULT_MAX_LEET_VARIANTS,
) -> Iterator[str]:
    """Yield ``candidate`` unmodified, then bounded leetspeak combinations.

    The unmodified candidate counts toward ``max_variants``, matching
    PRD 4.3's "generates the unmodified candidate followed by
    replacement combinations". Enumeration is fully lazy: even when a
    candidate has many substitutable characters (so the theoretical
    combination count is very large), only as many combinations as are
    actually needed to reach ``max_variants`` are ever computed.
    """
    if max_variants <= 0:
        raise ValueError("max_variants must be a positive integer")

    yield candidate
    emitted = 1
    if emitted >= max_variants:
        return

    positions = _substitutable_positions(candidate)
    substitutable_count = len(positions)
    if substitutable_count == 0:
        return

    # range() over a huge span is O(1) space; iteration still breaks
    # early once max_variants is reached, so this stays cheap even for
    # long candidates with many substitutable characters.
    total_masks = 1 << substitutable_count
    for mask in range(1, total_masks):
        if emitted >= max_variants:
            return
        yield _apply_mask(candidate, positions, mask)
        emitted += 1
