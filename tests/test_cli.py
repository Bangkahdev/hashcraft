"""Integration tests for ``hashcraft.cli`` (PRD 6, 8): every documented
exit code, the atomic-file/clean-stdout contracts at the CLI layer, and
the full ``generate --stdout | verify --stdin`` pipeline from PRD 6.
"""

from __future__ import annotations

import io
import sys

import pytest

from hashcraft import __version__, cli


class FakeTtyStdin(io.StringIO):
    """A stdin-like stream that reports itself as an interactive terminal."""

    def isatty(self) -> bool:  # noqa: D102
        return True


PASSWORD123_DIGEST = "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"


# --------------------------------------------------------------------------
# version / info -- exit code 0
# --------------------------------------------------------------------------


def test_version_command(capsys):
    assert cli.main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_info_command_mentions_authorized_use_and_algorithm(capsys):
    assert cli.main(["info"]) == 0
    out = capsys.readouterr().out
    assert "Authorized Use Only" in out
    assert "sha256" in out


# --------------------------------------------------------------------------
# generate: dry-run, file output, stdout, exit codes 0/2/3/5
# --------------------------------------------------------------------------


def test_generate_dry_run_never_creates_a_file_and_reports_to_stdout(tmp_path, capsys):
    destination = tmp_path / "wordlist.txt"
    exit_code = cli.main(
        ["generate", "--names", "atha", "--dry-run", "--output", str(destination)]
    )
    assert exit_code == 0
    assert not destination.exists()
    out = capsys.readouterr().out
    assert "dry run" in out.lower()
    assert "filter-aware count" in out


def test_generate_writes_file_matches_prd_section_6_example(tmp_path):
    destination = tmp_path / "wordlist.txt"
    exit_code = cli.main(
        [
            "generate",
            "--names",
            "atha,bangkah",
            "--max-words",
            "2",
            "--case",
            "lower",
            "--separators",
            "_",
            "--output",
            str(destination),
        ]
    )
    assert exit_code == 0
    assert destination.read_text(encoding="utf-8") == (
        "atha\nbangkah\natha_bangkah\nbangkah_atha\n"
    )


def test_generate_existing_file_without_overwrite_is_exit_2(tmp_path):
    destination = tmp_path / "wordlist.txt"
    destination.write_text("original\n", encoding="utf-8")

    exit_code = cli.main(["generate", "--names", "atha", "--output", str(destination)])

    assert exit_code == 2
    assert destination.read_text(encoding="utf-8") == "original\n"


def test_generate_overwrite_flag_replaces_existing_file(tmp_path):
    destination = tmp_path / "wordlist.txt"
    destination.write_text("original\n", encoding="utf-8")

    exit_code = cli.main(
        [
            "generate",
            "--names",
            "atha",
            "--max-words",
            "1",
            "--case",
            "lower",
            "--separators",
            "",
            "--output",
            str(destination),
            "--overwrite",
        ]
    )

    assert exit_code == 0
    assert destination.read_text(encoding="utf-8") == "atha\n"


def test_generate_stdout_contract_has_no_banner_or_status(capsys):
    exit_code = cli.main(
        [
            "generate",
            "--names",
            "atha",
            "--max-words",
            "1",
            "--case",
            "lower",
            "--separators",
            "",
            "--stdout",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == "atha\n"
    assert captured.err == ""


def test_generate_max_combinations_exceeded_is_exit_5_and_creates_no_file(tmp_path):
    destination = tmp_path / "wordlist.txt"
    exit_code = cli.main(
        [
            "generate",
            "--names",
            "a,b,c,d,e",
            "--max-words",
            "4",
            "--max-combinations",
            "5",
            "--output",
            str(destination),
        ]
    )
    assert exit_code == 5
    assert not destination.exists()


def test_generate_limit_exceeded_is_exit_5_and_leaves_no_partial_file(tmp_path):
    destination = tmp_path / "wordlist.txt"
    exit_code = cli.main(
        [
            "generate",
            "--names",
            "a,b,c,d,e",
            "--max-words",
            "3",
            "--limit",
            "3",
            "--max-combinations",
            "100000",
            "--output",
            str(destination),
        ]
    )
    assert exit_code == 5
    assert not destination.exists()


def test_generate_with_no_tokens_is_exit_3():
    exit_code = cli.main(["generate", "--stdout"])
    assert exit_code == 3


def test_generate_max_words_over_hard_cap_is_exit_2():
    exit_code = cli.main(
        ["generate", "--names", "atha", "--max-words", "999", "--stdout"]
    )
    assert exit_code == 2


def test_generate_requires_output_or_stdout_unless_dry_run():
    exit_code = cli.main(["generate", "--names", "atha"])
    assert exit_code == 2


def test_generate_quiet_suppresses_status_but_not_errors(tmp_path, capsys):
    destination = tmp_path / "wordlist.txt"
    destination.write_text("existing\n", encoding="utf-8")

    exit_code = cli.main(
        ["generate", "--names", "atha", "--output", str(destination), "--quiet"]
    )
    assert exit_code == 2
    err = capsys.readouterr().err
    assert "error" in err.lower()

    # A successful, quiet run should print no status at all.
    destination.unlink()
    exit_code = cli.main(
        [
            "generate",
            "--names",
            "atha",
            "--max-words",
            "1",
            "--separators",
            "",
            "--output",
            str(destination),
            "--quiet",
        ]
    )
    assert exit_code == 0
    assert capsys.readouterr().err == ""


# --------------------------------------------------------------------------
# verify: exit codes 0/3/4, and the full generate|verify pipeline
# --------------------------------------------------------------------------


def test_verify_match_via_wordlist_file_is_exit_0(tmp_path, capsys):
    wordlist = tmp_path / "wordlist.txt"
    wordlist.write_text("wrong1\npassword123\nwrong2\n", encoding="utf-8")

    exit_code = cli.main(
        ["verify", "--hash", PASSWORD123_DIGEST, "--wordlist", str(wordlist)]
    )

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "password123"


def test_full_generate_stdout_pipe_verify_stdin_matches_prd_section_6(
    capsys, monkeypatch
):
    import hashlib

    target = hashlib.sha256(b"atha").hexdigest()

    assert cli.main(["generate", "--names", "atha", "--stdout"]) == 0
    generated_stdout = capsys.readouterr().out

    monkeypatch.setattr(sys, "stdin", io.StringIO(generated_stdout))
    exit_code = cli.main(["verify", "--hash", target, "--stdin"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "atha"


def test_verify_no_match_is_exit_4(tmp_path):
    wordlist = tmp_path / "wordlist.txt"
    wordlist.write_text("nope1\nnope2\n", encoding="utf-8")

    exit_code = cli.main(
        ["verify", "--hash", PASSWORD123_DIGEST, "--wordlist", str(wordlist)]
    )
    assert exit_code == 4


def test_verify_invalid_digest_is_exit_3_before_reading_wordlist(tmp_path, monkeypatch):
    wordlist = tmp_path / "wordlist.txt"
    wordlist.write_text("password123\n", encoding="utf-8")

    def exploding_reader(path):
        raise AssertionError("wordlist must not be read for an invalid digest")

    monkeypatch.setattr(cli, "iter_wordlist_file_lines", exploding_reader)

    exit_code = cli.main(
        ["verify", "--hash", "not-a-valid-digest", "--wordlist", str(wordlist)]
    )
    assert exit_code == 3


def test_verify_unreadable_wordlist_is_exit_3():
    exit_code = cli.main(
        [
            "verify",
            "--hash",
            PASSWORD123_DIGEST,
            "--wordlist",
            "/nonexistent/path/wordlist.txt",
        ]
    )
    assert exit_code == 3


def test_verify_unsupported_algorithm_is_rejected_by_argparse_exit_2(tmp_path):
    wordlist = tmp_path / "wordlist.txt"
    wordlist.write_text("x\n", encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "verify",
                "--algorithm",
                "md5",
                "--hash",
                PASSWORD123_DIGEST,
                "--wordlist",
                str(wordlist),
            ]
        )
    assert excinfo.value.code == 2


# --------------------------------------------------------------------------
# exit code 1 (internal error) and --debug
# --------------------------------------------------------------------------


def test_internal_error_is_exit_1(monkeypatch, capsys):
    def exploding_iter_candidates(tokens, config):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "iter_candidates", exploding_iter_candidates)

    exit_code = cli.main(["generate", "--names", "atha", "--stdout"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "internal error" in err
    assert "boom" in err
    assert "Traceback" not in err


def test_internal_error_with_debug_includes_traceback(monkeypatch, capsys):
    def exploding_iter_candidates(tokens, config):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "iter_candidates", exploding_iter_candidates)

    exit_code = cli.main(["generate", "--names", "atha", "--stdout", "--debug"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "Traceback" in err


# --------------------------------------------------------------------------
# argparse-level invalid arguments -- exit code 2 (via SystemExit)
# --------------------------------------------------------------------------


def test_negative_max_words_is_argparse_exit_2(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "generate",
                "--names",
                "atha",
                "--max-words",
                "-1",
                "--output",
                str(tmp_path / "wl.txt"),
            ]
        )
    assert excinfo.value.code == 2


def test_verify_missing_required_hash_is_argparse_exit_2(tmp_path):
    wordlist = tmp_path / "wordlist.txt"
    wordlist.write_text("x\n", encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["verify", "--wordlist", str(wordlist)])
    assert excinfo.value.code == 2


# --------------------------------------------------------------------------
# interactive confirmation prompt (PRD 5's "configurable warning threshold")
# --------------------------------------------------------------------------


def _large_run_args(tmp_path, extra=()):
    return [
        "generate",
        "--names",
        "a,b,c",
        "--max-words",
        "2",
        "--case",
        "lower",
        "--separators",
        "_",
        "--warn-threshold",
        "3",
        "--max-combinations",
        "1000",
        "--output",
        str(tmp_path / "wl.txt"),
        *extra,
    ]


def test_confirmation_prompt_declined_aborts_without_writing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", FakeTtyStdin("n\n"))
    exit_code = cli.main(_large_run_args(tmp_path))
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "[y/N]" in captured.err
    assert "[y/N]" not in captured.out
    assert not (tmp_path / "wl.txt").exists()


def test_confirmation_prompt_accepted_proceeds_with_generation(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stdin", FakeTtyStdin("y\n"))
    exit_code = cli.main(_large_run_args(tmp_path))
    assert exit_code == 0
    destination = tmp_path / "wl.txt"
    assert destination.exists()
    lines = destination.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 9  # 3 singles + 6 length-2 permutations


def test_yes_flag_bypasses_confirmation_prompt_entirely(tmp_path, monkeypatch):
    # No stdin is provided at all; if the prompt were shown, reading an
    # answer from this empty, non-interactive stream would not raise,
    # but --yes must skip the prompt path entirely regardless.
    monkeypatch.setattr(sys, "stdin", FakeTtyStdin(""))
    exit_code = cli.main(_large_run_args(tmp_path, extra=["--yes"]))
    assert exit_code == 0
    assert (tmp_path / "wl.txt").exists()
