"""Shared pytest configuration: make the root modules importable.

The project is a flat collection of top-level modules (``zone.py``,
``network.py``, ...), not an installable package, so the repository root
must be on ``sys.path`` for ``tests/`` to import them regardless of the
directory pytest is invoked from.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MAPS_DIR = ROOT / "maps"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "invalid"
