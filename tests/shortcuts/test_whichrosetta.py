import os
import subprocess
from unittest.mock import patch

import pytest

from tests.conftest import github_rosetta_test

# Assuming 'whichrosetta' is an installed command available in the PATH.
# If not, you need to adjust the PATH or ensure the command is available during testing.


@pytest.mark.integration
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_integration_whichrosetta_success(tmp_path, monkeypatch):
    """
    Test that 'whichrosetta' successfully finds the Rosetta binary when it exists.
    """
    # Create a temporary directory to act as ROSETTA_BIN
    temp_dir = tmp_path

    # Create a mock binary file
    binary_name = "rosetta_scripts.linuxgccrelease"
    binary_path = temp_dir / binary_name
    binary_path.write_text("# Mock Rosetta binary")

    # Set the ROSETTA_BIN environment variable to the temp directory
    monkeypatch.setenv("ROSETTA_BIN", str(temp_dir))

    # Patch sys.platform to 'linux'
    with patch("sys.platform", "linux"):
        # Invoke the whichrosetta command
        result = subprocess.run(
            ["whichrosetta", "rosetta_scripts"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),  # Use the modified environment
        )

        # Check that the command was successful
        assert result.returncode == 0
        expected_output = f"{binary_path}\n"
        assert result.stdout == expected_output
        assert result.stderr == ""


@pytest.mark.integration
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_dockerized_whichrosetta_success(tmp_path, monkeypatch):
    """
    Test that 'whichrosetta' successfully finds the Rosetta binary in a dockerized environment.
    """
    # Create a temporary directory to act as the directory containing the binary
    temp_dir = tmp_path

    # Create a mock binary file
    binary_name = "rosetta_scripts"
    binary_path = temp_dir / binary_name
    binary_path.write_text("# Mock Rosetta binary")

    # Make the binary executable
    os.chmod(str(binary_path), 0o755)

    # Set the PATH environment variable to include the temp directory
    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{temp_dir}{os.pathsep}{original_path}")

    # Remove any ROSETTA-related environment variables
    for key in list(os.environ.keys()):
        if "ROSETTA" in key:
            monkeypatch.delenv(key, raising=False)

    # Patch sys.platform to 'linux'
    with patch("sys.platform", "linux"):
        # Invoke the whichrosetta command
        result = subprocess.run(
            ["whichrosetta", "rosetta_scripts"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

        # Check that the command was successful
        print(result.stderr)
        print(result.stdout)
        assert result.returncode == 0
        expected_output = f"{binary_path}\n"
        assert result.stdout == expected_output
        assert result.stderr == ""


@pytest.mark.integration
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_integration_whichrosetta_not_found(tmp_path, monkeypatch):
    """
    Test that 'whichrosetta' correctly reports when the Rosetta binary is not found.
    """
    # Create a temporary directory to act as ROSETTA_BIN
    temp_dir = tmp_path

    # Set the ROSETTA_BIN environment variable to the temp directory
    monkeypatch.setenv("ROSETTA_BIN", str(temp_dir))

    # Patch sys.platform to 'linux'
    with patch("sys.platform", "linux"):
        # Invoke the whichrosetta command
        result = subprocess.run(
            ["whichrosetta", "rosetta_scripts"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

        # Check that the command failed
        assert result.returncode != 0
        expected_error = "rosetta_scripts binary not found in the specified paths.\n"
        assert result.stdout == ""
        assert expected_error in result.stderr
