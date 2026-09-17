"""Tests for ``hashcraft.generation.combinations`` (PRD 4.2)."""

from __future__ import annotations

import pytest

from hashcraft.generation.combinations import (
    DEFAULT_SEPARATORS,
    iter_separated_candidates,
    iter_token_sequences,
)


def test_default_separators_match_prd():
    assert DEFAULT_SEPARATORS == ("", "_", ".", "-")


def test_single_token_depth_one():
    assert list(iter_token_sequences(("atha",), 1)) == [("atha",)]


def test_two_tokens_depth_two_matches_prd_example_order():
    # PRD 6's own example distinguishes atha_bangkah from bangkah_atha.
    sequences = list(iter_token_sequences(("atha", "bangkah"), 2))
    assert sequences == [
        ("atha",),
        ("bangkah",),
        ("atha", "bangkah"),
        ("bangkah", "atha"),
    ]


def test_depth_capped_at_min_max_words_and_token_count():
    # max_words=5 but only 2 tokens available -> depth stays at 2.
    sequences = list(iter_token_sequences(("a", "b"), 5))
    lengths = {len(seq) for seq in sequences}
    assert lengths == {1, 2}


def test_duplicate_valued_tokens_at_different_positions_combine():
    # PRD 4.2: "atha_atha is not generated from a single occurrence of
    # atha" implies it IS generated from two occurrences.
    sequences = list(iter_token_sequences(("atha", "atha"), 2))
    assert ("atha", "atha") in sequences
    # Two length-1 occurrences (by position), both value "atha".
    length_one = [seq for seq in sequences if len(seq) == 1]
    assert length_one == [("atha",), ("atha",)]


def test_max_words_must_be_positive():
    with pytest.raises(ValueError):
        list(iter_token_sequences(("a",), 0))
    with pytest.raises(ValueError):
        list(iter_token_sequences(("a",), -1))


def test_empty_token_list_yields_nothing():
    assert list(iter_token_sequences((), 3)) == []


def test_separated_candidates_join_in_supplied_separator_order():
    result = list(iter_separated_candidates(("atha", "bangkah"), ("_", ".", "")))
    assert result == ["atha_bangkah", "atha.bangkah", "athabangkah"]


def test_separated_candidates_empty_separator_is_valid():
    assert list(iter_separated_candidates(("atha",), ("",))) == ["atha"]


def test_separated_candidates_requires_at_least_one_separator():
    with pytest.raises(ValueError):
        list(iter_separated_candidates(("atha",), ()))
