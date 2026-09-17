"""Digest validation and normalization (PRD 7; generalized in v2).

PRD 7 (v1): "A SHA-256 digest must contain exactly 64 hexadecimal
characters. Invalid digests fail before the wordlist is read." PRD v2
section A adds algorithms with other digest lengths (``md5`` = 32 hex
characters, ``sha1`` = 40, ``sha512`` / ``blake2b`` = 128), so the
length check here is now parametrized by the selected algorithm's
``digest_hex_length`` instead of a hardcoded 64 -- the *rule* ("exactly
N hexadecimal characters, checked before any candidate input is read")
is unchanged from v1, only which N applies.

Since comparison against the target digest is explicitly
case-insensitive (PRD 7), this module also normalizes a valid digest
to a canonical lowercase form so callers can compare with simple
string equality.
"""

from __future__ import annotations

import re

_HEX_PATTERN = re.compile(r"^[0-9a-fA-F]+$")


class InvalidDigestError(ValueError):
    """A digest is not exactly the expected number of hex characters.

    Maps to CLI exit code 3 (PRD 8: "invalid input (including
    malformed SHA-256 digest or unreadable input)"). Per PRD 7 this
    must be raised *before* any wordlist or stdin input is read --
    callers should validate the digest first and only then start
    iterating candidates.
    """


def validate_and_normalize_digest(raw_digest: str, *, expected_hex_length: int = 64) -> str:
    """Validate ``raw_digest`` as a hex digest and lowercase it.

    ``expected_hex_length`` is the selected algorithm's
    ``HashAlgorithm.digest_hex_length`` (default 64, SHA-256's length,
    preserved for backward compatibility with v1 callers that don't
    pass it explicitly). Surrounding whitespace is stripped before
    validation. Raises ``InvalidDigestError`` if the stripped value is
    not exactly ``expected_hex_length`` hexadecimal characters;
    otherwise returns it lowercased, ready for direct comparison
    against a computed ``hashlib``-style hex digest (which is always
    lowercase).
    """
    candidate = raw_digest.strip()
    if len(candidate) != expected_hex_length or not _HEX_PATTERN.match(candidate):
        raise InvalidDigestError(
            f"a digest must contain exactly {expected_hex_length} "
            "hexadecimal characters"
        )
    return candidate.lower()
