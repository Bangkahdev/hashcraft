"""Tests for ``hashcraft.output.text`` (PRD 5, 6)."""

from __future__ import annotations

import io
import os

import pytest

from hashcraft.output.text import (
    DestinationExistsError,
    write_candidates_to_file,
    write_candidates_to_stdout,
)


def test_write_creates_file_with_one_candidate_per_line(tmp_path):
    destination = tmp_path / "wordlist.txt"
    count = write_candidates_to_file(["a", "b", "c"], destination)
    assert count == 3
    assert destination.read_text(encoding="utf-8") == "a\nb\nc\n"


def test_write_leaves_no_sibling_temp_file_after_success(tmp_path):
    destination = tmp_path / "wordlist.txt"
    write_candidates_to_file(["a"], destination)
    leftovers = [p for p in tmp_path.iterdir() if p != destination]
    assert leftovers == []


def test_write_uses_unix_newlines_only_regardless_of_platform(tmp_path):
    # PRD 4's canonical-generation contract requires byte-identical
    # output across platforms; the destination must never contain
    # platform-translated "\r\n" sequences.
    destination = tmp_path / "wordlist.txt"
    write_candidates_to_file(["a", "b"], destination)
    raw_bytes = destination.read_bytes()
    assert b"\r\n" not in raw_bytes
    assert raw_bytes == b"a\nb\n"


def test_write_refuses_existing_destination_without_overwrite(tmp_path):
    destination = tmp_path / "wordlist.txt"
    destination.write_text("original\n", encoding="utf-8")

    with pytest.raises(DestinationExistsError):
        write_candidates_to_file(["new"], destination, overwrite=False)

    assert destination.read_text(encoding="utf-8") == "original\n"


def test_write_with_overwrite_true_replaces_existing_content(tmp_path):
    destination = tmp_path / "wordlist.txt"
    destination.write_text("original\n", encoding="utf-8")

    write_candidates_to_file(["new1", "new2"], destination, overwrite=True)

    assert destination.read_text(encoding="utf-8") == "new1\nnew2\n"


def test_write_discards_temp_file_and_reraises_on_mid_stream_failure(tmp_path):
    destination = tmp_path / "wordlist.txt"

    def exploding_candidates():
        yield "one"
        yield "two"
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        write_candidates_to_file(exploding_candidates(), destination)

    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_write_failure_does_not_touch_pre_existing_destination(tmp_path):
    destination = tmp_path / "wordlist.txt"
    destination.write_text("safe\n", encoding="utf-8")

    def exploding_candidates():
        yield "one"
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        write_candidates_to_file(exploding_candidates(), destination, overwrite=True)

    # The temp file was discarded and the original destination -- only
    # ever replaced by os.replace() on success -- is untouched.
    assert destination.read_text(encoding="utf-8") == "safe\n"


def test_stdout_writer_contract_is_exactly_candidate_plus_newline():
    buffer = io.StringIO()
    count = write_candidates_to_stdout(["p1", "p2", "p3"], buffer)
    assert count == 3
    assert buffer.getvalue() == "p1\np2\np3\n"


def test_stdout_writer_preserves_partial_output_on_mid_stream_failure():
    buffer = io.StringIO()

    def exploding_candidates():
        yield "a"
        yield "b"
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        write_candidates_to_stdout(exploding_candidates(), buffer)

    # PRD 5: stdout may already contain earlier candidates when the
    # error occurs -- there is nothing to roll back on a stream.
    assert buffer.getvalue() == "a\nb\n"


def test_temp_file_lives_in_same_directory_as_destination(tmp_path, monkeypatch):
    destination = tmp_path / "wordlist.txt"
    seen_dirs = []

    import tempfile as tempfile_module

    original_mkstemp = tempfile_module.mkstemp

    def spying_mkstemp(*args, **kwargs):
        seen_dirs.append(kwargs.get("dir"))
        return original_mkstemp(*args, **kwargs)

    monkeypatch.setattr(tempfile_module, "mkstemp", spying_mkstemp)
    write_candidates_to_file(["a"], destination)

    assert seen_dirs == [os.path.dirname(str(destination)) or "."]
