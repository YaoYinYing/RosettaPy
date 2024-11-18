#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""
This is a configuration file for pytest containing customizations and fixtures.

In VSCode, Code Coverage is recorded in config.xml. Delete this file to reset reporting.
"""

from __future__ import annotations

import os
import platform
import shutil
import warnings

import pytest
from _pytest.nodes import Item


def create_mock_rosetta_bin(tmp_path, binary_name):
    # Create a mock binary file in the temporary directory
    binary_path = tmp_path / binary_name
    binary_path.write_text('#!/bin/bash\necho "Mock Rosetta binary"')

    # Make the mock binary executable
    os.chmod(binary_path, 0o755)
    return str(binary_path)


def _make_rosetta_fixture(binary_suffix: str):
    """Factory function to create Rosetta binary fixtures.

    Args:
        binary_suffix: Suffix for the Rosetta binary name
    """

    @pytest.fixture
    def _fixture(tmp_path):
        return create_mock_rosetta_bin(tmp_path, f"rosetta_scripts{binary_suffix}")

    return _fixture


# Create fixtures using the factory
mock_rosetta_bin_container = _make_rosetta_fixture("")  # returns 'rosetta_scripts'
mock_rosetta_bin = _make_rosetta_fixture(".linuxgccrelease")  # returns 'rosetta_scripts.linuxgccrelease'
mock_rosetta_mpi_bin = _make_rosetta_fixture(".mpi.linuxgccrelease")  # returns 'rosetta_scripts.mpi.linuxgccrelease'
mock_rosetta_static_bin = _make_rosetta_fixture(
    ".static.linuxgccrelease"
)  # returns 'rosetta_scripts.static.linuxgccrelease'
mock_rosetta_mac_bin = _make_rosetta_fixture(".default.macosclangrelease")
mock_rosetta_mac_mpi_bin = _make_rosetta_fixture(".mpi.macosclangrelease")


def pytest_collection_modifyitems(items: list[Item]):
    for item in items:
        if "spark" in item.nodeid:
            item.add_marker(pytest.mark.spark)
        elif "_int_" in item.nodeid:
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def unit_test_mocks(monkeypatch: None):
    """Include Mocks here to execute all commands offline and fast."""


def no_rosetta():
    import subprocess

    result = subprocess.run(["whichrosetta", "rosetta_scripts"], capture_output=True, text=True)
    # Check that the command was successful
    has_rosetta_installed = "rosetta_scripts" in result.stdout
    warnings.warn(UserWarning(f"Rosetta Installed: {has_rosetta_installed} - {result.stdout}"))
    return not has_rosetta_installed


NO_NATIVE_ROSETTA = no_rosetta()


def github_rosetta_test():
    return os.environ.get("GITHUB_ROSETTA_TEST", "NO") == "YES"


# Determine if running in GitHub Actions
is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

has_docker = shutil.which("docker") is not None

# Github Actions, Ubuntu-latest with Rosetta Docker container enabled
GITHUB_CONTAINER_ROSETTA_TEST = os.environ.get("GITHUB_CONTAINER_ROSETTA_TEST", "NO") == "YES"

WINDOWS_WITH_WSL = platform.system() == "Windows" and shutil.which("wsl") is not None


@pytest.fixture(
    params=[
        pytest.param(
            "docker",
            marks=pytest.mark.skipif(
                not GITHUB_CONTAINER_ROSETTA_TEST, reason="Skipping docker tests in GitHub Actions"
            ),
        ),
        pytest.param(
            None,
            marks=pytest.mark.skipif(NO_NATIVE_ROSETTA, reason="No Rosetta Installed."),
        ),
    ]
)
def test_node_hint(request):
    return request.param
