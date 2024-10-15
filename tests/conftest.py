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
import shutil
import warnings
from typing import List

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

    result = subprocess.run(
        ["whichrosetta", "rosetta_scripts"], capture_output=True, text=True)
    # Check that the command was successful
    has_rosetta_installed = "rosetta_scripts" in result.stdout
    warnings.warn(UserWarning(
        f"Rosetta Installed: {has_rosetta_installed} - {result.stdout}"))
    return not has_rosetta_installed


NO_NATIVE_ROSETTA = no_rosetta()


def github_rosetta_test():
    return os.environ.get("GITHUB_ROSETTA_TEST", "NO") == "YES"


# Determine if running in GitHub Actions
is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

has_docker = shutil.which("docker") is not None

GITHUB_CONTAINER_ROSETTA_TEST = os.environ.get(
    "GITHUB_CONTAINER_ROSETTA_TEST", "NO") == "YES"
