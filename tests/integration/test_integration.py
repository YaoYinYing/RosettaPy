import os
import subprocess
from unittest import mock

import pytest

from ..conftest import github_rosetta_test


@pytest.mark.integration
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_whichrosetta_integration(mock_rosetta_bin, monkeypatch):
    """
    Test that 'whichrosetta' can find and execute a mock Rosetta binary.
    """

    # Set the ROSETTA_BIN environment variable to the temporary directory
    monkeypatch.setenv("ROSETTA_BIN", str(os.path.dirname(mock_rosetta_bin)))

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
        expected_output = f"{mock_rosetta_bin}\n"
        assert result.stdout == expected_output
        assert result.stderr == ""

        # Now, execute the found binary to ensure it works
        result_binary = subprocess.run(
            [str(mock_rosetta_bin)],
            capture_output=True,
            text=True,
        )
        assert result_binary.returncode == 0
        assert result_binary.stdout.strip() == "Mock Rosetta binary"
