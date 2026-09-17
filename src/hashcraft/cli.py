"""Command-line interface: argument parsing, command dispatch, and the
exit-code contract in PRD 8:

    0  successful generation or a verification match
    1  internal/general error
    2  invalid command-line arguments
    3  invalid input (including malformed SHA-256 digest or unreadable input)
    4  verification completed with no match
    5  preflight or runtime resource limit exceeded

This module is the thin adapter described in PRD 9 ("The generator,
verifier, sources, and output writer must be independently callable
Python APIs. The CLI is an adapter over those APIs.") -- it parses
arguments, wires the independently-callable modules together in
pipeline order, and maps their exceptions to the exit codes above. It
contains no generation, hashing, or output logic of its own.

Design decisions inferred where PRD 6/8 do not fully specify CLI
mechanics (flagged here for confirmation, in the same spirit as the
assumptions already noted and approved in earlier modules):

* ``--max-words`` "may not exceed the hard limit configured for the
  invocation" (PRD 4.2) without PRD 4.2 naming that limit's value.
  ``_MAX_WORDS_HARD_CAP`` below is this implementation's chosen bound
  (10), separate from and much smaller than ``--max-combinations`` /
  ``--limit``; it exists purely to reject a clearly-mistyped
  ``--max-words`` before any combinatorial work starts.
* ``generate`` requires exactly one of ``--output`` / ``--stdout``
  unless ``--dry-run`` is given (PRD 5 says dry-run "never creates an
  output file", implying no destination is needed for it); PRD 6 does
  not state this requirement explicitly for the non-dry-run case.
* The "configurable warning threshold" for the interactive
  confirmation prompt (PRD 5) is exposed as ``--warn-threshold`` and,
  when not given, defaults to the run's own ``--limit`` value: an
  estimate above ``--limit`` (even if still under
  ``--max-combinations``) is exactly the case where real generation
  would later fail with exit code 5, so warning at that same
  threshold ties the prompt to genuinely useful information.
* ``--dry-run``'s report is written to stdout, not stderr: PRD 6's
  "no banner ... on standard output" rule is scoped to
  ``generate --stdout``'s candidate-emission contract, and a dry run
  never emits candidates at all -- its report *is* the command's
  requested output, analogous to ``info`` and ``version``.
* An empty resolved token list (no sources produced anything) is
  treated as invalid input (exit code 3), since generation cannot
  proceed meaningfully without at least one token.
* (v2) ``verify --jobs``/``-j`` resolves PRD v2 section B's own
  ambiguous wording ("Default: 1 ... or auto-detect CPU count if
  ``-j 0`` or flag is omitted") as: omitted -> ``1`` (sequential,
  byte-identical to v1's behavior); ``--jobs 0`` -> auto-detect via
  ``os.cpu_count()`` (falling back to ``1`` if that returns
  ``None``, e.g. inside some containers); ``--jobs N`` (N>0) -> ``N``
  worker processes. See ``hashing/verifier.py``'s module docstring
  for the ordering/determinism guarantees of the parallel path itself.

Flag these for explicit PRD confirmation before relying on them.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from collections.abc import Sequence
from typing import NoReturn, TextIO

from . import __version__
from .generation.combinations import DEFAULT_SEPARATORS
from .generation.estimate import PreflightResult, raw_upper_bound, run_filter_aware_preflight
from .generation.generator import GenerationConfig, iter_candidates
from .generation.limits import (
    DEFAULT_LIMIT,
    DEFAULT_MAX_COMBINATIONS,
    EmissionLimitExceeded,
    ResourceLimits,
    enforce_emission_limit,
)
from .hashing.algorithms import get_algorithm, supported_algorithm_names
from .hashing.validators import InvalidDigestError, validate_and_normalize_digest
from .hashing.verifier import (
    iter_stdin_candidate_lines,
    iter_wordlist_file_lines,
    verify,
)
from .output.text import (
    DestinationExistsError,
    write_candidates_to_file,
    write_candidates_to_stdout,
)
from .sources.text import CATEGORY_ORDER, iter_tokens, normalize_tokens
from .transforms.leetspeak import DEFAULT_MAX_LEET_VARIANTS
from .transforms.symbols import DEFAULT_SYMBOLS

_MAX_WORDS_HARD_CAP = 10  # See module docstring's first design note.

_EXIT_SUCCESS = 0
_EXIT_GENERAL_ERROR = 1
_EXIT_INVALID_ARGUMENTS = 2
_EXIT_INVALID_INPUT = 3
_EXIT_NO_MATCH = 4
_EXIT_LIMIT_EXCEEDED = 5


class _CliError(Exception):
    """An error already mapped to one of PRD 8's exit codes."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"{value!r} must be a positive integer")
    return parsed


def _non_negative_int(value: str) -> int:
    """Type for ``--jobs``/``-j`` (PRD v2 section B): 0 or a positive integer.

    ``0`` is a legitimate, meaningful value here ("auto-detect CPU
    count" -- resolved later by ``_resolve_jobs``), unlike every other
    numeric option in this CLI, which is why this is a separate type
    function from ``_positive_int`` rather than reusing it.
    """
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"{value!r} must be 0 or a positive integer")
    return parsed


def _comma_list(value: str | None, *, default: Sequence[str]) -> tuple[str, ...]:
    """Parse a ``--separators``/``--symbols-list``-style comma list.

    ``value is None`` means the flag was not supplied at all -- use
    ``default``. Any *supplied* string, including the empty string, is
    split on commas with no further filtering: an empty entry is a
    legitimate value for this option (PRD 4.3: "an empty separator is
    valid"), so ``--separators ""`` must produce a single empty-string
    separator, not silently fall back to the default list.
    """
    if value is None:
        return tuple(default)
    return tuple(value.split(","))


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--quiet",
        action="store_true",
        help="suppress non-error status on stderr (never suppresses errors)",
    )
    common.add_argument(
        "--debug",
        action="store_true",
        help="show full tracebacks for unexpected errors",
    )

    parser = argparse.ArgumentParser(prog="hashcraft")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- generate -----------------------------------------------------
    generate = subparsers.add_parser(
        "generate", parents=[common], help="deterministically generate candidates"
    )

    sources_group = generate.add_argument_group("source options")
    for category in CATEGORY_ORDER:
        sources_group.add_argument(f"--{category}", default=None)
    sources_group.add_argument("--input", dest="input_path", default=None)
    sources_group.add_argument(
        "--stdin", dest="use_stdin_tokens", action="store_true"
    )
    sources_group.add_argument(
        "--unicode-normalization",
        choices=("nfc", "none"),
        default="nfc",
    )

    generation_group = generate.add_argument_group("generation options")
    generation_group.add_argument("--max-words", type=_positive_int, default=2)
    generation_group.add_argument(
        "--case", choices=("lower", "upper", "capitalize", "all"), default="all"
    )
    generation_group.add_argument("--separators", default=None)
    generation_group.add_argument("--symbols", action="store_true")
    generation_group.add_argument("--no-symbols", action="store_true")
    generation_group.add_argument("--symbols-list", default=None)
    generation_group.add_argument("--leet", action="store_true")
    generation_group.add_argument(
        "--max-leet-variants", type=_positive_int, default=DEFAULT_MAX_LEET_VARIANTS
    )
    generation_group.add_argument("--max-length", type=_positive_int, default=32)

    limits_group = generate.add_argument_group("limits and preflight")
    limits_group.add_argument(
        "--max-combinations", type=_positive_int, default=DEFAULT_MAX_COMBINATIONS
    )
    limits_group.add_argument("--limit", type=_positive_int, default=DEFAULT_LIMIT)
    limits_group.add_argument("--warn-threshold", type=_positive_int, default=None)
    limits_group.add_argument("--dry-run", action="store_true")
    limits_group.add_argument("--yes", action="store_true")

    output_group = generate.add_argument_group("output options")
    destination = output_group.add_mutually_exclusive_group()
    destination.add_argument("--output", dest="output_path", default=None)
    destination.add_argument("--stdout", dest="use_stdout", action="store_true")
    output_group.add_argument("--overwrite", action="store_true")

    # -- verify ---------------------------------------------------------
    verify_parser = subparsers.add_parser(
        "verify", parents=[common], help="verify a digest against candidates"
    )
    verify_parser.add_argument(
        "--algorithm", choices=supported_algorithm_names(), default="sha256"
    )
    verify_parser.add_argument("--hash", dest="target_hash", required=True)
    verify_source = verify_parser.add_mutually_exclusive_group(required=True)
    verify_source.add_argument("--wordlist", dest="wordlist_path", default=None)
    verify_source.add_argument(
        "--stdin", dest="use_stdin_candidates", action="store_true"
    )
    verify_parser.add_argument(
        "--jobs",
        "-j",
        type=_non_negative_int,
        default=1,
        help=(
            "worker processes for parallel hashing (PRD v2 section B); "
            "default 1 (sequential); 0 auto-detects the CPU count"
        ),
    )

    # -- info / version ---------------------------------------------------
    subparsers.add_parser("info", parents=[common], help="show tool information")
    subparsers.add_parser("version", parents=[common], help="show the version")

    return parser


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------


def _status(message: str, *, stream: TextIO, quiet: bool) -> None:
    """Write a non-error status line to stderr, honoring ``--quiet`` (PRD 6)."""
    if not quiet:
        print(message, file=stream)


def _error(message: str, *, stream: TextIO) -> None:
    """Write an error line to stderr. Never suppressed by ``--quiet`` (PRD 6)."""
    print(f"error: {message}", file=stream)


def _confirm(prompt: str) -> bool:
    """Prompt for y/N confirmation without touching stdout.

    Writes the prompt to stderr and reads the answer from stdin
    directly (rather than the builtin ``input()``, which writes its
    prompt to stdout) so this never violates the clean ``--stdout``
    contract in PRD 6, even when a confirmation is needed for a run
    that will otherwise stream candidates straight to stdout.
    """
    print(f"{prompt} [y/N]: ", file=sys.stderr, end="", flush=True)
    answer = sys.stdin.readline()
    return answer.strip().lower() in ("y", "yes")


# --------------------------------------------------------------------------
# generate
# --------------------------------------------------------------------------


def _resolve_generation_config(args: argparse.Namespace) -> GenerationConfig:
    separators = (
        _comma_list(args.separators, default=DEFAULT_SEPARATORS)
        if args.separators is not None
        else DEFAULT_SEPARATORS
    )
    symbols = (
        _comma_list(args.symbols_list, default=DEFAULT_SYMBOLS)
        if args.symbols_list is not None
        else DEFAULT_SYMBOLS
    )
    return GenerationConfig(
        max_words=args.max_words,
        case_mode=args.case,
        leet_enabled=args.leet,
        max_leet_variants=args.max_leet_variants,
        separators=separators,
        symbols_enabled=args.symbols,
        symbols=symbols,
        max_length=args.max_length,
    )


def _resolve_tokens(args: argparse.Namespace) -> tuple[str, ...]:
    source_values = {category: getattr(args, category) for category in CATEGORY_ORDER}
    stdin_stream = sys.stdin if args.use_stdin_tokens else None
    raw_tokens = iter_tokens(
        source_values=source_values,
        input_path=args.input_path,
        stdin_stream=stdin_stream,
    )
    return tuple(normalize_tokens(raw_tokens, mode=args.unicode_normalization))


def _print_dry_run_report(
    *,
    tokens: Sequence[str],
    config: GenerationConfig,
    resource_limits: ResourceLimits,
    preflight: PreflightResult,
    stream: TextIO,
) -> None:
    print("Hashcraft dry run", file=stream)
    print(f"  tokens: {list(tokens)}", file=stream)
    print(f"  max-words: {config.max_words}", file=stream)
    print(f"  case: {config.case_mode}", file=stream)
    print(f"  separators: {list(config.separators)}", file=stream)
    print(f"  leet: {config.leet_enabled} (max variants: {config.max_leet_variants})", file=stream)
    print(f"  symbols: {config.symbols_enabled} ({list(config.symbols)})", file=stream)
    print(f"  max-length: {config.max_length}", file=stream)
    print(f"  max-combinations (ceiling): {resource_limits.max_combinations}", file=stream)
    print(f"  limit (emission ceiling): {resource_limits.limit}", file=stream)
    bound = raw_upper_bound(len(tokens), config)
    print(f"  raw upper bound (conservative, ignores filters): {bound}", file=stream)
    if preflight.exceeds_ceiling:
        print(
            f"  filter-aware count: exceeds --max-combinations={resource_limits.max_combinations}",
            file=stream,
        )
    else:
        print(f"  filter-aware count (exact): {preflight.count}", file=stream)


def _cmd_generate(args: argparse.Namespace) -> int:
    if not args.dry_run and not (args.output_path or args.use_stdout):
        raise _CliError(
            "generate requires --output PATH or --stdout (unless --dry-run)",
            _EXIT_INVALID_ARGUMENTS,
        )
    if args.max_words > _MAX_WORDS_HARD_CAP:
        raise _CliError(
            f"--max-words={args.max_words} exceeds the hard limit of {_MAX_WORDS_HARD_CAP}",
            _EXIT_INVALID_ARGUMENTS,
        )

    tokens = _resolve_tokens(args)
    if not tokens:
        raise _CliError("no input tokens were supplied", _EXIT_INVALID_INPUT)

    config = _resolve_generation_config(args)
    resource_limits = ResourceLimits(
        max_combinations=args.max_combinations, limit=args.limit
    )

    preflight = run_filter_aware_preflight(
        tokens, config, resource_limits.max_combinations
    )

    if args.dry_run:
        _print_dry_run_report(
            tokens=tokens,
            config=config,
            resource_limits=resource_limits,
            preflight=preflight,
            stream=sys.stdout,
        )
        return _EXIT_SUCCESS

    if preflight.exceeds_ceiling:
        raise _CliError(
            f"filter-aware candidate estimate exceeds "
            f"--max-combinations={resource_limits.max_combinations}",
            _EXIT_LIMIT_EXCEEDED,
        )

    warn_threshold = (
        args.warn_threshold if args.warn_threshold is not None else resource_limits.limit
    )
    interactive = sys.stdin.isatty() and not args.use_stdin_tokens
    if (
        preflight.count > warn_threshold
        and not args.yes
        and interactive
        and not _confirm(
            f"About to generate {preflight.count} candidates "
            f"(above warning threshold {warn_threshold}). Continue?"
        )
    ):
        raise _CliError("aborted by user", _EXIT_GENERAL_ERROR)

    candidates = enforce_emission_limit(
        iter_candidates(tokens, config), resource_limits.limit
    )

    if args.use_stdout:
        # PRD 6: no banner/progress/status may reach stdout in this mode.
        write_candidates_to_stdout(candidates, sys.stdout)
        return _EXIT_SUCCESS

    # Status is only printed after a successful write (PRD 6: status/
    # warnings belong on stderr, but a message implying work is
    # underway before we even know the destination is writable would
    # be misleading -- e.g. when DestinationExistsError is about to
    # be raised by write_candidates_to_file below).
    count = write_candidates_to_file(
        candidates, args.output_path, overwrite=args.overwrite
    )
    _status(
        f"Done: {count} candidate(s) written to {args.output_path}",
        stream=sys.stderr,
        quiet=args.quiet,
    )
    return _EXIT_SUCCESS


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------


def _resolve_jobs(requested: int) -> int:
    """Resolve ``--jobs``' CLI value to a concrete positive worker count.

    ``0`` means "auto-detect" (PRD v2 section B) via ``os.cpu_count()``;
    some sandboxed/containerized environments report ``None`` here, in
    which case this falls back to ``1`` (fully sequential) rather than
    failing the command outright.
    """
    if requested == 0:
        return os.cpu_count() or 1
    return requested


def _cmd_verify(args: argparse.Namespace) -> int:
    algorithm = get_algorithm(args.algorithm)
    # PRD 7: invalid digests fail before the wordlist/stdin is read at
    # all. The expected length depends on the selected algorithm (v2
    # section A), so the algorithm must be resolved first.
    validate_and_normalize_digest(
        args.target_hash, expected_hex_length=algorithm.digest_hex_length
    )
    jobs = _resolve_jobs(args.jobs)

    if args.wordlist_path is not None:
        try:
            candidates = iter_wordlist_file_lines(args.wordlist_path)
            result = verify(candidates, args.target_hash, algorithm=algorithm, jobs=jobs)
        except OSError as exc:
            raise _CliError(f"could not read wordlist: {exc}", _EXIT_INVALID_INPUT) from exc
    else:
        candidates = iter_stdin_candidate_lines(sys.stdin)
        result = verify(candidates, args.target_hash, algorithm=algorithm, jobs=jobs)

    if result.matched:
        print(result.matched_candidate)
        _status(
            f"checked {result.checked_count} candidate(s)",
            stream=sys.stderr,
            quiet=args.quiet,
        )
        return _EXIT_SUCCESS

    _error(f"no match after checking {result.checked_count} candidate(s)", stream=sys.stderr)
    return _EXIT_NO_MATCH


# --------------------------------------------------------------------------
# info / version
# --------------------------------------------------------------------------

_INFO_TEXT = """\
Hashcraft {version}

A deterministic candidate-generation and cryptographic
digest-verification CLI for authorized security research, password
auditing, CTFs, and security education. It is not a password cracker
or a SHA-256 decryptor.

Authorized Use Only: use this tool only against systems and hashes
you own or are explicitly authorized to test -- CTFs, laboratory
work, lawful research, and permitted penetration tests.

SHA-256 (and every other supported algorithm here) is a one-way
cryptographic hash function. A failed verification means only that
none of the generated candidates matched the supplied digest; it does
not establish that an original plaintext does not exist.

Supported digest algorithm(s): {algorithms}
"""


def _cmd_info(_args: argparse.Namespace) -> int:
    print(_INFO_TEXT.format(version=__version__, algorithms=", ".join(supported_algorithm_names())))
    return _EXIT_SUCCESS


def _cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return _EXIT_SUCCESS


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

_COMMANDS = {
    "generate": _cmd_generate,
    "verify": _cmd_verify,
    "info": _cmd_info,
    "version": _cmd_version,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, dispatch to a command, and return a PRD-8 exit code.

    Exceptions raised by the underlying, independently-callable APIs
    are caught here and mapped to PRD 8's exit codes; unrecognized
    exceptions are treated as general errors (exit code 1), with
    ``--debug`` re-raising them so a full traceback reaches stderr.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    # argparse itself calls sys.exit(2) for malformed arguments, which
    # already matches PRD 8's exit code 2 for "invalid command-line
    # arguments" -- no extra handling is needed for that class of error.

    handler = _COMMANDS[args.command]
    try:
        return handler(args)
    except _CliError as exc:
        _error(str(exc), stream=sys.stderr)
        return exc.exit_code
    except InvalidDigestError as exc:
        _error(str(exc), stream=sys.stderr)
        return _EXIT_INVALID_INPUT
    except DestinationExistsError as exc:
        _error(f"{exc} (use --overwrite to replace it)", stream=sys.stderr)
        return _EXIT_INVALID_ARGUMENTS
    except EmissionLimitExceeded as exc:
        _error(str(exc), stream=sys.stderr)
        return _EXIT_LIMIT_EXCEEDED
    except OSError as exc:
        _error(f"unreadable input or output: {exc}", stream=sys.stderr)
        return _EXIT_INVALID_INPUT
    except Exception as exc:  # noqa: BLE001 - deliberate top-level safety net
        # PRD 8: "Normal CLI errors must be concise, actionable,
        # traceback-free. --debug may add diagnostic detail." Exit code
        # is always 1 here regardless of --debug; --debug only adds the
        # traceback below.
        _error(f"internal error: {exc}", stream=sys.stderr)
        if getattr(args, "debug", False):
            traceback.print_exc(file=sys.stderr)
        return _EXIT_GENERAL_ERROR


def _entry_point() -> NoReturn:
    sys.exit(main())


if __name__ == "__main__":
    _entry_point()
