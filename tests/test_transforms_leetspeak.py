"""Tests for ``hashcraft.transforms.leetspeak`` (PRD 4.3)."""

from __future__ import annotations

import pytest

from hashcraft.transforms.leetspeak import (
    LEET_MAP,
    generate_leetspeak_variants,
)


def test_leet_map_matches_prd_substitution_table():
    assert LEET_MAP == {
        "a": "@",
        "e": "3",
        "i": "1",
        "o": "0",
        "s": "$",
        "t": "7",
    }


def test_unmodified_candidate_is_yielded_first():
    variants = list(generate_leetspeak_variants("at", max_variants=10))
    assert variants[0] == "at"


def test_no_substitutable_characters_yields_only_the_unmodified_candidate():
    variants = list(generate_leetspeak_variants("xyz", max_variants=64))
    assert variants == ["xyz"]


def test_left_to_right_deterministic_variant_order():
    # For "at": positions [0]='a', [1]='t'. Mask order 1,2,3 -> leftmost
    # position varies first: '@t', then 'a7', then '@7'.
    variants = list(generate_leetspeak_variants("at", max_variants=4))
    assert variants == ["at", "@t", "a7", "@7"]


def test_max_variants_bound_is_respected_and_counts_the_unmodified_one():
    variants = list(generate_leetspeak_variants("at", max_variants=1))
    assert variants == ["at"]

    variants = list(generate_leetspeak_variants("at", max_variants=2))
    assert variants == ["at", "@t"]


def test_case_insensitive_substitution_preserves_untouched_character_case():
    # 'A' matches the 'a' rule case-insensitively; the untouched 'T'
    # keeps its original (upper) case since it is never substituted here.
    variants = list(generate_leetspeak_variants("AT", max_variants=2))
    assert variants == ["AT", "@T"]


def test_invalid_max_variants_raises_value_error():
    with pytest.raises(ValueError):
        list(generate_leetspeak_variants("at", max_variants=0))
    with pytest.raises(ValueError):
        list(generate_leetspeak_variants("at", max_variants=-5))


def test_deterministic_repeat_call_matches():
    first = list(generate_leetspeak_variants("password", max_variants=64))
    second = list(generate_leetspeak_variants("password", max_variants=64))
    assert first == second


def test_no_full_materialization_for_a_long_highly_substitutable_candidate():
    # A 40-character, fully-substitutable candidate has 2**40 possible
    # combinations. If this eagerly built the full combination space it
    # would never complete; finishing quickly with exactly `max_variants`
    # results demonstrates the generator only computes what is needed.
    long_candidate = "a" * 40
    variants = list(generate_leetspeak_variants(long_candidate, max_variants=5))
    assert len(variants) == 5
    assert variants[0] == long_candidate
