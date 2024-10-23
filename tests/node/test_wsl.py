import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from RosettaPy.node.wsl import WslMount, WslWrapper
from RosettaPy.utils.task import RosettaCmdTask


def test_from_path_success():
    # Test successful conversion of Windows path to WSL path
    windows_path = "C:\\Windows\\Path"
    expected_wsl_path = "/mnt/c/Windows/Path"

    with patch("subprocess.check_output") as mock_check_output:
        mock_check_output.return_value = expected_wsl_path.encode() + b"\n"
        mount = WslMount.from_path(windows_path)

        assert mount.source == windows_path
        assert mount.target == expected_wsl_path
        mock_check_output.assert_called_once_with(["wsl", "wslpath", "-a", windows_path])


def test_from_path_failure():
    # Test failure of conversion from Windows path to WSL path
    windows_path = "C:\\Invalid\\Path"

    with patch("subprocess.check_output") as mock_check_output:
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "wslpath")
        with pytest.raises(RuntimeError) as exc_info:
            WslMount.from_path(windows_path)

        assert f"Failed to convert Windows path to WSL path: {windows_path}" in str(exc_info.value)


def test_mounted_property():
    # Test the mounted property returns the correct value
    wsl_mount = WslMount(source="C:\\Windows\\Path", target="/mnt/c/Windows/Path")
    assert wsl_mount.mounted == "/mnt/c/Windows/Path"


# Mock environment for WSL
os.environ["WSL_DISTRO_NAME"] = "Ubuntu"


class TestWslWrapper:

    @pytest.fixture
    def wsl_wrapper(self):
        return WslWrapper(rosetta_bin_dir="/path/to/rosetta/bin")

    @patch("subprocess.run")
    def test_is_root_user_wsl_true(self, mock_subprocess, wsl_wrapper):
        mock_subprocess.return_value = MagicMock(stdout="root\n", stderr="", returncode=0)
        assert wsl_wrapper.is_root_user_wsl is True

    @patch("subprocess.run")
    def test_is_root_user_wsl_false(self, mock_subprocess, wsl_wrapper):
        mock_subprocess.return_value = MagicMock(stdout="user\n", stderr="", returncode=0)
        assert wsl_wrapper.is_root_user_wsl is False

    @patch("subprocess.run")
    def test_is_root_user_wsl_exception(self, mock_subprocess, wsl_wrapper):
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "wsl whoami")
        assert wsl_wrapper.is_root_user_wsl is False

    @patch("subprocess.run")
    def test_does_wsl_have_mpirun_true(self, mock_subprocess, wsl_wrapper):
        mock_subprocess.return_value = MagicMock(returncode=0)
        assert wsl_wrapper.does_wsl_have_mpirun is True

    @patch("subprocess.run")
    def test_does_wsl_have_mpirun_false(self, mock_subprocess, wsl_wrapper):
        mock_subprocess.return_value = MagicMock(returncode=1)
        assert wsl_wrapper.does_wsl_have_mpirun is False

    @patch("subprocess.run")
    def test_does_wsl_have_mpirun_exception(self, mock_subprocess, wsl_wrapper):
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "wsl which mpirun")
        assert wsl_wrapper.does_wsl_have_mpirun is False

    def test_recompose_no_mpi(self, wsl_wrapper):
        wsl_wrapper.mpi_available = False
        cmd = ["ls", "-l"]
        recomposed_cmd = wsl_wrapper.recompose(cmd)
        assert recomposed_cmd == cmd

    def test_recompose_with_mpi(self, wsl_wrapper):
        wsl_wrapper.mpi_available = True
        wsl_wrapper._mpirun_cache = True
        with patch("RosettaPy.node.wsl.WslWrapper.is_root_user_wsl", return_value=True):

            cmd = ["ls", "-l"]
            recomposed_cmd = wsl_wrapper.recompose(cmd)
            expected_cmd = ["mpirun", "--use-hwthread-cpus", "-np", "4", "--allow-run-as-root", "ls", "-l"]
            assert recomposed_cmd == expected_cmd
