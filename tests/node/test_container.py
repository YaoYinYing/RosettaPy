import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from RosettaPy.node import RosettaContainer
from RosettaPy.node.dockerized import RosettaPyMount
from RosettaPy.node.utils import get_quoted, mount
from RosettaPy.utils import RosettaCmdTask


@pytest.fixture
def temp_dir():
    # Create a temporary directory
    dirpath = tempfile.mkdtemp()
    yield dirpath
    # Clean up after test
    shutil.rmtree(dirpath)


@pytest.fixture
def mock_task():
    return RosettaCmdTask(
        cmd=["/path/to/executable", "-option", "file.txt", "@flagfile", "-parser:script_vars", "var=/some/path"],
        base_dir="/tmp/runtime_dir",
    )


def get_mounted_name(path: str):
    with patch("os.path.exists", return_value=True), patch("os.path.isdir", return_value=True):
        return RosettaPyMount.get_mounted_name(os.path.abspath(path))


def get_mounted_path(path: str, as_dir: bool = False):
    path = os.path.abspath(os.path.normpath(path))

    # if it is a directory
    if as_dir:
        return os.path.join("/tmp/", get_mounted_name(path))

    # if not a directory
    return os.path.join("/tmp/", get_mounted_name(os.path.dirname(path)), os.path.basename(path))


def test_get_quoted():
    expected = "'test'"
    assert get_quoted("test") == expected
    assert get_quoted("'test") == expected
    assert get_quoted("test'") == expected
    assert get_quoted("'test'") == expected


def test_rosetta_pymount_from_path():
    with patch("os.path.normpath", return_value="/normalized/path"), patch(
        "os.path.abspath", return_value="/absolute/path"
    ), patch("os.path.isdir", return_value=True), patch("os.path.exists", return_value=True), patch(
        "os.makedirs"
    ) as mock_makedirs, patch(
        "docker.types.Mount"
    ) as mock_mount:

        mock_mount.return_value = MagicMock()
        mounted = RosettaPyMount.from_path("/path/to/mount")

        assert mounted.source == "/absolute/path"
        assert mounted.target == "/tmp/absolute-path"
        assert mounted.mounted == "/tmp/absolute-path"


def test_rosetta_pymount_get_mounted_name():
    with patch("os.path.exists", return_value=True), patch("os.path.abspath", return_value="/absolute/path"):

        with patch("os.path.isfile", return_value=False):
            result = RosettaPyMount.get_mounted_name("/some/path")
            assert result == "absolute-path"

        with patch("os.path.isfile", return_value=True):
            result = RosettaPyMount.get_mounted_name("/some/file.txt")
            assert result == "absolute"


def test_rosetta_container_recompose():
    container = RosettaContainer(image="rosettacommons/rosetta:mpi", mpi_available=True, nproc=4)
    cmd = ["some_executable", "-flag"]
    with container.apply(cmd) as recomposed_cmd:

        assert recomposed_cmd == [
            "mpirun",
            "--use-hwthread-cpus",
            "-np",
            "4",
            "--allow-run-as-root",
            "some_executable",
            "-flag",
        ]


def test_rosetta_container_run_single_task(mock_task):
    with patch("docker.from_env") as mock_docker, patch(
        "RosettaPy.node.utils.mount", return_value=(mock_task, [])
    ) as mock_mount, patch("signal.signal") as mock_signal:

        mock_client = mock_docker.return_value
        mock_container = mock_client.containers.run.return_value
        mock_container.logs.return_value = [b"Log line 1\n", b"Log line 2\n"]

        container = RosettaContainer()
        mounted_task, mounts = mount(mock_task, mounter=RosettaPyMount)
        result_task = container.run_single_task(mock_task)

        mock_client.containers.run.assert_called_once_with(
            image=container.image,
            command=mock_task.cmd,
            remove=True,
            detach=True,
            mounts=mounts,
            user=container.user,
            stdout=True,
            stderr=True,
            working_dir=mounted_task.runtime_dir,
            platform="linux/amd64",
        )
        mock_signal.assert_called_once()
        assert result_task == mock_task


def test_rosetta_container_recompose_no_mpi():
    container = RosettaContainer(image="rosettacommons/rosetta:static", mpi_available=False)
    cmd = ["some_executable", "-flag"]
    with container.apply(cmd) as recomposed_cmd:

        assert recomposed_cmd == cmd


def test_rosetta_pymount_squeeze():
    mount1 = MagicMock()
    mount2 = MagicMock()
    mount3 = mount1  # Duplicate

    result = RosettaPyMount.squeeze([mount1, mount2, mount3])
    assert len(result) == 2


@pytest.mark.parametrize(
    "file_paths, dir_paths, cmd, expected_cmd, expected_mounts_count",
    [
        (["input.pdb"], [], ["-in:file:s", "input.pdb"], ["-in:file:s", get_mounted_path("input.pdb")], 2),
        (
            [],
            [
                "/path/to/pdb",
                "/path/to/scorefile",
            ],
            [
                "-out:path:pdb",
                "/path/to/pdb",
                "-out:path:score",
                "/path/to/scorefile",
            ],
            [
                "-out:path:pdb",
                get_mounted_path("/path/to/pdb/", as_dir=True),
                "-out:path:score",
                get_mounted_path("/path/to/scorefile/", as_dir=True),
            ],
            3,
        ),
        (
            ["input.pdb"],
            [
                "/path/to/pdb",
                "/path/to/scorefile",
            ],
            [
                "-in:file:s",
                "input.pdb",
                "-out:path:pdb",
                "/path/to/pdb",
                "-out:path:score",
                "/path/to/scorefile",
            ],
            [
                "-in:file:s",
                get_mounted_path("input.pdb"),
                "-out:path:pdb",
                get_mounted_path("/path/to/pdb/", as_dir=True),
                "-out:path:score",
                get_mounted_path("/path/to/scorefile/", as_dir=True),
            ],
            4,
        ),
        (["flag.txt"], [], ["@flag.txt"], [f'@{get_mounted_path("flag.txt")}'], 2),
        ([], [], ["-parser:script_vars", "var=1"], ["-parser:script_vars", "var=1"], 1),
        (
            ["value.txt"],
            [],
            ["-parser:script_vars", "var=value.txt"],
            ["-parser:script_vars", f"var={get_mounted_path('value.txt')}"],
            2,
        ),
        (
            ["constraints.cst"],
            [],
            ["-parser:script_vars", "xml_var='<Add file=\"constraints.cst\" />'"],
            ["-parser:script_vars", f"xml_var='<Add file=\"{get_mounted_path('constraints.cst')}\" />'"],
            2,
        ),
        ([], [], ["-out:prefix", "test"], ["-out:prefix", "test"], 1),
        (
            ["test_scripts.xml"],
            [],
            [
                "-parser:protocol",
                "test_scripts.xml",
            ],
            [
                "-parser:protocol",
                get_mounted_path("test_scripts.xml"),
            ],
            2,
        ),
        (
            ["/test/input.pdb", "/test/relax_script.txt"],
            [],
            [
                "-in:file:s",
                "/test/input.pdb",
                "-relax:script",
                "/test/relax_script.txt",
                "-relax:default_repeats",
                "15",
                "-out:prefix",
                "my_fastrelax_",
                "-out:file:scorefile",
                "my_fastrelax.sc",
                "-score:weights",
                "ref2015_cart",
                "-relax:dualspace",
                "true",
            ],
            [
                "-in:file:s",
                get_mounted_path("/test/input.pdb"),
                "-relax:script",
                get_mounted_path("/test/relax_script.txt"),
                "-relax:default_repeats",
                "15",
                "-out:prefix",
                "my_fastrelax_",
                "-out:file:scorefile",
                "my_fastrelax.sc",
                "-score:weights",
                "ref2015_cart",
                "-relax:dualspace",
                "true",
            ],
            2,
        ),
    ],
)
def test_mount_with_command(file_paths, dir_paths, cmd, expected_cmd, expected_mounts_count, temp_dir):
    """Test mounting when the command includes relative file paths."""

    file_paths = [os.path.abspath(file_path) for file_path in file_paths]
    dir_paths = [os.path.abspath(dir_path) for dir_path in dir_paths]

    def is_file_side_effect(path):
        path = os.path.abspath(path)
        _ = path in file_paths
        return _

    def is_dir_side_effect(path):
        path = os.path.abspath(path)
        _ = path in dir_paths
        return _

    with patch("os.path.exists", return_value=True), patch("os.path.isfile", side_effect=is_file_side_effect), patch(
        "os.path.isdir", side_effect=is_dir_side_effect
    ):
        task = RosettaCmdTask(cmd=cmd, base_dir=temp_dir)

        mounted_task, mounts = mount(task, RosettaPyMount)
        assert mounts is not None
        assert mounted_task.cmd == expected_cmd
        assert len(mounts) == expected_mounts_count


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
def test_mount_with_relative_paths(cmd, file_paths, expected_cmd, expected_mounts_count, temp_dir):
    """Test mounting when the command includes relative file paths."""
    task = RosettaCmdTask(cmd=cmd, base_dir=temp_dir)

    def is_file_side_effect(path):
        return os.path.abspath(path) in file_paths

    def create_mount_side_effect(mn, p, ro=False):
        target = os.path.join("/tmp", mn)
        mounted_path = os.path.join(target, os.path.basename(p))
        return RosettaPyMount(
            name=mn,
            source=os.path.abspath(p),
            target=target,
            mounted=mounted_path,
        )

    with patch("os.path.exists", return_value=True), patch("os.path.isfile", side_effect=is_file_side_effect), patch(
        "os.path.abspath", side_effect=lambda p: "/abs/path/input.pdb"
    ), patch.object(RosettaPyMount, "_create_mount", side_effect=create_mount_side_effect):

        # Compute expected_cmd if not provided
        if expected_cmd is None:
            mn = RosettaPyMount.get_mounted_name("/abs/path/input.pdb")
            mounted_path = os.path.join("/tmp", mn, "input.pdb")
            expected_cmd = ["-in:file:s", mounted_path]

        mounted_task, mounts = mount(task, RosettaPyMount)
        assert mounts is not None
        assert mounted_task.cmd == expected_cmd
        assert len(mounts) == expected_mounts_count
