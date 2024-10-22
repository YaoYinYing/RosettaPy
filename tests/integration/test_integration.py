import os
import subprocess
from unittest import mock

import pytest

from ..conftest import github_rosetta_test


@pytest.mark.integration
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_whichrosetta_integration(tmp_path, monkeypatch):
    """
    Test that 'whichrosetta' can find and execute a mock Rosetta binary.
    """
    # Create a mock binary file in the temporary directory
    binary_name = "rosetta_scripts.linuxgccrelease"
    binary_path = tmp_path / binary_name
    binary_content = '#!/bin/bash\necho "Mock Rosetta binary"'
    binary_path.write_text(binary_content)

    # Make the mock binary executable
    os.chmod(binary_path, 0o755)

    # Set the ROSETTA_BIN environment variable to the temporary directory
    monkeypatch.setenv("ROSETTA_BIN", str(tmp_path))

    # Patch sys.platform to 'linux' to simulate a Linux environment
    with mock.patch("sys.platform", "linux"):
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

        # Now, execute the found binary to ensure it works
        result_binary = subprocess.run(
            [str(binary_path)],
            capture_output=True,
            text=True,
        )
        assert result_binary.returncode == 0
        assert result_binary.stdout.strip() == "Mock Rosetta binary"
