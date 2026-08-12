"""Pytest configuration for the Leibniz engine test suite."""

import sys
import os

# Ensure leibniz/ is on path
PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

# Allow `import leibniz` / `import api` / `import training`
# Tests use explicit relative imports, so this is belt-and-suspenders.
