"""Tests for ``hashcraft.transforms.symbols`` (PRD 4.3)."""

from __future__ import annotations

from hashcraft.transforms.symbols import DEFAULT_SYMBOLS, generate_symbol_variants


def test_default_symbol_list_matches_prd():
    assert DEFAULT_SYMBOLS == ("!", "@", "#", "$", "_", "-")


def test_disabled_symbols_pass_through_unchanged():
    assert list(generate_symbol_variants("atha", enabled=False)) == ["atha"]


def test_disabled_ignores_symbols_argument_too():
    assert list(generate_symbol_variants("atha", ("!", "@"), enabled=False)) == ["atha"]


def test_enabled_yields_unmodified_then_prefix_suffix_per_symbol_in_order():
    variants = list(generate_symbol_variants("atha", ("!", "@"), enabled=True))
    assert variants == ["atha", "!atha", "atha!", "@atha", "atha@"]


def test_enabled_with_default_symbol_list():
    variants = list(generate_symbol_variants("at", enabled=True))
    expected = ["at"]
    for symbol in DEFAULT_SYMBOLS:
        expected.append(f"{symbol}at")
        expected.append(f"at{symbol}")
    assert variants == expected


def test_enabled_with_empty_symbol_list_behaves_like_disabled():
    assert list(generate_symbol_variants("atha", (), enabled=True)) == ["atha"]
