"""SHA-256 digest validation and normalization (PRD 7).

PRD 7: "A SHA-256 digest must contain exactly 64 hexadecimal
characters. Invalid digests fail before the wordlist is read." Since
comparison against the target digest is explicitly case-insensitive
(PRD 7), this module also normalizes a valid digest to a canonical
lowercase form so callers can compare with simple string equality.
"""

from __future__ import annotations

import re

_HEX_64_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class InvalidDigestError(ValueError):
    """A digest is not exactly 64 hexadecimal characters (PRD 7).

    Maps to CLI exit code 3 (PRD 8: "invalid input (including
    malformed SHA-256 digest or unreadable input)"). Per PRD 7 this
    must be raised *before* any wordlist or stdin input is read --
    callers should validate the digest first and only then start
    iterating candidates.
    """


def validate_and_normalize_digest(raw_digest: str) -> str:
    """Validate ``raw_digest`` as a SHA-256 hex digest and lowercase it.

    Surrounding whitespace is stripped before validation. Raises
    ``InvalidDigestError`` if the stripped value is not exactly 64
    hexadecimal characters (PRD 7); otherwise returns it lowercased,
    ready for direct comparison against a computed
    ``hashlib``-style hex digest (which is always lowercase).
    """
    candidate = raw_digest.strip()
    if not _HEX_64_PATTERN.match(candidate):
        raise InvalidDigestError(
            "a SHA-256 digest must contain exactly 64 hexadecimal characters"
        )
    return candidate.lower()
