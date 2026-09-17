"""Tests for ``hashcraft.generation.limits`` (PRD 5)."""

from __future__ import annotations

import pytest

from hashcraft.generation.limits import (
    DEFAULT_LIMIT,
    DEFAULT_MAX_COMBINATIONS,
    EmissionLimitExceeded,
    ResourceLimits,
    enforce_emission_limit,
)


def test_resource_limits_defaults_match_prd():
    limits = ResourceLimits()
    assert limits.max_combinations == 500_000 == DEFAULT_MAX_COMBINATIONS
    assert limits.limit == 100_000 == DEFAULT_LIMIT


@pytest.mark.parametrize(
    "kwargs",
    [{"max_combinations": 0}, {"max_combinations": -1}, {"limit": 0}, {"limit": -1}],
)
def test_resource_limits_reject_non_positive_values(kwargs):
    with pytest.raises(ValueError):
        ResourceLimits(**kwargs)


def test_enforce_emission_limit_yields_up_to_limit_without_raising():
    result = list(enforce_emission_limit(iter(["a", "b"]), limit=5))
    assert result == ["a", "b"]


def test_enforce_emission_limit_raises_on_the_limit_plus_one_th_item():
    result = []
    with pytest.raises(EmissionLimitExceeded) as excinfo:
        for candidate in enforce_emission_limit(iter(["a", "b", "c"]), limit=2):
            result.append(candidate)
    # Exactly `limit` candidates were yielded before the error.
    assert result == ["a", "b"]
    assert excinfo.value.limit == 2


def test_enforce_emission_limit_does_not_pull_beyond_limit_plus_one():
    pull_count = 0

    def counting_source():
        nonlocal pull_count
        while True:
            pull_count += 1
            yield "x"

    with pytest.raises(EmissionLimitExceeded):
        list(enforce_emission_limit(counting_source(), limit=3))

    # 3 yielded + 1 pulled-and-rejected = 4 pulls, never more.
    assert pull_count == 4


def test_enforce_emission_limit_requires_positive_limit():
    with pytest.raises(ValueError):
        list(enforce_emission_limit(iter(["a"]), limit=0))
