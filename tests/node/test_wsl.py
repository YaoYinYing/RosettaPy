import subprocess
from unittest.mock import MagicMock, patch

import pytest

from RosettaPy.node.wsl import WslMount, WslWrapper, which_wsl
from RosettaPy.rosetta_finder import RosettaBinary
from RosettaPy.utils import tmpdir_manager
from RosettaPy.utils.task import RosettaCmdTask

# Mock data
MOCK_DISTRO = "Ubuntu"
MOCK_USER = "testuser"
MOCK_CMD = ["echo", "Hello, WSL!"]
MOCK_OUTPUT = "Hello, WSL!\n"

MOCK_ROSETTA = RosettaBinary("/bin", "rosetta_scripts")
MOCK_WSL_BIN = "C:\\Windows\\system32\\wsl.EXE"
MOCK_MOUNTED_CURDIR = "/mnt/tmp/runtime_dir"


@patch("RosettaPy.node.wsl.which_wsl", return_value=MOCK_WSL_BIN)
def test_from_path_success(mock_wsl_exe):
    # Test successful conversion of Windows path to WSL path
    windows_path = "C:\\Windows\\Path"
    expected_wsl_path = "/mnt/c/Windows/Path"

    with patch("subprocess.check_output") as mock_check_output:
        mock_check_output.return_value = expected_wsl_path.encode() + b"\n"
        mount = WslMount.from_path(windows_path)

        assert mount.source == windows_path
        assert mount.target == expected_wsl_path
        mock_check_output.assert_called_once_with([mock_wsl_exe.return_value, "wslpath", "-a", windows_path])


@patch("RosettaPy.node.wsl.which_wsl", return_value=MOCK_WSL_BIN)
def test_from_path_failure(mock_wsl_exe):
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


@pytest.fixture
def mock_task():
    with tmpdir_manager() as tmp_dir:
        return RosettaCmdTask(cmd=["rosetta"], base_dir=tmp_dir)


@pytest.fixture
def wsl_wrapper(mock_task):
    with patch("RosettaPy.node.wsl.WslWrapper.run_wsl_command", return_value=f"{MOCK_DISTRO}\nDebian"):
        return WslWrapper(rosetta_bin=MOCK_ROSETTA, distro=MOCK_DISTRO, user=MOCK_USER)


def test_run_wsl_command_success(wsl_wrapper):
    with patch.object(wsl_wrapper, "run_wsl_command", return_value=MOCK_OUTPUT):

        mock_process = MagicMock()
        mock_process.communicate.return_value = (MOCK_OUTPUT, "")
        mock_process.wait.return_value = 0

        output = wsl_wrapper.run_wsl_command(MOCK_CMD)
        assert output == MOCK_OUTPUT


def test_has_mpirun_installed(wsl_wrapper):
    with patch.object(wsl_wrapper, "run_wsl_command", return_value="/usr/bin/mpirun\n"):
        assert wsl_wrapper.has_mpirun is True


def test_recompose_with_mpi(wsl_wrapper):
    wsl_wrapper.mpi_available = True
    wsl_wrapper._mpirun_cache = True
    cmd = ["rosetta", "-in:file:somefile.pdb"]
    expected_cmd = ["mpirun", "--use-hwthread-cpus", "-np", "4", "rosetta", "-in:file:somefile.pdb"]
    with wsl_wrapper.apply(cmd) as recomposed_cmd:
        assert recomposed_cmd == expected_cmd


def test_recompose_without_mpi(wsl_wrapper):
    wsl_wrapper.mpi_available = False
    cmd = ["rosetta", "-in:file:somefile.pdb"]
    with wsl_wrapper.apply(cmd) as recomposed_cmd:
        assert recomposed_cmd == cmd


def test_run_single_task(wsl_wrapper, mock_task):
    with patch("RosettaPy.node.wsl.which_wsl", return_value=MOCK_WSL_BIN), patch(
        "RosettaPy.node.wsl.WslMount.from_path",
        return_value=WslMount(source=mock_task.runtime_dir, target=MOCK_MOUNTED_CURDIR),
    ), patch("RosettaPy.utils.task._non_isolated_execute", side_effect=lambda x: x), patch(
        "RosettaPy.utils.task.execute"
    ) as mock_execute:
        expected_cmd = [
            MOCK_WSL_BIN,
            "-d",
            MOCK_DISTRO,
            "-u",
            MOCK_USER,
            "--cd",
            MOCK_MOUNTED_CURDIR,
            "rosetta",
        ]

        result_task = wsl_wrapper.run_single_task(mock_task)

        assert result_task.cmd == expected_cmd


# Mock the platform.system function to simulate different operating systems
@patch("platform.system")
def test_which_wsl_on_windows_with_wsl(mock_platform_system):
    # Arrange
    mock_platform_system.return_value = "Windows"
    mock_shutil_which = MagicMock(return_value="/path/to/wsl")

    with patch("shutil.which", mock_shutil_which):
        # Act
        result = which_wsl()

        # Assert
        assert result == "/path/to/wsl"
        mock_shutil_which.assert_called_once_with("wsl")


# Test when WSL is not available
@patch("platform.system")
def test_which_wsl_on_windows_without_wsl(mock_platform_system):
    # Arrange
    mock_platform_system.return_value = "Windows"
    mock_shutil_which = MagicMock(return_value=None)

    with patch("shutil.which", mock_shutil_which):
        # Act & Assert
        with pytest.raises(RuntimeError, match="WSL is not available."):
            which_wsl()


# Test on non-Windows system
@patch("platform.system")
def test_which_wsl_on_non_windows(mock_platform_system):
    # Arrange
    mock_platform_system.return_value = "Linux"

    # Act & Assert
    with pytest.raises(RuntimeError, match="WslWrapper is only available on Windows."):
        which_wsl()
