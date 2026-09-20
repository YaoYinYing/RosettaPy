"""Architectural boundary tests for the v2 kernel.

These tests enforce the dependency invariants of ``docs/v2/ARCHITECTURE.md`` and
``docs/v2/IMPLEMENTATION_CONTRACT.md``. They use static import analysis so that a
forbidden dependency fails the suite even when it is not installed, and so the
boundary can be checked without importing the modules under test.
"""

from __future__ import annotations

import ast

import pytest

from tests.v2._helpers import (
    CORE_ROOT,
    PACKAGE_ROOT,
    ROSETTA_ROOT,
    imported_modules,
    python_files,
)

FORBIDDEN_IN_CORE = (
    "rosetta",
    "node",
    "executors",
    "launchers",
    "schedulers",
    "workflows",
    "analyser",
    "app",
    "utils",
    "docker",
    "mpi",
    "wsl",
    "slurm",
    "subprocess",
    "socket",
    "shutil",
    "joblib",
)

FORBIDDEN_IN_ROSETTA = (
    "executors",
    "launchers",
    "schedulers",
    "workflows",
    "node",
    "utils",
    "docker",
    "mpi",
    "wsl",
    "slurm",
    "subprocess",
    "socket",
    "shutil",
    "joblib",
)


def _offends(module: str, forbidden: str) -> bool:
    parts = module.split(".")
    return any(part == forbidden for part in parts)


class TestCoreBoundary:
    def test_core_has_source_files(self):
        assert python_files(CORE_ROOT)

    def test_core_imports_are_visible_to_the_boundary_check(self, core_imports):
        """Guard against a detector that silently resolves nothing."""
        assert core_imports
        assert any("RosettaPy.core" in module for modules in core_imports.values() for module in modules)

    def test_core_imports_no_forbidden_module(self, core_imports):
        offenders = [
            f"{name}: {module}"
            for name, modules in core_imports.items()
            for module in sorted(modules)
            for forbidden in FORBIDDEN_IN_CORE
            if _offends(module, forbidden)
        ]
        assert offenders == []

    def test_core_does_not_import_the_legacy_module(self, core_imports):
        offenders = [
            f"{name}: {module}"
            for name, modules in core_imports.items()
            for module in modules
            if "_legacy_rosetta" in module
        ]
        assert offenders == []

    def test_core_defines_the_executor_protocol(self):
        from RosettaPy.core import Executor

        assert Executor is not None


class TestRosettaBoundary:
    def test_rosetta_layer_has_source_files(self):
        assert python_files(ROSETTA_ROOT)

    def test_rosetta_imports_are_visible_to_the_boundary_check(self, rosetta_imports):
        """Guard against a detector that silently resolves nothing."""
        assert rosetta_imports
        assert any("RosettaPy.core" in module for modules in rosetta_imports.values() for module in modules)

    def test_relative_imports_resolve_to_the_package_root(self):
        resolved = imported_modules(ROSETTA_ROOT / "invocation.py")
        assert "RosettaPy.core.errors" in resolved
        assert "RosettaPy.rosetta.binary" in resolved

    def test_rosetta_compiler_imports_no_concrete_executor(self, rosetta_imports):
        offenders = [
            f"{name}: {module}"
            for name, modules in rosetta_imports.items()
            for module in sorted(modules)
            for token in FORBIDDEN_IN_ROSETTA
            if _offends(module, token)
        ]
        assert offenders == []

    def test_compilation_module_runs_no_process(self, rosetta_imports):
        offenders = [
            f"{name}: {module}"
            for name, modules in rosetta_imports.items()
            if name == "compiler.py"
            for module in modules
            if _offends(module, "subprocess") or _offends(module, "socket") or _offends(module, "shutil")
        ]
        assert offenders == []

    def test_rosetta_layer_imports_only_core_and_stdlib(self, rosetta_imports):
        """
        The Rosetta layer may import ``core`` and the standard library, nothing
        else from the package: no sibling RosettaPy subpackage is reached into.
        """
        offenders: list[str] = []
        for name, modules in rosetta_imports.items():
            for module in modules:
                parts = module.split(".")
                if not parts or parts[0] != "RosettaPy":
                    continue
                if parts[1] in {"core", "rosetta"}:
                    continue
                offenders.append(f"{name}: {module}")
        assert offenders == []

    def test_rosetta_layer_does_not_import_the_legacy_module(self, rosetta_imports):
        offenders = [
            f"{name}: {module}"
            for name, modules in rosetta_imports.items()
            for module in modules
            if "_legacy_rosetta" in module
        ]
        assert offenders == []


class TestBoundaryDetectorIsEffective:
    """
    Negative controls proving the boundary checks are not vacuous.

    A boundary assertion that cannot fail is worse than no assertion, so these
    tests verify that the detector reports a known-bad import shape.
    """

    def test_detector_flags_a_forbidden_relative_import_in_core(self, tmp_path):
        fixture = CORE_ROOT / "_boundary_probe.py"
        fixture.write_text("from ..node import Native\nfrom .task import TaskSpec\n", encoding="utf-8")
        try:
            resolved = imported_modules(fixture)
            assert "RosettaPy.node" in resolved
            assert _offends("RosettaPy.node", "node")
            assert not _offends("RosettaPy.core.task", "node")
        finally:
            fixture.unlink()

    def test_detector_flags_a_forbidden_absolute_import(self, tmp_path):
        fixture = CORE_ROOT / "_boundary_probe.py"
        fixture.write_text("import subprocess\nfrom RosettaPy.utils import task\n", encoding="utf-8")
        try:
            imported_modules(fixture)
            assert _offends("subprocess", "subprocess")
            assert _offends("RosettaPy.utils", "utils")
        finally:
            fixture.unlink()

    def test_legacy_module_would_violate_the_core_boundary(self):
        """The parked 1.x module must stay outside ``core`` for a reason."""
        resolved = imported_modules(PACKAGE_ROOT / "_legacy_rosetta.py")
        assert any(_offends(module, "node") for module in resolved)
        assert any(_offends(module, "subprocess") or "joblib" in module for module in resolved)


_BACKEND_IDENTITIES = {"native", "docker", "mpi", "slurm", "wsl"}
"""Backend identity strings the kernel must never switch on."""


class TestNoBackendBranching:
    def test_kernel_does_not_branch_on_executor_identity(self):
        """
        The kernel must not restore the old pattern by switching on a backend
        type or identity string.
        """
        suspicious: list[str] = []
        for root in (CORE_ROOT, ROSETTA_ROOT):
            for path in python_files(root):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Compare):
                        names = [
                            child.id
                            for child in ast.walk(node)
                            if isinstance(child, ast.Name) and child.id in {"isinstance", "type"}
                        ]
                        for child in ast.walk(node):
                            if not isinstance(child, ast.Constant) or not isinstance(child.value, str):
                                continue
                            if child.value in _BACKEND_IDENTITIES and names:
                                suspicious.append(f"{path.name}: {ast.dump(node)[:80]}")
        assert suspicious == []

    def test_kernel_does_not_reference_container_or_scheduler_tokens(self):
        """No kernel source file may name a backend implementation detail."""
        forbidden_tokens = ("RosettaContainer", "MpiNode", "WslWrapper", "Native(", "slurm", "SLURM_")
        offenders: list[str] = []
        for root in (CORE_ROOT, ROSETTA_ROOT):
            for path in python_files(root):
                text = path.read_text(encoding="utf-8")
                offenders.extend(f"{path.name}: {token}" for token in forbidden_tokens if token in text)
        assert offenders == []


class TestPackageLayout:
    def test_core_package_exists_at_the_documented_location(self):
        assert (PACKAGE_ROOT / "core" / "__init__.py").is_file()

    def test_rosetta_layer_exists_at_the_documented_location(self):
        assert (PACKAGE_ROOT / "rosetta" / "__init__.py").is_file()

    def test_legacy_module_is_parked_outside_the_v2_layer(self):
        assert (PACKAGE_ROOT / "_legacy_rosetta.py").is_file()
        assert not (PACKAGE_ROOT / "rosetta.py").exists()

    @pytest.mark.parametrize(
        "module",
        ["core.artifact", "core.errors", "core.executor", "core.result", "core.task"],
    )
    def test_core_module_is_importable(self, module):
        __import__(f"RosettaPy.{module}")

    @pytest.mark.parametrize("module", ["rosetta.binary", "rosetta.invocation", "rosetta.compiler"])
    def test_rosetta_module_is_importable(self, module):
        __import__(f"RosettaPy.{module}")

    def test_deferred_milestones_are_not_implemented(self):
        """PR 2 must not create the later executor and scheduler packages."""
        for absent in ("executors", "launchers", "schedulers", "workflows"):
            assert not (PACKAGE_ROOT / absent).exists(), f"{absent} belongs to a later milestone"


class TestCompatibilityOfTheLegacyRename:
    def test_public_facade_still_resolves(self):
        from RosettaPy import MpiNode, Rosetta, RosettaScriptsVariableGroup

        assert Rosetta is not None
        assert MpiNode is not None
        assert RosettaScriptsVariableGroup is not None

    def test_legacy_module_keeps_its_symbols(self):
        from RosettaPy._legacy_rosetta import (  # noqa: F401
            IgnoreMissingFileWarning,
            RosettaCmdTask,
            RosettaScriptsVariableGroup,
        )

        assert RosettaCmdTask is not None
        assert IgnoreMissingFileWarning is not None
        assert RosettaScriptsVariableGroup is not None

    def test_v2_layer_does_not_leak_the_legacy_api(self):
        """Importing ``RosettaPy.rosetta`` must not pull in the 1.x facade."""
        import sys

        for name in [key for key in sys.modules if key.startswith("RosettaPy._legacy_rosetta")]:
            del sys.modules[name]
        __import__("RosettaPy.rosetta")
        assert not any(key.startswith("RosettaPy._legacy_rosetta") for key in sys.modules)
