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


def pytest_collection_modifyitems(items: list[Item]):
    for item in items:
        if "spark" in item.nodeid:
            item.add_marker(pytest.mark.spark)
        elif "_int_" in item.nodeid:
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def unit_test_mocks(monkeypatch: None):
    """Include Mocks here to execute all commands offline and fast."""
    pass


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
