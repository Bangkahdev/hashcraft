"""Tests for ``hashcraft.hashing.verifier`` (PRD 7)."""

from __future__ import annotations

import hashlib
import io

import pytest

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
