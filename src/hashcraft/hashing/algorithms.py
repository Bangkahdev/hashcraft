"""Pluggable digest algorithms behind a ``HashAlgorithm`` protocol (PRD 7).

v0.1 supports SHA-256 only, but per PRD 7 the verifier is written
against a ``HashAlgorithm`` protocol "so later algorithms can be added
without changing the verifier." Additional algorithms (deferred to
v0.2+ alongside TOML configuration, per PRD 2) can be added by
implementing this protocol and registering an instance in
``_ALGORITHMS`` below -- ``hashing/verifier.py`` never needs to change.
"""

from __future__ import annotations

import hashlib
from typing import Protocol


class HashAlgorithm(Protocol):
    """The minimal contract a digest algorithm must satisfy for ``verify``."""

    name: str
    digest_hex_length: int

    def hexdigest(self, data: bytes) -> str:
        """Return the lowercase hex digest of ``data``."""
        ...


class Sha256Algorithm:
    """SHA-256 -- the only algorithm v0.1 supports (PRD 7)."""

    name = "sha256"
    digest_hex_length = 64  # 256 bits / 4 bits per hex digit

    def hexdigest(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


_ALGORITHMS: dict[str, HashAlgorithm] = {
    "sha256": Sha256Algorithm(),
}


def get_algorithm(name: str) -> HashAlgorithm:
    """Look up a ``HashAlgorithm`` by its ``--algorithm`` name.

    Raises ``ValueError`` for anything other than ``"sha256"`` in
    v0.1. Mapping that to a specific CLI exit code is ``cli.py``'s
    job -- PRD 8 assigns exit code 2 to invalid command-line arguments
    in general, which is the natural fit for an unsupported
    ``--algorithm`` value.
    """
    try:
        return _ALGORITHMS[name]
    except KeyError as exc:
        supported = ", ".join(sorted(_ALGORITHMS))
        raise ValueError(
            f"unsupported algorithm {name!r}; v0.1 supports: {supported}"
        ) from exc
