import os
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from docker import types
from RosettaPy.utils import RosettaCmdTask
from RosettaPy.utils.escape import Colors

from RosettaPy.node import RosettaContainer


@pytest.fixture
def temp_dir():
    # Create a temporary directory
    dirpath = tempfile.mkdtemp()
    yield dirpath
    # Clean up after test
    shutil.rmtree(dirpath)


@pytest.fixture
def rosetta_container():
    """Fixture to create a RosettaContainer instance."""
    return RosettaContainer(
        image="rosettacommons/rosetta:mpi",
        mpi_available=True,
        nproc=4,
        prohibit_mpi=False,
    )


def test_post_init(rosetta_container):
    """Test the __post_init__ method."""
    assert rosetta_container.mpi_available == True
    assert rosetta_container.nproc == 4


def test_mounted_name_valid_path(temp_dir, rosetta_container):
    """Test the mounted_name method with a valid path."""
    test_dir = os.path.join(temp_dir, "test_dir")
    os.makedirs(test_dir, exist_ok=True)
    result = rosetta_container.mounted_name(str(test_dir))
    expected = str(test_dir).replace("/", "-").strip("-")
    assert result == expected


def test_mounted_name_valid_file(temp_dir, rosetta_container):
    """Test the mounted_name method with a valid path."""
    test_file = os.path.join(temp_dir, "test_dir", "sample.txt")
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, "w") as fh:
        fh.write("content")

    result = rosetta_container.mounted_name(str(test_file))
    expected = os.path.dirname(test_file).replace("/", "-").strip("-")
    assert result == expected


def test_mounted_name_invalid_path():
    """Test the mounted_name method with an invalid path."""
    with pytest.raises(FileNotFoundError):
        RosettaContainer.mounted_name("/non/existent/path")


@patch("os.makedirs")
def test_mount_method_2(mock_makedirs, rosetta_container):
    """Test the mount method."""
    task = RosettaCmdTask(cmd=["-in:file", "input.pdb", "-out:file", "output.pdb"], base_dir="/tmp/runtime")
    with patch("os.path.exists", return_value=True), patch("os.path.isfile", return_value=True), patch.object(
        rosetta_container,
        "_create_mount",
        return_value=(types.Mount(target="/mount", source="/source"), "/mounted/path"),
    ):
        mounted_task, mounts = rosetta_container.mount(task)
        assert mounted_task.cmd == ["-in:file", "/mounted/path", "-out:file", "/mounted/path"]
        assert len(mounts) > 0


def test_recompose_mpi_available(rosetta_container):
    """Test the recompose method when MPI is available."""
    cmd = ["rosetta_script", "-in:file", "input.pdb"]
    recomposed_cmd = rosetta_container.recompose(cmd)
    expected_cmd = ["mpirun", "--use-hwthread-cpus", "-np", "4", "--allow-run-as-root"] + cmd
    assert recomposed_cmd == expected_cmd


def test_recompose_mpi_not_available():
    """Test the recompose method when MPI is not available."""
    rosetta_container = RosettaContainer(mpi_available=False, prohibit_mpi=True)
    cmd = ["rosetta_script", "-in:file", "input.pdb"]
    with pytest.warns(RuntimeWarning):
        recomposed_cmd = rosetta_container.recompose(cmd)
    assert recomposed_cmd == cmd


@patch("docker.from_env")
def test_run_single_task(mock_docker, rosetta_container, temp_dir):
    """Test the run_single_task method."""
    task = RosettaCmdTask(cmd=["-in:file", "input.pdb"], base_dir=temp_dir)
    mock_container = MagicMock()
    mock_container.logs.return_value = [b"Processing input.pdb", b"Finished"]
    mock_docker.return_value.containers.run.return_value = mock_container

    with patch.object(rosetta_container, "mount", return_value=(task, [])), patch("signal.signal"):
        result_task = rosetta_container.run_single_task(task)
        assert result_task == task
        mock_container.logs.assert_called_once_with(stream=True)


def get_mounted_path(rosetta_container, fp):
    """Helper function to compute the mounted path for a given file or directory."""
    mounted_name = rosetta_container.mounted_name(fp)
    if os.path.isdir(fp):
        # Directory mount
        return os.path.join(rosetta_container.root_mount_directory, mounted_name)
    else:
        # File mount
        return os.path.join(rosetta_container.root_mount_directory, mounted_name, os.path.basename(fp))


@pytest.mark.parametrize(
    "cmd, file_paths, dir_paths, expected_cmd, expected_mounts_count",
    [
        # Test case 1: Simple command with options and files
        (
            ["-in:file:s", "input.pdb", "-out:file:o", "output.pdb"],
            ["input.pdb", "output.pdb"],  # Files that exist
            [],  # No directories
            None,  # Will compute expected_cmd in the test function
            3,  # Number of expected mounts
        ),
        # Test case 3: Command with directory
        (
            ["-in:path", "input_dir/"],
            [],  # No files
            ["input_dir/"],  # Directories that exist
            None,
            2,
        ),
        # Test case 4: Command with options only
        (["-help", "-version"], [], [], ["-help", "-version"], 1),  # No files  # No directories
        # Test case 5: Empty command list
        ([], [], [], [], 1),
    ],
)
def test_mount_method(
    cmd,
    file_paths,
    dir_paths,
    expected_cmd,
    expected_mounts_count,
    temp_dir,
    rosetta_container,
):
    """Test the mount method with various inputs."""
    task = RosettaCmdTask(cmd=cmd, base_dir=temp_dir)

    # Define side effect functions for os.path.isfile and os.path.isdir
    def is_file_side_effect(path):
        return path in file_paths

    def is_dir_side_effect(path):
        return path.rstrip("/") in [d.rstrip("/") for d in dir_paths]

    # Define the side effect for _create_mount
    def create_mount_side_effect(mn, p, ro=False):
        if is_dir_side_effect(p):
            # Directory mount
            target = os.path.join(rosetta_container.root_mount_directory, mn)
            mounted_path = target
        else:
            # File mount
            target = os.path.join(rosetta_container.root_mount_directory, mn)
            mounted_path = os.path.join(target, os.path.basename(p))
        return (types.Mount(target=target, source=os.path.abspath(p.rstrip("/")), type="bind"), mounted_path)

    with patch("os.path.exists", return_value=True), patch("os.path.isfile", side_effect=is_file_side_effect), patch(
        "os.path.isdir", side_effect=is_dir_side_effect
    ), patch.object(rosetta_container, "_create_mount", side_effect=create_mount_side_effect):

        # Compute expected_cmd if not provided
        if expected_cmd is None:
            expected_cmd = []
            for arg in cmd:
                if arg.startswith("-") or arg.startswith("@"):
                    expected_cmd.append(arg)
                elif is_file_side_effect(arg) or is_dir_side_effect(arg):
                    mn = rosetta_container.mounted_name(os.path.abspath(arg))
                    if is_dir_side_effect(arg):
                        # Directory mount
                        mounted_path = os.path.join(rosetta_container.root_mount_directory, mn)
                    else:
                        # File mount
                        mounted_path = os.path.join(rosetta_container.root_mount_directory, mn, os.path.basename(arg))
                    expected_cmd.append(mounted_path)
                else:
                    expected_cmd.append(arg)

        mounted_task, mounts = rosetta_container.mount(task)
        assert mounted_task.cmd == expected_cmd
        assert len(mounts) == expected_mounts_count


def test_mount_with_flag_files(rosetta_container, temp_dir):
    """Test mounting when script_vars include XML fragments with file paths."""
    flag_file = "flag.txt"
    task = RosettaCmdTask(cmd=["rosetta_scripts", f"@{flag_file}", "-nstruct", "1000"], base_dir=temp_dir)

    def is_file_side_effect(path):
        return path == flag_file

    def create_mount_side_effect(mn, p, ro=False):
        target = os.path.join(rosetta_container.root_mount_directory, mn)
        mounted_path = os.path.join(target, os.path.basename(p))
        return (types.Mount(target=target, source=os.path.abspath(p), type="bind"), mounted_path)

    with patch("os.path.exists", return_value=True), patch(
        "os.path.isfile", side_effect=is_file_side_effect
    ), patch.object(rosetta_container, "_create_mount", side_effect=create_mount_side_effect):

        mounted_task, mounts = rosetta_container.mount(task)

        # Expected mounted path for constraints.cst
        mn = rosetta_container.mounted_name(os.path.abspath(flag_file))
        flag_mounted_path = os.path.join(rosetta_container.root_mount_directory, mn, flag_file)

        expected_flag = f"@{flag_mounted_path}"
        expected_cmd = ["rosetta_scripts", expected_flag, "-nstruct", "1000"]
        assert mounted_task.cmd == expected_cmd
        assert len(mounts) == 2


def test_mount_with_complex_script_vars(rosetta_container, temp_dir):
    """Test mounting when script_vars include XML fragments with file paths."""
    xml_fragment = '<Add file="constraints.cst" />'
    task = RosettaCmdTask(cmd=["-parser:script_vars", f"xml_var='{xml_fragment}'"], base_dir=temp_dir)

    def is_file_side_effect(path):
        return path == "constraints.cst"

    def create_mount_side_effect(mn, p, ro=False):
        target = os.path.join(rosetta_container.root_mount_directory, mn)
        mounted_path = os.path.join(target, os.path.basename(p))
        return (types.Mount(target=target, source=os.path.abspath(p), type="bind"), mounted_path)

    with patch("os.path.exists", return_value=True), patch(
        "os.path.isfile", side_effect=is_file_side_effect
    ), patch.object(rosetta_container, "_create_mount", side_effect=create_mount_side_effect):

        mounted_task, mounts = rosetta_container.mount(task)

        # Expected mounted path for constraints.cst
        mn = rosetta_container.mounted_name(os.path.abspath("constraints.cst"))
        constraints_mounted_path = os.path.join(rosetta_container.root_mount_directory, mn, "constraints.cst")

        expected_xml_fragment = f"'<Add file=\"{constraints_mounted_path}\" />'"
        expected_cmd = ["-parser:script_vars", f"xml_var={expected_xml_fragment}"]
        assert mounted_task.cmd == expected_cmd
        assert len(mounts) == 2


def test_mount_with_multiple_files_same_name(rosetta_container, temp_dir):
    """Test mounting multiple files with the same name in different directories."""
    task = RosettaCmdTask(cmd=["-in:file:s", "/path1/input.pdb", "/path2/input.pdb"], base_dir=temp_dir)
    file_paths = ["/path1/input.pdb", "/path2/input.pdb"]

    def is_file_side_effect(path):
        return path in file_paths

    def create_mount_side_effect(mn, p, ro=False):
        target = os.path.join(rosetta_container.root_mount_directory, mn)
        mounted_path = os.path.join(target, os.path.basename(p))
        return (types.Mount(target=target, source=os.path.abspath(p), type="bind"), mounted_path)

    with patch("os.path.exists", return_value=True), patch(
        "os.path.isfile", side_effect=is_file_side_effect
    ), patch.object(rosetta_container, "_create_mount", side_effect=create_mount_side_effect):

        mounted_task, mounts = rosetta_container.mount(task)

        # Expected commands
        expected_cmd = ["-in:file:s"]
        for fp in ["/path1/input.pdb", "/path2/input.pdb"]:
            mn = rosetta_container.mounted_name(os.path.abspath(fp))
            mounted_path = os.path.join(rosetta_container.root_mount_directory, mn, "input.pdb")
            expected_cmd.append(mounted_path)

        assert mounted_task.cmd == expected_cmd
        assert len(mounts) == 3


@pytest.mark.parametrize(
    "cmd, file_paths, expected_exception",
    [
        # Test case: Non-existent file
        (["-in:file:s", "nonexistent.pdb"], [], FileNotFoundError),  # No files exist
    ],
)
def test_mount_with_exceptions(rosetta_container, cmd, file_paths, expected_exception, temp_dir):
    """Test that the mount method raises exceptions as expected."""
    # Ensure that cmd is a list
    if isinstance(cmd, str):
        cmd_input = cmd  # Keep original input for exception testing
    else:
        cmd_input = cmd

    task = RosettaCmdTask(cmd=cmd_input, base_dir=temp_dir)

    def is_file_side_effect(path):
        return path in file_paths

    with patch("os.path.exists", return_value=False), patch("os.path.isfile", side_effect=is_file_side_effect):
        with pytest.raises(expected_exception):
            rosetta_container.mount(task)


@pytest.mark.parametrize(
    "cmd, file_paths, expected_cmd, expected_mounts_count",
    [
        # Test case: Command with relative paths
        (
            ["-in:file:s", "../input.pdb"],
            ["/abs/path/input.pdb"],  # Absolute path after os.path.abspath
            None,  # Will compute expected_cmd in the test function
            1,
        ),
    ],
)
def test_mount_with_relative_paths(rosetta_container, cmd, file_paths, expected_cmd, expected_mounts_count, temp_dir):
    """Test mounting when the command includes relative file paths."""
    task = RosettaCmdTask(cmd=cmd, base_dir=temp_dir)

    def is_file_side_effect(path):
        return os.path.abspath(path) in file_paths

    def create_mount_side_effect(mn, p, ro=False):
        target = os.path.join(rosetta_container.root_mount_directory, mn)
        mounted_path = os.path.join(target, os.path.basename(p))
        return (types.Mount(target=target, source=os.path.abspath(p), type="bind"), mounted_path)

    with patch("os.path.exists", return_value=True), patch("os.path.isfile", side_effect=is_file_side_effect), patch(
        "os.path.abspath", side_effect=lambda p: "/abs/path/input.pdb"
    ), patch.object(rosetta_container, "_create_mount", side_effect=create_mount_side_effect):

        # Compute expected_cmd if not provided
        if expected_cmd is None:
            mn = rosetta_container.mounted_name("/abs/path/input.pdb")
            mounted_path = os.path.join(rosetta_container.root_mount_directory, mn, "input.pdb")
            expected_cmd = ["-in:file:s", mounted_path]

        mounted_task, mounts = rosetta_container.mount(task)
        assert mounted_task.cmd == expected_cmd
        assert len(mounts) == expected_mounts_count
