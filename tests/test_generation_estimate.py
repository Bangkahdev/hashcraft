"""Tests for ``hashcraft.generation.estimate`` (PRD 5)."""

from __future__ import annotations

import itertools

import pytest

from hashcraft.generation.estimate import (
    filter_aware_count,
    raw_upper_bound,
    run_filter_aware_preflight,
)
from hashcraft.generation.generator import GenerationConfig, iter_candidates


def test_filter_aware_count_exact_when_under_ceiling():
    result = filter_aware_count(["a", "b", "c"], max_combinations=10)
    assert result.count == 3
    assert result.exceeds_ceiling is False


def test_filter_aware_count_stops_at_ceiling_plus_one():
    # An "infinite" stream with an assertion that fails if pulled too
    # far proves counting truly stops early rather than exhausting it.
    pulls = itertools.count()

    def guarded_infinite_stream():
        for _ in itertools.repeat("x"):
            n = next(pulls)
            assert n <= 5, "counting pulled more than max_combinations + 1 items"
            yield "x"

    result = filter_aware_count(guarded_infinite_stream(), max_combinations=4)
    assert result.count == 5  # max_combinations + 1
    assert result.exceeds_ceiling is True


def test_filter_aware_count_requires_positive_ceiling():
    with pytest.raises(ValueError):
        filter_aware_count(["a"], max_combinations=0)


def test_run_filter_aware_preflight_matches_real_generation_count():
    config = GenerationConfig(max_words=2, case_mode="lower", separators=("_",))
    tokens = ("atha", "bangkah", "cinta")

    preflight = run_filter_aware_preflight(tokens, config, max_combinations=10_000)
    real = list(iter_candidates(tokens, config))

    assert preflight.exceeds_ceiling is False
    assert preflight.count == len(real)


def test_run_filter_aware_preflight_detects_exceeding_ceiling():
    config = GenerationConfig(max_words=2, case_mode="lower", separators=("_",))
    tokens = ("a", "b", "c")
    preflight = run_filter_aware_preflight(tokens, config, max_combinations=2)
    assert preflight.exceeds_ceiling is True
    assert preflight.count == 3  # max_combinations + 1


def test_raw_upper_bound_zero_tokens():
    config = GenerationConfig()
    assert raw_upper_bound(0, config) == 0


def test_raw_upper_bound_exact_in_the_trivial_all_transforms_off_case():
    # With case="lower" (multiplier 1), leet/symbols disabled
    # (multiplier 1), the "loose" formula must degenerate to an exact
    # count: nPr(n, r) summed over r, times the separator count.
    config = GenerationConfig(max_words=2, case_mode="lower", separators=("_", "."))
    tokens = ("a", "b", "c")
    bound = raw_upper_bound(len(tokens), config)
    real_count = len(list(iter_candidates(tokens, config)))
    assert bound == real_count


def test_raw_upper_bound_is_a_loose_upper_bound_when_transforms_are_on():
    config = GenerationConfig(
        max_words=2,
        case_mode="all",
        separators=("_",),
        leet_enabled=True,
        max_leet_variants=8,
        symbols_enabled=True,
        symbols=("!", "@"),
    )
    tokens = ("atha", "bangkah")
    bound = raw_upper_bound(len(tokens), config)
    real_count = len(list(iter_candidates(tokens, config)))
    assert bound >= real_count
