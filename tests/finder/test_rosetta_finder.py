from __future__ import annotations

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from RosettaPy import RosettaBinary, RosettaFinder
from tests.conftest import github_rosetta_test


# Test RosettaBinary.from_filename with valid filenames
@pytest.mark.parametrize(
    "filename",
    [
        "rosetta_scripts.linuxgccrelease",
        "rosetta_scripts.mpi.macosclangdebug",
        "rosetta_scripts.static.linuxgccrelease",
        "rosetta_scripts.default.macosclangdebug",
        "rosetta_scripts.cxx11threadserialization.linuxgccrelease",  # Docker serial
        "rosetta_scripts",  # Docker serial
    ],
)
def test_rosetta_binary_from_filename_valid(filename):
    dirname = "/path/to/rosetta/bin"
    rosetta_binary = RosettaBinary.from_filename(dirname, filename)
    assert rosetta_binary.dirname == dirname
    assert rosetta_binary.binary_name == "rosetta_scripts"
    assert rosetta_binary.mode in [None, "mpi", "static", "default", "cxx11threadserialization"]
    assert rosetta_binary.os in [None, "linux", "macos"]
    assert rosetta_binary.compiler in [None, "gcc", "clang"]
    assert rosetta_binary.release in [None, "release", "debug"]
    # Test filename property
    assert rosetta_binary.filename == filename
    # Test full_path property
    expected_full_path = os.path.join(dirname, filename)
    assert rosetta_binary.full_path == expected_full_path


# Test RosettaBinary.from_filename with invalid filenames
@pytest.mark.parametrize(
    "filename",
    [
        "rosetta_scripts.windowsgccrelease",  # Invalid OS
        "rosetta_scripts.linuxgcc",  # Missing release
        "rosetta_scripts.mpi.linuxgccbeta",  # Invalid release
        "rosetta_scripts.linuxgccrelease.exe",  # Extra extension
        "rosetta_scripts.cxx11threadserialization..linuxgccrelease",  # Typo
        "rosetta_scripts.",  # Ending dot
        "/rosetta_scripts",  # Leading slash
    ],
)
def test_rosetta_binary_from_filename_invalid(filename):
    dirname = "/path/to/rosetta/bin"
    with pytest.raises(ValueError):
        RosettaBinary.from_filename(dirname, filename)


# Test RosettaFinder.find_binary when binary is found
@patch("pathlib.Path.iterdir")
@patch("pathlib.Path.is_dir")
@patch("pathlib.Path.exists")
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_find_binary_success(mock_exists, mock_is_dir, mock_iterdir):
    # Set up the mocks
    with patch.dict("os.environ", {"ROSETTA_BIN": "/mock/rosetta/bin"}):
        mock_exists.return_value = True
        mock_is_dir.return_value = True

        # Mock files in the directory
        mock_file = MagicMock()
        mock_file.is_file.return_value = True
        mock_file.name = "rosetta_scripts.linuxgccrelease"

        mock_iterdir.return_value = [mock_file]

        finder = RosettaFinder()
        rosetta_binary = finder.find_binary("rosetta_scripts")

        assert isinstance(rosetta_binary, RosettaBinary)
        assert rosetta_binary.binary_name == "rosetta_scripts"
        assert rosetta_binary.mode is None
        assert rosetta_binary.os == "linux"
        assert rosetta_binary.compiler == "gcc"
        assert rosetta_binary.release == "release"
        assert rosetta_binary.dirname == "/mock/rosetta/bin"
        expected_full_path = "/mock/rosetta/bin/rosetta_scripts.linuxgccrelease"
        assert rosetta_binary.full_path == expected_full_path


# Test RosettaFinder.find_binary when binary is not found
@patch("pathlib.Path.iterdir")
@patch("pathlib.Path.is_dir")
@patch("pathlib.Path.exists")
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_find_binary_not_found(mock_exists, mock_is_dir, mock_iterdir):
    # Set up the mocks
    with patch.dict("os.environ", {"ROSETTA_BIN": "/mock/rosetta/bin"}):
        mock_exists.return_value = True
        mock_is_dir.return_value = True

        # Mock empty directory
        mock_iterdir.return_value = []

        finder = RosettaFinder()
        with pytest.raises(FileNotFoundError):
            finder.find_binary("rosetta_scripts")


# Test RosettaFinder initialization on unsupported OS
def test_unsupported_os():
    with patch("sys.platform", "win32"), pytest.raises(EnvironmentError):
        RosettaFinder()


# Integration tests


@pytest.fixture
def temp_dir():
    # Create a temporary directory
    dirpath = tempfile.mkdtemp()
    yield dirpath
    # Clean up after test
    shutil.rmtree(dirpath)


@pytest.mark.integration
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_integration_find_binary(temp_dir):
    # Create files in the temporary directory
    valid_filenames = [
        "rosetta_scripts.linuxgccrelease",
        "rosetta_scripts.mpi.linuxgccdebug",
        "rosetta_scripts.static.macosclangrelease",
        "rosetta_scripts.default.macosclangdebug",
    ]

    invalid_filenames = [
        "rosetta_scripts.windowsgccrelease",  # Invalid OS
        "rosetta_scripts.linuxgcc",  # Missing release
        "random_file.txt",  # Non-matching file
        "rosetta_scripts.linuxgccbeta",  # Invalid release
        "rosetta_scripts.linuxgccrelease.exe",  # Extra extension
    ]

    # Create valid binary files
    for filename in valid_filenames:
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w") as f:
            f.write("")  # Create an empty file

    # Create invalid files
    for filename in invalid_filenames:
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w") as f:
            f.write("")  # Create an empty file

    # Instantiate RosettaFinder with the temporary directory
    finder = RosettaFinder(search_path=temp_dir)

    # Search for 'rosetta_scripts' binary
    rosetta_binary = finder.find_binary("rosetta_scripts")

    # Verify that the returned binary is one of the valid ones
    assert isinstance(rosetta_binary, RosettaBinary)
    assert rosetta_binary.binary_name == "rosetta_scripts"
    assert rosetta_binary.filename in valid_filenames

    # Print the outputs
    print(f"Found binary: {rosetta_binary.full_path}")
    print(f"Binary Name: {rosetta_binary.binary_name}")
    print(f"Mode: {rosetta_binary.mode}")
    print(f"OS: {rosetta_binary.os}")
    print(f"Compiler: {rosetta_binary.compiler}")
    print(f"Release: {rosetta_binary.release}")


@pytest.mark.integration
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_integration_no_binary_found(temp_dir):
    # Create invalid files only
    invalid_filenames = [
        "rosetta_scripts.windowsgccrelease",  # Invalid OS
        "rosetta_scripts.linuxgcc",  # Missing release
        "random_file.txt",  # Non-matching file
        "rosetta_scripts.linuxgccbeta",  # Invalid release
        "rosetta_scripts.linuxgccrelease.exe",  # Extra extension
    ]

    # Create invalid files
    for filename in invalid_filenames:
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w") as f:
            f.write("")  # Create an empty file

    # Instantiate RosettaFinder with the temporary directory
    finder = RosettaFinder(search_path=temp_dir)

    # Attempt to find 'rosetta_scripts' binary, expect FileNotFoundError
    with pytest.raises(FileNotFoundError):
        finder.find_binary("rosetta_scripts.linuxgccrelease")
