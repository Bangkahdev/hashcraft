"""Tests for ``hashcraft.hashing.validators`` (PRD 7)."""

from __future__ import annotations

import pytest

from hashcraft.hashing.validators import InvalidDigestError, validate_and_normalize_digest

VALID_DIGEST = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_valid_lowercase_digest_is_accepted_unchanged():
    assert validate_and_normalize_digest(VALID_DIGEST) == VALID_DIGEST


def test_valid_uppercase_digest_is_normalized_to_lowercase():
    assert validate_and_normalize_digest(VALID_DIGEST.upper()) == VALID_DIGEST


def test_valid_mixed_case_digest_is_normalized_to_lowercase():
    mixed = "".join(
        c.upper() if i % 2 == 0 else c for i, c in enumerate(VALID_DIGEST)
    )
    assert validate_and_normalize_digest(mixed) == VALID_DIGEST


def test_surrounding_whitespace_is_stripped_before_validation():
    assert validate_and_normalize_digest(f"  {VALID_DIGEST}\n") == VALID_DIGEST


@pytest.mark.parametrize(
    "bad_digest",
    [
        "",
        "abc",
        VALID_DIGEST[:-1],  # 63 characters
        VALID_DIGEST + "a",  # 65 characters
        "g" * 64,  # non-hex character
        VALID_DIGEST.replace("e", "z", 1),  # one invalid character
        "not a digest at all",
    ],
)
def test_invalid_digests_are_rejected(bad_digest):
    with pytest.raises(InvalidDigestError):
        validate_and_normalize_digest(bad_digest)
