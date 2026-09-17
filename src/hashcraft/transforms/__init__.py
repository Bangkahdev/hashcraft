"""Candidate transformation stages: case, leetspeak, symbols (PRD 4.3).

Each module here exposes pure, generator-based ``str -> Iterator[str]``
transforms. They deliberately do not know *where* in the pipeline they
run (per-token vs. per-joined-candidate) -- that orchestration is the
responsibility of ``generation/generator.py``, which assembles the
normative pipeline order from PRD section 4:

    normalized tokens -> ordered combinations -> case variants
        -> leetspeak variants -> separators -> symbol variants
        -> length filter -> structural deduplication -> emit

Keeping these modules pipeline-order-agnostic keeps them independently
unit-testable, per PRD section 10 ("Tests must cover ... all
transformations").
"""
