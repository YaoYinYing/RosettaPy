import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from RosettaPy.node.wsl import WslMount, WslWrapper
from RosettaPy.rosetta_finder import RosettaBinary
from RosettaPy.utils import tmpdir_manager
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


# Mock data
MOCK_DISTRO = "Ubuntu"
MOCK_USER = "testuser"
MOCK_CMD = ["echo", "Hello, WSL!"]
MOCK_OUTPUT = "Hello, WSL!\n"

MOCK_ROSETTA = RosettaBinary("/bin", "rosetta_scripts")


class TestWslWrapper:

    @pytest.fixture
    def wsl_wrapper(self):
        with patch("RosettaPy.node.wsl.WslWrapper.run_wsl_command", return_value=f"{MOCK_DISTRO}\nDebian"):
            return WslWrapper(rosetta_bin=MOCK_ROSETTA, distro=MOCK_DISTRO, user=MOCK_USER)

    @pytest.fixture
    def mock_task(self):
        with tmpdir_manager() as tmp_dir:
            return RosettaCmdTask(cmd=["rosetta"], base_dir=tmp_dir)

    def test_run_wsl_command_success(self, wsl_wrapper):
        with patch.object(wsl_wrapper, "run_wsl_command", return_value=MOCK_OUTPUT):

            mock_process = MagicMock()
            mock_process.communicate.return_value = (MOCK_OUTPUT, "")
            mock_process.wait.return_value = 0

            output = wsl_wrapper.run_wsl_command(MOCK_CMD)
            assert output == MOCK_OUTPUT

    def test_has_mpirun_installed(self, wsl_wrapper):
        with patch.object(wsl_wrapper, "run_wsl_command", return_value="/usr/bin/mpirun\n"):
            assert wsl_wrapper.has_mpirun is True

    def test_recompose_with_mpi(self, wsl_wrapper):
        wsl_wrapper.mpi_available = True
        wsl_wrapper._mpirun_cache = True
        cmd = ["rosetta", "-in:file:somefile.pdb"]
        expected_cmd = ["mpirun", "--use-hwthread-cpus", "-np", "4", "rosetta", "-in:file:somefile.pdb"]
        assert wsl_wrapper.recompose(cmd) == expected_cmd

    def test_recompose_without_mpi(self, wsl_wrapper):
        wsl_wrapper.mpi_available = False
        cmd = ["rosetta", "-in:file:somefile.pdb"]
        assert wsl_wrapper.recompose(cmd) == cmd

    def test_run_single_task(self, wsl_wrapper, mock_task):
        with patch.object(wsl_wrapper, "run_wsl_command", return_value="C:\\Windows\\system32\\wsl.EXE"), patch(
            "RosettaPy.node.utils.mount", return_value=(mock_task, None)
        ):
            with patch(
                "RosettaPy.node.wsl.WslMount.from_path",
                return_value=WslMount(source=mock_task.runtime_dir, target="/mnt/tmp/runtime_dir"),
            ):
                result_task = wsl_wrapper.run_single_task(mock_task, lambda x: x)
                assert result_task.cmd == [
                    "wsl",
                    "-d",
                    MOCK_DISTRO,
                    "-u",
                    MOCK_USER,
                    "--cd",
                    "/mnt/tmp/runtime_dir",
                    "rosetta",
                ]
