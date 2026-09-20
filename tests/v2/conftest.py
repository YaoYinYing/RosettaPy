"""Fixtures for the v2 kernel test package."""

from __future__ import annotations

import pytest

from tests.v2._helpers import CORE_ROOT, ROSETTA_ROOT, imported_modules, python_files


@pytest.fixture(scope="module")
def core_imports() -> dict[str, set[str]]:
    """Map each ``core`` module file name to the modules it imports."""
    return {path.name: imported_modules(path) for path in python_files(CORE_ROOT)}


@pytest.fixture(scope="module")
def rosetta_imports() -> dict[str, set[str]]:
    """Map each ``rosetta`` module file name to the modules it imports."""
    return {path.name: imported_modules(path) for path in python_files(ROSETTA_ROOT)}
