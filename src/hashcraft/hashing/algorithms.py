"""Pluggable digest algorithms behind a ``HashAlgorithm`` protocol.

v1 (PRD 7) supported SHA-256 only. v2 (PRD v2 section A) expands this
into a small strategy-pattern registry -- ``md5``, ``sha1``,
``sha256``, ``sha512``, and ``blake2b`` -- all implemented via
Python's standard-library ``hashlib``, so this stays within the
zero-runtime-dependency constraint (PRD v2 section 3.1). Adding
another ``hashlib``-backed algorithm is a one-line registration via
``register_algorithm`` below; ``hashing/verifier.py`` never needs to
change, since it depends only on the ``HashAlgorithm`` protocol plus
``get_algorithm`` / ``supported_algorithm_names`` -- exactly the
"pluggable strategy pattern where new algorithms can be easily
registered without changing the verifier loop" PRD v2 section A asks
for.

Note on categorization: the v2 PRD describes ``blake2b`` as a "fast
checksum / non-cryptographic" algorithm. That's not accurate --
BLAKE2b is itself a cryptographic hash function (a faster relative of
the SHA-3 finalists), not a mere checksum like CRC32. It's included
here exactly as requested regardless; this note exists only so the
inaccurate categorization doesn't propagate into user-facing docs.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Protocol


class HashAlgorithm(Protocol):
    """The minimal contract a digest algorithm must satisfy for ``verify``."""

    name: str
    digest_hex_length: int

    def hexdigest(self, data: bytes) -> str:
        """Return the lowercase hex digest of ``data``."""
        ...


class _Digest(Protocol):
    """Structural type for a ``hashlib``-style digest object.

    Used instead of referencing ``hashlib``'s private, underscore-named
    ``_Hash`` stub type directly: that name is an implementation detail
    of typeshed's ``hashlib`` stub (and doesn't even exist as a real
    runtime attribute -- ``hashlib.md5(b"")`` actually returns a
    ``_hashlib.HASH`` instance), so pinning to it would be fragile
    across typeshed/mypy versions. This ``Protocol`` instead says
    exactly what ``_StdlibHashAlgorithm.hexdigest`` actually needs --
    an object with a zero-argument ``hexdigest() -> str`` method --
    which every ``hashlib`` constructor's return value satisfies
    structurally, regardless of its concrete/private type name.
    """

    def hexdigest(self) -> str:
        """Return the lowercase hex digest already computed so far."""
        ...


class _StdlibHashAlgorithm:
    """A ``HashAlgorithm`` backed by one ``hashlib`` constructor.

    This is the "pluggable strategy" PRD v2 section A asks for: every
    currently-supported algorithm is one instance of this class,
    registered by name in ``_ALGORITHMS`` below. ``hexdigest`` is the
    only method the verifier ever calls, so adding a brand-new
    algorithm needs nothing more than a ``hashlib``-compatible
    constructor and its output length in hex characters -- see
    ``register_algorithm``.
    """

    __slots__ = ("name", "digest_hex_length", "_factory")

    def __init__(
        self,
        name: str,
        factory: Callable[[bytes], _Digest],
        digest_hex_length: int,
    ) -> None:
        self.name = name
        self.digest_hex_length = digest_hex_length
        self._factory = factory

    def hexdigest(self, data: bytes) -> str:
        return self._factory(data).hexdigest()


_ALGORITHMS: dict[str, HashAlgorithm] = {
    "md5": _StdlibHashAlgorithm("md5", hashlib.md5, 32),
    "sha1": _StdlibHashAlgorithm("sha1", hashlib.sha1, 40),
    "sha256": _StdlibHashAlgorithm("sha256", hashlib.sha256, 64),
    "sha512": _StdlibHashAlgorithm("sha512", hashlib.sha512, 128),
    # hashlib.blake2b's default digest_size is 64 bytes -> 128 hex chars.
    "blake2b": _StdlibHashAlgorithm("blake2b", hashlib.blake2b, 128),
}


def register_algorithm(algorithm: HashAlgorithm) -> None:
    """Register (or replace) a ``HashAlgorithm`` by its ``.name``.

    Exists so a new algorithm -- built-in, or supplied by a caller of
    the Python API -- can be added without editing ``_ALGORITHMS``
    directly and without touching ``hashing/verifier.py`` at all, per
    PRD v2 section A's "pluggable strategy pattern" requirement.

    Note: ``hashing.verifier.verify``'s parallel path (``jobs`` > 1)
    reconstructs the algorithm by name inside each worker process (see
    that module's docstring), so an algorithm must be registered here
    -- via this function, at import time, before the pool starts -- to
    be usable in parallel mode; an ad hoc ``HashAlgorithm`` object that
    was never registered only works with ``jobs=1``.
    """
    _ALGORITHMS[algorithm.name] = algorithm


def supported_algorithm_names() -> tuple[str, ...]:
    """Names of every currently-registered algorithm, sorted.

    Used by ``cli.py`` to build ``--algorithm``'s ``choices=`` so the
    CLI's accepted values and this registry can never drift apart.
    """
    return tuple(sorted(_ALGORITHMS))


def get_algorithm(name: str) -> HashAlgorithm:
    """Look up a ``HashAlgorithm`` by its ``--algorithm`` name.

    Raises ``ValueError`` for any unregistered name. In normal CLI use
    this is unreachable with a bad value, since ``--algorithm`` is
    already constrained by ``argparse choices=supported_algorithm_names()``;
    it matters for direct Python API callers and is mapped by
    ``cli.py`` to exit code 2 (invalid command-line arguments) if it
    somehow surfaces there anyway.
    """
    try:
        return _ALGORITHMS[name]
    except KeyError as exc:
        supported = ", ".join(supported_algorithm_names())
        raise ValueError(
            f"unsupported algorithm {name!r}; supported: {supported}"
        ) from exc
