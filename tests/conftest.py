"""Shared test configuration — ensures project root is on the Python path."""

import sys
from pathlib import Path

# Add project root to path so `from src.*` imports work from tests/
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
