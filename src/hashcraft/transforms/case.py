"""Case-variant transformation (PRD 4.3, ``--case``).

``--case`` accepts ``lower``, ``upper``, ``capitalize``, or ``all``
(default ``all``). ``all`` emits exactly the ``lower, upper,
capitalize`` sequence after removing variants that are identical
within the same input candidate -- e.g. a purely numeric or symbol
string like ``"123"`` collapses to a single emitted variant because
``lower() == upper() == capitalize()`` for it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Literal

CaseMode = Literal["lower", "upper", "capitalize", "all"]

# Canonical emission order for --case all (PRD 4.3).
_ALL_ORDER: tuple[CaseMode, ...] = ("lower", "upper", "capitalize")


def _render(candidate: str, mode: CaseMode) -> str:
    if mode == "lower":
        return candidate.lower()
    if mode == "upper":
        return candidate.upper()
    return candidate.capitalize()


def apply_case_variants(candidate: str, mode: CaseMode) -> Iterator[str]:
    """Yield the case variant(s) of ``candidate`` required by ``mode``.

    For ``mode="all"``, variants are yielded in ``lower, upper,
    capitalize`` order, with any variant identical to an earlier one
    (for this same ``candidate``) skipped -- an insertion-ordered
    dedupe scoped to this single call, matching PRD 4.3's "removing
    variants that are identical within the same input candidate".
    """
    if mode not in ("lower", "upper", "capitalize", "all"):
        raise ValueError(f"Unsupported case mode: {mode!r}")

    if mode != "all":
        yield _render(candidate, mode)
        return

    seen: set[str] = set()
    for sub_mode in _ALL_ORDER:
        variant = _render(candidate, sub_mode)
        if variant in seen:
            continue
        seen.add(variant)
        yield variant
