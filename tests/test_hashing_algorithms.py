"""Tests for ``hashcraft.hashing.algorithms`` (PRD 7, 10).

Includes the SHA-256 known-answer vectors PRD 10 explicitly requires:
``""``, ``"hello"``, and ``"password123"``. The expected hex digests
below are hardcoded, well-known SHA-256 values (obtained once from
Python's own ``hashlib``, the standard reference implementation) --
not derived from ``hashcraft`` itself -- so these tests catch a
regression in ``Sha256Algorithm``, not just disagreement with a
second call to the same code path.
"""

from __future__ import annotations

import pytest

from hashcraft.hashing.algorithms import Sha256Algorithm, get_algorithm

KNOWN_VECTORS = {
    "": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "hello": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    "password123": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f",
}


@pytest.mark.parametrize("plaintext, expected_digest", list(KNOWN_VECTORS.items()))
def test_sha256_known_answer_vectors(plaintext, expected_digest):
    assert len(expected_digest) == 64
    algorithm = Sha256Algorithm()
    assert algorithm.hexdigest(plaintext.encode("utf-8")) == expected_digest


def test_sha256_algorithm_metadata():
    algorithm = Sha256Algorithm()
    assert algorithm.name == "sha256"
    assert algorithm.digest_hex_length == 64


def test_get_algorithm_returns_sha256():
    algorithm = get_algorithm("sha256")
    assert algorithm.name == "sha256"


def test_get_algorithm_rejects_unsupported_algorithm():
    with pytest.raises(ValueError):
        get_algorithm("md5")
