"""Text output destinations: atomic file writing and the clean ``--stdout``
contract (PRD 5, 6).

For file output, PRD 5 requires: "write to a sibling temporary file
and atomically replace the destination only after successful
completion; discard the temporary file on failure." This module
implements exactly that -- the temporary file lives next to the
destination (same directory, so the final replace is a same-filesystem
rename on Linux, Windows, and macOS) and is removed if anything goes
wrong before completion, including an emission-limit error raised
mid-stream by ``generation.limits.enforce_emission_limit``.

For standard output, PRD 6 requires that ``generate --stdout`` emit
"one candidate followed by ``\\n`` per line and nothing else on
standard output: no banner, preflight report, warning, progress, or
color-control sequence." This module's stdout writer enforces exactly
that -- it writes candidates and nothing else. Status, warnings,
preflight reports, progress, and errors belong on stderr (PRD 6) and
are deliberately out of scope here; ``cli.py`` owns that stream.
"""

from __future__ import annotations

import os
import tempfile
from typing import Iterable, TextIO


class DestinationExistsError(FileExistsError):
    """The output file already exists and ``--overwrite`` was not given.

    PRD 5: "``--overwrite`` alone authorizes replacement of an
    existing output file. It is deliberately distinct from ``--yes``."
    ``cli.py`` maps this to exit code 2 (invalid command-line
    arguments): the command was invoked without the flag required to
    replace this destination.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        super().__init__(
            f"output file already exists and --overwrite was not given: {path}"
        )
        self.path = path


def write_candidates_to_file(
    candidates: Iterable[str],
    destination: str | os.PathLike[str],
    *,
    overwrite: bool = False,
) -> int:
    """Write ``candidates`` to ``destination``, one per line, atomically.

    Implements PRD 5's atomic-write contract: a sibling temporary file
    (same directory as ``destination``) receives every candidate as it
    is produced; only once the *entire* stream is consumed without
    error is the temporary file atomically moved onto ``destination``
    via ``os.replace``. If ``candidates`` raises partway through --
    including ``generation.limits.EmissionLimitExceeded`` when
    ``--limit`` is exceeded -- the temporary file is deleted and the
    exception re-raised unchanged, so no partial or corrupt file is
    ever left in ``destination``'s place.

    Raises ``DestinationExistsError`` before writing anything if
    ``destination`` already exists and ``overwrite`` is False (PRD 5).
    Lines are written with an explicit ``"\\n"`` terminator and
    ``newline="\\n"`` is passed to the underlying file so no platform
    translates it to ``"\\r\\n"`` -- output must be byte-identical
    across platforms per PRD 4's canonical-generation contract.
    Returns the number of candidates written.
    """
    destination_str = os.fspath(destination)
    if not overwrite and os.path.exists(destination_str):
        raise DestinationExistsError(destination_str)

    directory = os.path.dirname(destination_str) or "."
    fd, temp_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(destination_str)}.",
        suffix=".tmp",
        dir=directory,
    )
    count = 0
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for candidate in candidates:
                handle.write(candidate)
                handle.write("\n")
                count += 1
        os.replace(temp_path, destination_str)
        return count
    except BaseException:
        _discard_temp_file(temp_path)
        raise


def _discard_temp_file(temp_path: str) -> None:
    """Best-effort removal of the sibling temp file after a failed write."""
    try:
        os.remove(temp_path)
    except OSError:
        pass


def write_candidates_to_stdout(candidates: Iterable[str], stream: TextIO) -> int:
    """Write ``candidates`` to ``stream``, one per line, nothing else.

    Implements the ``--stdout`` contract in PRD 6: exactly "one
    candidate followed by ``\\n`` per line and nothing else on standard
    output." Returns the number of candidates written. If
    ``candidates`` raises partway through (e.g. an emission-limit
    error), whatever has already been written to ``stream`` stays
    there -- PRD 5: "Standard output may already contain earlier
    candidates when this error occurs, so scripts must treat exit
    status as authoritative" -- and the exception propagates unchanged;
    there is nothing to undo on a stream that cannot be rewound.
    """
    count = 0
    for candidate in candidates:
        stream.write(candidate)
        stream.write("\n")
        count += 1
    return count
