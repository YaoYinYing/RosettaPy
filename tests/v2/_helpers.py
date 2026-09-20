"""Shared helpers for the v2 kernel unit tests."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_NAME = "RosettaPy"
PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / PACKAGE_NAME
CORE_ROOT = PACKAGE_ROOT / "core"
ROSETTA_ROOT = PACKAGE_ROOT / "rosetta"


def python_files(root: Path) -> list[Path]:
    """Return every Python source file under ``root`` in a deterministic order."""
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def imported_modules(path: Path) -> set[str]:
    """
    Return the package-root-resolved set of modules imported by ``path``.

    Resolution is relative to the RosettaPy package root, so ``from ..core.task
    import X`` is recorded as ``RosettaPy.core.task`` and can be compared against
    an absolute import of the same module. Analysis is static: the v2 boundary
    invariants must hold without importing the modules under test, so a boundary
    test still runs when a forbidden dependency is not installed.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # The module containing this file, expressed as a package path.
                parts = list(path.relative_to(PACKAGE_ROOT).parent.parts)
                # One level up per extra dot beyond the implicit current package.
                keep = len(parts) - (node.level - 1)
                prefix = PACKAGE_NAME if keep <= 0 else f"{PACKAGE_NAME}.{'.'.join(parts[:keep])}"
                modules.add(f"{prefix}.{node.module}" if node.module else prefix)
            elif node.module:
                modules.add(node.module)
    return modules
