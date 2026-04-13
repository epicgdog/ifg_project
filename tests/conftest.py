"""
Pytest configuration and shared fixtures for the test suite.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


# Run with: pytest tests/ -v
