"""Tests for ``hashcraft.sources.text`` (PRD 4.1)."""

from __future__ import annotations

import io

import pytest

from hashcraft.sources.text import (
    CATEGORY_ORDER,
    iter_cli_tokens,
    iter_file_tokens,
    iter_stdin_tokens,
    iter_tokens,
    normalize_tokens,
)


def test_cli_tokens_follow_fixed_category_order_not_dict_order():
    # Dict insertion order is deliberately scrambled relative to
    # CATEGORY_ORDER; the output must still follow CATEGORY_ORDER.
    source_values = {
        "dates": "2026-01-01",
        "names": "atha,bangkah",
        "cities": "lhokseumawe",
    }
    tokens = list(iter_cli_tokens(source_values))
    assert tokens == ["atha", "bangkah", "lhokseumawe", "2026-01-01"]


def test_cli_tokens_split_comma_strip_whitespace_and_discard_empty():
    source_values = {"names": " atha , , bangkah ,  "}
    tokens = list(iter_cli_tokens(source_values))
    assert tokens == ["atha", "bangkah"]


def test_cli_tokens_skip_missing_or_empty_categories():
    source_values = {"names": "atha", "cities": None, "years": ""}
    tokens = list(iter_cli_tokens(source_values))
    assert tokens == ["atha"]


def test_cli_tokens_duplicate_values_are_preserved_not_deduplicated():
    # PRD 4.2's "atha_atha is not generated from a single occurrence"
    # only makes sense if two occurrences of the same value can exist.
    source_values = {"names": "atha,atha"}
    tokens = list(iter_cli_tokens(source_values))
    assert tokens == ["atha", "atha"]


def test_category_order_matches_prd_4_1():
    assert CATEGORY_ORDER == (
        "names",
        "usernames",
        "pets",
        "cities",
        "vehicles",
        "food",
        "hobbies",
        "organizations",
        "keywords",
        "years",
        "dates",
    )


def test_file_tokens_strip_whitespace_discard_empty_lines_utf8(tmp_path):
    path = tmp_path / "tokens.txt"
    path.write_text("  atha  \n\nbangkah\ncafé\n   \n", encoding="utf-8")
    tokens = list(iter_file_tokens(path))
    assert tokens == ["atha", "bangkah", "café"]


def test_stdin_tokens_strip_whitespace_and_discard_empty():
    stream = io.StringIO("  atha  \n\n bangkah \n")
    tokens = list(iter_stdin_tokens(stream))
    assert tokens == ["atha", "bangkah"]


def test_iter_tokens_combines_sources_in_prd_order(tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_text("from_file\n", encoding="utf-8")
    stdin_stream = io.StringIO("from_stdin\n")

    tokens = list(
        iter_tokens(
            source_values={"names": "from_cli"},
            input_path=input_path,
            stdin_stream=stdin_stream,
        )
    )
    # CLI-option order, then input-file order, then stdin order (PRD 4.1).
    assert tokens == ["from_cli", "from_file", "from_stdin"]


def test_iter_tokens_all_sources_optional():
    assert list(iter_tokens()) == []


def test_normalize_tokens_default_nfc_composes_combining_characters():
    # "e" + combining acute accent (decomposed) -> single "é" codepoint (NFC).
    decomposed = "e\u0301"
    (normalized,) = list(normalize_tokens([decomposed]))
    assert normalized == "\u00e9"
    assert len(normalized) == 1


def test_normalize_tokens_none_mode_passes_through_unchanged():
    decomposed = "e\u0301"
    (normalized,) = list(normalize_tokens([decomposed], mode="none"))
    assert normalized == decomposed


def test_normalize_tokens_invalid_mode_raises():
    with pytest.raises(ValueError):
        list(normalize_tokens(["atha"], mode="nfkc"))  # type: ignore[arg-type]
