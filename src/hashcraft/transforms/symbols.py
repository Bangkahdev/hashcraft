"""Symbol prefix/suffix transformation (PRD 4.3, ``--symbols``).

Symbols are disabled unless ``--symbols`` is supplied. When enabled,
each configured symbol produces a prefix variant and a suffix variant.
The default symbol list is ``!``, ``@``, ``#``, ``$``, ``_``, ``-``;
``--symbols-list`` replaces it, in the supplied order.

Implementation note (assumption, not fully specified in PRD 4.3): the
PRD does not state whether the plain, undecorated candidate should
still be emitted once ``--symbols`` is enabled, or whether it is
entirely replaced by symbol-decorated variants. This module preserves
the undecorated candidate alongside the prefix/suffix variants, for
consistency with the leetspeak stage's explicit "unmodified candidate
followed by variants" contract (PRD 4.3). Flag this for explicit PRD
confirmation before relying on it.
"""

from __future__ import annotations

from typing import Iterator, Sequence

DEFAULT_SYMBOLS: tuple[str, ...] = ("!", "@", "#", "$", "_", "-")


def generate_symbol_variants(
    candidate: str,
    symbols: Sequence[str] = DEFAULT_SYMBOLS,
    *,
    enabled: bool,
) -> Iterator[str]:
    """Yield ``candidate`` plus a prefix and suffix variant per symbol.

    When ``enabled`` is ``False`` (the default posture, per PRD 4.3:
    "Symbols are disabled unless ``--symbols`` is supplied"), this is
    an identity pass-through and yields only ``candidate``. When
    enabled, symbols are applied in the supplied order; for each
    symbol, the prefix variant (``symbol + candidate``) is yielded
    before the suffix variant (``candidate + symbol``).
    """
    if not enabled or not symbols:
        yield candidate
        return

    yield candidate
    for symbol in symbols:
        yield f"{symbol}{candidate}"
        yield f"{candidate}{symbol}"
