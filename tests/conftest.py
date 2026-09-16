"""Shared pytest configuration.

Ensures ``src/`` is importable even if the package has not been
installed (e.g. via ``pip install -e .``) -- this mirrors the
``[tool.pytest.ini_options] pythonpath`` setting in ``pyproject.toml``
as a defensive fallback for tooling that does not read it.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
