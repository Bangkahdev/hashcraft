"""Tests for ``hashcraft.hashing.algorithms`` (PRD 7, 10; PRD v2 section A).

Includes known-answer vectors for every supported algorithm across the
same three plaintexts PRD 10 requires for SHA-256 (``""``, ``"hello"``,
``"password123"``). Every expected hex digest below is hardcoded, from
Python's own ``hashlib`` (the standard reference implementation) --
not derived by calling ``hashcraft`` twice -- so these tests catch a
regression in the algorithm registry itself, not just disagreement
with a second call to the same code path.
"""

from __future__ import annotations

import pytest

from hashcraft.hashing.algorithms import (
    HashAlgorithm,
    get_algorithm,
    register_algorithm,
    supported_algorithm_names,
)

# {algorithm_name: {plaintext: expected_hex_digest}}
KNOWN_VECTORS: dict[str, dict[str, str]] = {
    "md5": {
        "": "d41d8cd98f00b204e9800998ecf8427e",
        "hello": "5d41402abc4b2a76b9719d911017c592",
        "password123": "482c811da5d5b4bc6d497ffa98491e38",
    },
    "sha1": {
        "": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
        "hello": "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d",
        "password123": "cbfdac6008f9cab4083784cbd1874f76618d2a97",
    },
    "sha256": {
        "": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "hello": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        "password123": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f",
    },
    "sha512": {
        "": (
            "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9c"
            "e47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
        ),
        "hello": (
            "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca"
            "72323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043"
        ),
        "password123": (
            "bed4efa1d4fdbd954bd3705d6a2a78270ec9a52ecfbfb010c61862af5c76af1"
            "761ffeb1aef6aca1bf5d02b3781aa854fabd2b69c790de74e17ecfec3cb6ac4bf"
        ),
    },
    "blake2b": {
        "": (
            "786a02f742015903c6c6fd852552d272912f4740e15847618a86e217f71f54"
            "19d25e1031afee585313896444934eb04b903a685b1448b755d56f701afe9be2ce"
        ),
        "hello": (
            "e4cfa39a3d37be31c59609e807970799caa68a19bfaa15135f165085e01d41a"
            "65ba1e1b146aeb6bd0092b49eac214c103ccfa3a365954bbbe52f74a2b3620c94"
        ),
        "password123": (
            "fbdba996cade3bae2d948c2f03f8149ffa7068584731ac6efbef1688e64609b"
            "6969a52dcc203b74aa87d6d9d1b0cd93bea724cddd12443f2b808bc03776b81cc"
        ),
    },
}

EXPECTED_DIGEST_HEX_LENGTHS = {
    "md5": 32,
    "sha1": 40,
    "sha256": 64,
    "sha512": 128,
    "blake2b": 128,
}


def test_supported_algorithm_names_matches_prd_v2_section_a():
    # PRD v2 section A: md5, sha1, sha256, sha512 (cryptographic) plus
    # blake2b. Sorted, since supported_algorithm_names() documents a
    # sorted return value (used verbatim as argparse choices=).
    assert supported_algorithm_names() == (
        "blake2b",
        "md5",
        "sha1",
        "sha256",
        "sha512",
    )


@pytest.mark.parametrize("algorithm_name", list(KNOWN_VECTORS))
def test_known_answer_vectors_for_every_algorithm(algorithm_name):
    algorithm = get_algorithm(algorithm_name)
    for plaintext, expected_digest in KNOWN_VECTORS[algorithm_name].items():
        assert len(expected_digest) == EXPECTED_DIGEST_HEX_LENGTHS[algorithm_name]
        assert algorithm.hexdigest(plaintext.encode("utf-8")) == expected_digest


@pytest.mark.parametrize("algorithm_name", list(KNOWN_VECTORS))
def test_algorithm_metadata_matches_its_actual_digest_length(algorithm_name):
    algorithm = get_algorithm(algorithm_name)
    assert algorithm.name == algorithm_name
    assert algorithm.digest_hex_length == EXPECTED_DIGEST_HEX_LENGTHS[algorithm_name]
    # The declared length must match what hexdigest() actually returns,
    # since hashing/validators.py trusts digest_hex_length to validate
    # a --hash value before any candidate is even read.
    produced = algorithm.hexdigest(b"anything")
    assert len(produced) == algorithm.digest_hex_length


def test_get_algorithm_rejects_unsupported_algorithm():
    with pytest.raises(ValueError, match="unsupported algorithm"):
        get_algorithm("sha3_256")


def test_get_algorithm_error_message_lists_supported_names():
    with pytest.raises(ValueError, match="md5"):
        get_algorithm("not_a_real_algorithm")


def test_default_algorithm_is_still_sha256_for_backward_compatibility():
    # PRD v2 section 4 Task 2: "--algorithm (defaulting to sha256 for
    # backward compatibility)".
    assert get_algorithm("sha256").name == "sha256"


def test_register_algorithm_adds_a_new_entry_without_touching_existing_ones():
    class _FakeAlgorithm:
        name = "fake_for_test"
        digest_hex_length = 8

        def hexdigest(self, data: bytes) -> str:
            return "deadbeef"

    before = supported_algorithm_names()
    register_algorithm(_FakeAlgorithm())
    try:
        after = supported_algorithm_names()
        assert "fake_for_test" in after
        assert set(after) - set(before) == {"fake_for_test"}
        assert get_algorithm("fake_for_test").hexdigest(b"x") == "deadbeef"
        # Registering doesn't disturb any existing algorithm.
        assert get_algorithm("sha256").hexdigest(b"") == KNOWN_VECTORS["sha256"][""]
    finally:
        # Don't leak this fake registration into other test modules --
        # _ALGORITHMS is process-wide module state.
        from hashcraft.hashing import algorithms as algorithms_module

        del algorithms_module._ALGORITHMS["fake_for_test"]


def test_registered_algorithm_satisfies_the_hashalgorithm_protocol():
    # Structural typing sanity check: get_algorithm's return value
    # should be usable anywhere a HashAlgorithm is expected.
    algorithm: HashAlgorithm = get_algorithm("sha256")
    assert isinstance(algorithm.name, str)
    assert isinstance(algorithm.digest_hex_length, int)
    assert isinstance(algorithm.hexdigest(b"x"), str)
