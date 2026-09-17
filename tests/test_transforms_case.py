"""Tests for ``hashcraft.transforms.case`` (PRD 4.3)."""

from __future__ import annotations

import pytest

from hashcraft.transforms.case import apply_case_variants


def test_lower_mode_yields_single_lowercase_variant():
    assert list(apply_case_variants("AtHa", "lower")) == ["atha"]


def test_upper_mode_yields_single_uppercase_variant():
    assert list(apply_case_variants("AtHa", "upper")) == ["ATHA"]


def test_capitalize_mode_yields_single_capitalized_variant():
    assert list(apply_case_variants("ATHA", "capitalize")) == ["Atha"]


def test_all_mode_yields_lower_upper_capitalize_in_order():
    assert list(apply_case_variants("atha", "all")) == ["atha", "ATHA", "Atha"]


def test_all_mode_deduplicates_identical_variants_for_numeric_token():
    # "123".lower() == "123".upper() == "123".capitalize() == "123".
    assert list(apply_case_variants("123", "all")) == ["123"]


def test_all_mode_partial_collapse_when_two_of_three_coincide():
    # For a single lowercase letter: lower()="a", upper()="A",
    # capitalize()="A" -- upper and capitalize coincide, so only two
    # distinct variants should be emitted, in order.
    assert list(apply_case_variants("a", "all")) == ["a", "A"]


def test_invalid_case_mode_raises_value_error():
    with pytest.raises(ValueError):
        list(apply_case_variants("atha", "title"))  # type: ignore[arg-type]
