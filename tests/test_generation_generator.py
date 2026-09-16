"""Tests for ``hashcraft.generation.generator`` (PRD 4)."""

from __future__ import annotations

import itertools

import pytest

from hashcraft.generation.generator import GenerationConfig, iter_candidates


def test_generation_config_defaults_match_prd():
    config = GenerationConfig()
    assert config.max_words == 2
    assert config.case_mode == "all"
    assert config.leet_enabled is False
    assert config.max_leet_variants == 64
    assert config.separators == ("", "_", ".", "-")
    assert config.symbols_enabled is False
    assert config.symbols == ("!", "@", "#", "$", "_", "-")
    assert config.max_length == 32


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_words": 0},
        {"max_words": -1},
        {"max_leet_variants": 0},
        {"max_length": 0},
        {"separators": ()},
    ],
)
def test_generation_config_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        GenerationConfig(**kwargs)


def test_prd_section_6_worked_example_exact_output():
    # hashcraft generate --names atha,bangkah --max-words 2 --case lower
    #                     --separators "_"
    config = GenerationConfig(max_words=2, case_mode="lower", separators=("_",))
    result = list(iter_candidates(("atha", "bangkah"), config))
    assert result == ["atha", "bangkah", "atha_bangkah", "bangkah_atha"]


def test_deterministic_repeat_calls_produce_identical_stream():
    config = GenerationConfig(max_words=2, case_mode="lower", separators=("_", "."))
    tokens = ("atha", "bangkah", "cinta")
    first = list(iter_candidates(tokens, config))
    second = list(iter_candidates(tokens, config))
    assert first == second


def test_structural_dedup_collapses_case_variants_for_numeric_token():
    # "123" is identical under lower/upper/capitalize, so case="all"
    # must collapse to exactly one emitted candidate for a single seed.
    config = GenerationConfig(max_words=1, case_mode="all", separators=("",))
    assert list(iter_candidates(("123",), config)) == ["123"]


def test_structural_dedup_is_per_seed_not_global_across_separators():
    # PRD 4.4: no promise of global dedup across distinct (sequence,
    # separator) seeds. A single-token sequence looks identical under
    # every separator (nothing to separate), so each of the 4 default
    # separators is its own seed and repeats the same value.
    config = GenerationConfig(max_words=1, case_mode="lower")
    result = list(iter_candidates(("atha",), config))
    assert result == ["atha"] * len(config.separators)


def test_max_length_filters_by_unicode_code_points_not_utf8_bytes():
    # A single emoji code point encodes to 4 UTF-8 bytes; max_length=1
    # must still allow it through, since PRD 4.4 measures code points.
    config = GenerationConfig(
        max_words=1, case_mode="lower", separators=("",), max_length=1
    )
    assert list(iter_candidates(("\U0001f4a7",), config)) == ["\U0001f4a7"]


def test_max_length_excludes_candidates_over_the_limit():
    config = GenerationConfig(
        max_words=1, case_mode="lower", separators=("",), max_length=3
    )
    assert list(iter_candidates(("atha",), config)) == []  # len("atha") == 4


def test_leetspeak_variants_flow_through_the_full_pipeline():
    config = GenerationConfig(
        max_words=1,
        case_mode="lower",
        separators=("",),
        leet_enabled=True,
        max_leet_variants=2,
    )
    assert list(iter_candidates(("at",), config)) == ["at", "@t"]


def test_symbol_variants_flow_through_the_full_pipeline():
    config = GenerationConfig(
        max_words=1,
        case_mode="lower",
        separators=("",),
        symbols_enabled=True,
        symbols=("!",),
    )
    assert list(iter_candidates(("at",), config)) == ["at", "!at", "at!"]


def test_multi_word_case_variants_are_a_cartesian_product_per_token():
    # Approved assumption: for a multi-word sequence, each token's case
    # variant pool is computed independently and combined via Cartesian
    # product, in token order. Verify against an independent, from-first-
    # principles computation (not the production code) for two tokens
    # with fully distinct case variants (no accidental collisions).
    config = GenerationConfig(max_words=2, case_mode="all", separators=("",))
    tokens = ("ab", "cd")
    result = list(iter_candidates(tokens, config))

    def case_variants(token: str) -> list[str]:
        return [token.lower(), token.upper(), token.capitalize()]

    expected: list[str] = []
    expected.extend(case_variants("ab"))
    expected.extend(case_variants("cd"))
    for combo in itertools.product(case_variants("ab"), case_variants("cd")):
        expected.append("".join(combo))
    for combo in itertools.product(case_variants("cd"), case_variants("ab")):
        expected.append("".join(combo))

    assert result == expected
    assert len(result) == 3 + 3 + 9 + 9


def test_duplicate_input_tokens_are_not_globally_deduplicated():
    # Two independent ('atha', 'atha') sequence instances (from
    # duplicate-valued input tokens) each build and discard their own
    # seed, so the resulting duplicate candidate is not collapsed away.
    config = GenerationConfig(max_words=2, case_mode="lower", separators=("",))
    result = list(iter_candidates(("atha", "atha"), config))
    assert result.count("athaatha") == 2


def test_empty_token_list_yields_no_candidates():
    config = GenerationConfig()
    assert list(iter_candidates((), config)) == []
