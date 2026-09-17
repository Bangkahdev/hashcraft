"""Tests for ``hashcraft.hashing.verifier`` (PRD 7)."""

from __future__ import annotations

import hashlib
import io

import pytest

from hashcraft.hashing.algorithms import get_algorithm
from hashcraft.hashing.validators import InvalidDigestError
from hashcraft.hashing.verifier import (
    iter_stdin_candidate_lines,
    iter_wordlist_file_lines,
    verify,
)

PASSWORD123_DIGEST = "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"


def test_verify_matches_and_reports_correct_checked_count():
    candidates = ["wrong1", "wrong2", "password123", "wrong3"]
    result = verify(candidates, PASSWORD123_DIGEST)
    assert result.matched is True
    assert result.matched_candidate == "password123"
    assert result.checked_count == 3  # stopped at the match


def test_verify_no_match_after_full_consumption():
    result = verify(["a", "b", "c"], PASSWORD123_DIGEST)
    assert result.matched is False
    assert result.matched_candidate is None
    assert result.checked_count == 3


def test_verify_rejects_invalid_digest_before_touching_candidates():
    class ExplodingIterable:
        def __iter__(self):
            raise AssertionError("candidates must not be iterated for an invalid digest")

    with pytest.raises(InvalidDigestError):
        verify(ExplodingIterable(), "not-a-valid-digest")


def test_verify_encodes_candidates_as_utf8_explicitly():
    candidate = "pässwörd"
    target = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    result = verify(["wrong", candidate], target)
    assert result.matched is True
    assert result.matched_candidate == candidate


def test_verify_digest_comparison_is_case_insensitive():
    result = verify(["password123"], PASSWORD123_DIGEST.upper())
    assert result.matched is True


def test_wordlist_file_reader_preserves_exact_content_only_strips_newline(tmp_path):
    path = tmp_path / "wordlist.txt"
    path.write_text("  spaced  \npassword123\ncafé\n", encoding="utf-8")
    lines = list(iter_wordlist_file_lines(path))
    assert lines == ["  spaced  ", "password123", "café"]


def test_stdin_candidate_reader_preserves_exact_content_only_strips_newline():
    stream = io.StringIO("  spaced  \npassword123\n")
    lines = list(iter_stdin_candidate_lines(stream))
    assert lines == ["  spaced  ", "password123"]


def test_generate_stdout_style_pipeline_round_trips_through_stdin_reader():
    # Simulates `generate --stdout | verify --stdin` (PRD 6/7): a clean
    # one-candidate-per-line stream must round-trip to an exact match.
    generated_stdout = "wrong1\nwrong2\npassword123\n"
    stream = io.StringIO(generated_stdout)
    result = verify(iter_stdin_candidate_lines(stream), PASSWORD123_DIGEST)
    assert result.matched is True
    assert result.matched_candidate == "password123"
    assert result.checked_count == 3


# --------------------------------------------------------------------------
# PRD v2 section A: multi-algorithm verification
# --------------------------------------------------------------------------


def test_verify_with_a_non_default_algorithm():
    target = hashlib.md5(b"password123").hexdigest()
    result = verify(
        ["wrong1", "password123", "wrong2"],
        target,
        algorithm=get_algorithm("md5"),
    )
    assert result.matched is True
    assert result.matched_candidate == "password123"
    assert result.checked_count == 2


@pytest.mark.parametrize("algorithm_name", ["md5", "sha1", "sha256", "sha512", "blake2b"])
def test_verify_matches_for_every_supported_algorithm(algorithm_name):
    algorithm = get_algorithm(algorithm_name)
    target = algorithm.hexdigest(b"password123")
    result = verify(["nope", "password123"], target, algorithm=algorithm)
    assert result.matched is True
    assert result.matched_candidate == "password123"


def test_verify_rejects_a_digest_of_the_wrong_length_for_the_selected_algorithm():
    # A valid SHA-256 digest is the wrong length for md5 (32 expected).
    sha256_shaped_digest = PASSWORD123_DIGEST
    with pytest.raises(InvalidDigestError, match="32"):
        verify(["password123"], sha256_shaped_digest, algorithm=get_algorithm("md5"))


# --------------------------------------------------------------------------
# PRD v2 section B: multiprocessing (--jobs)
# --------------------------------------------------------------------------


def test_verify_parallel_finds_a_match():
    candidates = [f"nope{i}" for i in range(40)]
    candidates[23] = "password123"
    result = verify(candidates, PASSWORD123_DIGEST, jobs=3, chunk_size=5)
    assert result.matched is True
    assert result.matched_candidate == "password123"


def test_verify_parallel_no_match_after_full_consumption():
    candidates = [f"nope{i}" for i in range(17)]
    result = verify(candidates, PASSWORD123_DIGEST, jobs=2, chunk_size=4)
    assert result.matched is False
    assert result.matched_candidate is None
    assert result.checked_count == 17


def test_verify_parallel_checked_count_is_exact_and_deterministic():
    # 50 candidates, chunk_size=5 -> 10 chunks of 5. Planting the match
    # in the 6th chunk (indices 25-29) means a correct, deterministic
    # implementation always reports exactly 30 checked (6 chunks * 5),
    # regardless of which worker happened to process which chunk.
    candidates = [f"nope{i}" for i in range(50)]
    candidates[27] = "password123"

    seen_counts = {
        verify(candidates, PASSWORD123_DIGEST, jobs=4, chunk_size=5).checked_count
        for _ in range(5)
    }
    assert seen_counts == {30}


def test_verify_parallel_stops_early_short_circuit():
    # A match near the front of a much larger candidate list should
    # only require a small fraction of it to be checked -- proving the
    # worker pool is actually terminated on match (PRD v2 section B),
    # not silently left to hash the rest in the background.
    candidates = [f"nope{i}" for i in range(20_000)]
    candidates[10] = "password123"
    result = verify(candidates, PASSWORD123_DIGEST, jobs=2, chunk_size=100)
    assert result.matched is True
    assert result.checked_count <= 200  # a couple of chunks at most


def test_verify_parallel_matches_sequential_result_for_the_same_input():
    candidates = [f"nope{i}" for i in range(30)]
    candidates[12] = "password123"
    sequential = verify(candidates, PASSWORD123_DIGEST, jobs=1)
    parallel = verify(candidates, PASSWORD123_DIGEST, jobs=3, chunk_size=4)
    assert sequential.matched == parallel.matched
    assert sequential.matched_candidate == parallel.matched_candidate
    # checked_count is chunk-granular in parallel mode (see
    # VerificationResult's docstring): it can only be >= the exact,
    # per-candidate sequential count, rounded up to a whole number of
    # chunks -- here, the match at index 12 falls in the 4th chunk of
    # 4 (indices 12-15), so parallel reports 16 checked vs sequential's
    # exact 13.
    assert sequential.checked_count == 13
    assert parallel.checked_count == 16
    assert parallel.checked_count >= sequential.checked_count
    assert parallel.checked_count % 4 == 0


def test_verify_jobs_must_be_positive():
    with pytest.raises(ValueError, match="positive"):
        verify(["a"], PASSWORD123_DIGEST, jobs=0)
    with pytest.raises(ValueError, match="positive"):
        verify(["a"], PASSWORD123_DIGEST, jobs=-1)


def test_verify_chunk_size_must_be_positive():
    # Regression test: chunk_size<=0 must fail loudly, not silently
    # produce every chunk as empty (which would report matched=False /
    # checked_count=0 even when a real match exists in the input).
    candidates = ["nope1", "password123", "nope2"]
    for bad_chunk_size in (0, -1, -5):
        with pytest.raises(ValueError, match="chunk_size"):
            verify(candidates, PASSWORD123_DIGEST, jobs=2, chunk_size=bad_chunk_size)


def test_verify_parallel_with_unregistered_algorithm_raises_a_clear_error():
    class _UnregisteredAlgorithm:
        name = "totally_unregistered_for_test"
        digest_hex_length = 8

        def hexdigest(self, data: bytes) -> str:
            return "deadbeef"

    # jobs=1 (sequential) works fine with an ad hoc, unregistered algorithm...
    result = verify(["x"], "deadbeef", algorithm=_UnregisteredAlgorithm(), jobs=1)
    assert result.matched is True

    # ...but jobs>1 needs to reconstruct it by name inside worker
    # processes, so an unregistered algorithm must fail fast and
    # clearly, not with an opaque error from inside a worker.
    with pytest.raises(ValueError, match="registered"):
        verify(["x"], "deadbeef", algorithm=_UnregisteredAlgorithm(), jobs=2)


def test_verify_parallel_invalid_digest_still_fails_before_reading_candidates():
    class ExplodingIterable:
        def __iter__(self):
            raise AssertionError("candidates must not be iterated for an invalid digest")

    with pytest.raises(InvalidDigestError):
        verify(ExplodingIterable(), "not-a-valid-digest", jobs=4)