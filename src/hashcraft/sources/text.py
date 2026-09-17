"""UTF-8 token sources and Unicode normalization.

Implements the first stage of the canonical generation pipeline defined
in PRD section 4 ("Canonical generation contract"):

    sources -> normalized tokens -> ordered combinations -> ...

Everything here is an iterator. Nothing in this module materializes the
complete token space with ``list(...)``, a ``set``, or an equivalent
whole-dataset collection, per the pipeline contract in section 4.

Token ordering (PRD 4.1): tokens are read in CLI-option order, then
input-file order, then stdin order. Whitespace surrounding a token is
stripped; empty tokens are discarded. Categories (--names, --cities,
etc.) are metadata only in v0.1 -- they do not alter generation or
ordering, so this module intentionally returns plain strings, not
category-tagged records.
"""

from __future__ import annotations

import os
import unicodedata
from typing import Iterable, Iterator, Literal, Mapping, TextIO

# Fixed CLI-option order per PRD 4.1. This order is normative: it is the
# order in which categories are drained when building the combined token
# stream, regardless of the order flags are given on the command line.
CATEGORY_ORDER: tuple[str, ...] = (
    "names",
    "usernames",
    "pets",
    "cities",
    "vehicles",
    "food",
    "hobbies",
    "organizations",
    "keywords",
    "years",
    "dates",
)

NormalizationMode = Literal["nfc", "none"]


def _split_comma_separated(raw: str) -> Iterator[str]:
    """Split one comma-separated CLI value into stripped, non-empty tokens."""
    for piece in raw.split(","):
        token = piece.strip()
        if token:
            yield token


def iter_cli_tokens(source_values: Mapping[str, str | None]) -> Iterator[str]:
    """Yield tokens from comma-separated CLI source options.

    ``source_values`` maps a category name (e.g. ``"names"``, ``"cities"``)
    to its raw comma-separated CLI value, or ``None``/empty if that option
    was not supplied. Categories are drained in ``CATEGORY_ORDER`` (PRD
    4.1), independent of the mapping's own iteration order or the order
    the flags appeared on the command line.
    """
    for category in CATEGORY_ORDER:
        raw = source_values.get(category)
        if not raw:
            continue
        yield from _split_comma_separated(raw)


def iter_file_tokens(path: str | os.PathLike[str]) -> Iterator[str]:
    """Stream one token per line from an ``--input PATH`` file.

    The file is decoded as UTF-8 (PRD 4.1). Lines are read lazily; the
    file is never read fully into memory as a list of lines.
    """
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            token = line.strip()
            if token:
                yield token


def iter_stdin_tokens(stream: TextIO) -> Iterator[str]:
    """Stream one token per line from a ``--stdin`` text stream.

    ``stream`` is expected to already be a UTF-8 text stream (e.g.
    ``sys.stdin``). Lines are consumed lazily.
    """
    for line in stream:
        token = line.strip()
        if token:
            yield token


def iter_tokens(
    *,
    source_values: Mapping[str, str | None] | None = None,
    input_path: str | os.PathLike[str] | None = None,
    stdin_stream: TextIO | None = None,
) -> Iterator[str]:
    """Combine all configured token sources in the order required by PRD 4.1.

    Order: CLI-option sources, then ``--input`` file, then ``--stdin``.
    Any of the three sources may be omitted (``None`` / not provided).
    This is a thin, lazy composition -- no source is buffered here.
    """
    if source_values:
        yield from iter_cli_tokens(source_values)
    if input_path is not None:
        yield from iter_file_tokens(input_path)
    if stdin_stream is not None:
        yield from iter_stdin_tokens(stdin_stream)


def normalize_tokens(
    tokens: Iterable[str],
    mode: NormalizationMode = "nfc",
) -> Iterator[str]:
    """Apply Unicode normalization, the step right after sourcing (PRD 4.1).

    Per PRD 4.1, the default is NFC, not NFKC: compatibility
    normalization (NFKC) can alter user-intended text and blur
    security-relevant confusables, so it is deliberately not offered as
    an alias here. ``mode="none"`` passes tokens through unchanged for
    explicit opt-out (``--unicode-normalization nfc|none``).

    This must run before any transformation stage (case, leetspeak,
    separators, symbols) and before length filtering, per the pipeline
    contract in PRD 4.1 and 4.4.
    """
    if mode not in ("nfc", "none"):
        raise ValueError(f"Unsupported unicode normalization mode: {mode!r}")

    if mode == "none":
        yield from tokens
        return

    for token in tokens:
        yield unicodedata.normalize("NFC", token)
