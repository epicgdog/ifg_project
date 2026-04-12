from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root (containing the ``src`` package) is on ``sys.path``
# so tests can ``from src.x import y`` regardless of where pytest is invoked.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
