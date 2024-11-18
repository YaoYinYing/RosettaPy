import os
import shutil
import subprocess
import sys
import warnings
from unittest.mock import patch

import pytest

from tests.conftest import github_rosetta_test

# Assuming 'whichrosetta' is an installed command available in the PATH.
# If not, you need to adjust the PATH or ensure the command is available during testing.


@pytest.mark.integration
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_integration_whichrosetta_success(mock_rosetta_bin, monkeypatch):
    """
    Test that 'whichrosetta' successfully finds the Rosetta binary when it exists.
    """

    # Set the ROSETTA_BIN environment variable to the temp directory
    monkeypatch.setenv("ROSETTA_BIN", str(os.path.dirname(mock_rosetta_bin)))

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
        expected_output = f"{mock_rosetta_bin}\n"
        assert result.stdout == expected_output
        assert result.stderr == ""


@pytest.mark.integration
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_dockerized_whichrosetta_success(mock_rosetta_bin, monkeypatch):
    """
    Test that 'whichrosetta' successfully finds the Rosetta binary in a dockerized environment.
    """

    _mock_rosetta_bin = os.path.join(
        os.path.dirname(mock_rosetta_bin), os.path.basename(mock_rosetta_bin).split(".")[0]
    )
    shutil.move(mock_rosetta_bin, _mock_rosetta_bin)
    mock_rosetta_bin = _mock_rosetta_bin

    # Set the PATH environment variable to include the temp directory
    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{os.path.dirname(mock_rosetta_bin)}{os.pathsep}{original_path}")

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
        expected_output = f"{mock_rosetta_bin}\n"
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


@pytest.mark.integration
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
@pytest.mark.parametrize(
    "sys_argv, which_bin_return, os_path_isfile_return, finder_bin_path, finder_full_path, set_to_path",
    [
        # Test case 1: Binary is found in system PATH
        (["whichrosetta", "relax"], "/usr/bin/relax", True, None, None, False),
        # Test case 2: Binary is not in PATH, but found in Rosetta installation
        (["whichrosetta", "relax", "/usr/local/bin"], True, True, None, None, False),
        # Test case 2: Binary is in PATH and found in Rosetta installation
        (["whichrosetta", "relax", "/usr/local/bin"], True, True, None, None, True),
    ],
)
def test_main(
    sys_argv,
    which_bin_return,
    os_path_isfile_return,
    finder_bin_path,
    finder_full_path,
    set_to_path,
    monkeypatch,
    capsys,
    mock_rosetta_bin,
):
    from RosettaPy.rosetta_finder import main

    if len(sys_argv) > 2:
        dir_name = os.path.dirname(mock_rosetta_bin)
        original_path = os.environ.get("PATH", "").split(os.pathsep)

        # drop rosetta related path from PATH
        for _p in original_path:
            if "rosetta" in _p:
                warnings.warn(f"Removing Rosetta from PATH: {_p}")
                original_path.remove(_p)
        if set_to_path:
            original_path.insert(0, dir_name)
        monkeypatch.setenv("PATH", f"{os.pathsep.join(original_path)}")

        sys_argv[2] = dir_name
        finder_full_path = mock_rosetta_bin

    if isinstance(which_bin_return, bool):
        if which_bin_return:
            which_bin_return = finder_full_path
        else:
            which_bin_return = None

    # Mock sys.argv
    monkeypatch.setattr(sys, "argv", sys_argv)

    # Mock shutil.which to return the desired value
    monkeypatch.setattr("shutil.which", lambda x: which_bin_return)

    # Mock os.path.isfile to return True or False based on the input
    def mock_isfile(path):
        if path == which_bin_return or path == finder_full_path:
            return os_path_isfile_return
        return False

    monkeypatch.setattr("os.path.isfile", mock_isfile)

    # Now call main() and capture output or exceptions
    if which_bin_return and os_path_isfile_return:
        # Expect the binary path from shutil.which to be printed
        main()
        captured = capsys.readouterr()
        assert captured.out.strip() == which_bin_return
    elif finder_full_path:
        # Expect the binary path from RosettaFinder to be printed
        main()
        captured = capsys.readouterr()
        assert captured.out.strip() == finder_full_path
    else:
        # Expect a FileNotFoundError to be raised
        with pytest.raises(FileNotFoundError):
            main()
