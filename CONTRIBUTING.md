# Contributing to Hashcraft

Thanks for your interest in contributing. Hashcraft is a small,
deliberately scoped tool (see the PRD's "Non-goals", section 11), so
the bar for new features is "does this fit the documented v0.1/v0.2+
scope" rather than "is this a good idea in general" -- please open an
issue to discuss any new feature before writing code for it.

## Development setup

```bash
git clone https://github.com/Bangkahdev/hashcraft.git
cd hashcraft
python3 -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

This installs Hashcraft itself (editable) plus `pytest`, `ruff`, and
`mypy`.

## Running the checks locally

Run all three before opening a pull request -- they're exactly what
CI runs (`.github/workflows/ci.yml`):

```bash
ruff check .
mypy src
pytest
```

`pytest` picks up `src/` automatically via the `pythonpath` setting in
`pyproject.toml`, so you don't need to reinstall after every change
when using an editable install.

### Packaging sanity check

If you're touching `pyproject.toml`, packaging metadata, or the
`src/` layout itself, also verify the package builds and installs
cleanly (this mirrors the CI "packaging" job):

```bash
pip install build
python -m build
python -m venv /tmp/hashcraft-clean-check
/tmp/hashcraft-clean-check/bin/pip install dist/*.whl
/tmp/hashcraft-clean-check/bin/hashcraft version
```

## The invariants a change must not break

These come directly from the PRD and are covered by the test suite in
`tests/`. If a change requires breaking one of these, it needs to be
discussed and the PRD/README updated accordingly -- these are not
incidental implementation details:

- **Canonical generation contract (PRD section 4).** For a fixed
  program version, normalized inputs, and configuration, generated
  candidates and their order must be identical across Linux, Windows,
  and macOS, and across repeated runs. Anything that introduces
  platform-dependent ordering (e.g. relying on unordered `dict`/`set`
  iteration for anything user-visible, or on OS-specific sort
  behavior) breaks this.
- **No full candidate-space materialization (PRD section 4).** Every
  stage of the generation pipeline (`hashcraft.generation.*`) must
  stay a generator. Don't introduce a `list(...)`, a `set`, or an
  equivalent full-collection buffer of the *candidate output* -- small,
  explicitly bounded pools (e.g. one token's case/leetspeak variants)
  are fine and already used; the *combinatorial output* across tokens
  and separators is not.
- **The two-pass preflight (PRD section 5).** The filter-aware
  preflight count and the real generation pass must run the *same*
  pipeline (`generation.generator.iter_candidates`) so the count is
  exact, not an approximation that could later disagree with what
  generation actually emits.
- **Atomic file output (PRD section 5).** File output must always go
  through a sibling temporary file, replaced onto the destination only
  on success (`os.replace`), with the temp file discarded on any
  failure -- see `output/text.py` and its tests for the exact contract.
- **The clean `--stdout` contract (PRD section 6).** `generate
  --stdout` must never write anything to standard output except
  candidates, one per line. Status, warnings, and errors always go to
  stderr.
- **The exit-code table (PRD section 8).** 0 success/match, 1 general
  error, 2 invalid arguments, 3 invalid input, 4 no match, 5 a
  resource limit was hit. If you add a new failure mode, map it to one
  of these -- don't invent a new code without discussing it first.
- **Local-only operation (PRD section 3).** No telemetry, analytics,
  remote candidate submission, external API calls, or online
  authentication attempts, ever.
- **Multiprocessing worker safety (PRD v2 section B).** Any function
  passed to a `multiprocessing.Pool` (see `hashing/verifier.py`) must
  stay a plain, module-level function taking only picklable arguments
  (strings, lists of strings, etc.) -- never a closure, a bound
  method, or an object holding an open file handle or a live
  `HashAlgorithm` instance. `spawn`, the default start method on
  Windows and macOS, starts a fresh interpreter per worker and pickles
  the callable and its arguments to get there; code that only works
  under Linux's `fork` will silently break on the other two platforms.

## Adding or changing behavior

- **Every module stays an independently callable Python API** (PRD
  section 9): `hashcraft.cli` is a thin adapter that wires the
  `sources`, `generation`, `hashing`, and `output` packages together
  and maps their exceptions to exit codes -- it should not gain new
  generation/hashing/output logic of its own.
- **Type hints are required** on new public functions and classes;
  `mypy src` must pass.
- **Add tests alongside the change**, in the matching `tests/`
  file (one test module per `src/` module, e.g.
  `hashcraft.transforms.case` -> `tests/test_transforms_case.py`).
  New CLI-visible behavior needs a `tests/test_cli.py` case exercising
  it through `cli.main(...)`, not just the underlying function.
- **Document PRD-derived assumptions inline.** Several modules
  already contain `NOTE`/docstring call-outs for places where the PRD
  underspecifies behavior (multi-word case/leetspeak combination, the
  `--warn-threshold` default, etc.). If you make a similar judgment
  call, document it the same way, at the point of the decision, so a
  reviewer can evaluate it against the PRD directly.
- **Update `CHANGELOG.md`** under an "Unreleased" heading for any
  user-visible change (new flag, behavior change, bug fix).

## Reporting bugs

Please open a GitHub issue with:

- the exact command line you ran (or the Python API call, if using
  Hashcraft as a library);
- what you expected vs. what happened;
- your Hashcraft version (`hashcraft version`), Python version, and OS.

For suspected **security** issues, see `SECURITY.md` instead of
opening a public issue.

## Pull requests

1. Fork and branch from `main`.
2. Make your change, with tests, following the invariants above.
3. Run `ruff check .`, `mypy src`, and `pytest` locally.
4. Add a `CHANGELOG.md` entry under "Unreleased".
5. Open the PR describing *what* changed and *why*, and which PRD
   section(s) it relates to, if any.

By contributing, you agree your contribution is licensed under this
project's MIT license (see `LICENSE`).
