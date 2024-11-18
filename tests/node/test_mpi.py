import os
import subprocess
from unittest.mock import patch

import pytest

from RosettaPy.node.mpi import MpiNode, get_nodes, which_scontrol

from ..conftest import github_rosetta_test


# Test for which_scontrol function
def test_which_scontrol_success():
    with patch("shutil.which", return_value="/fake/path/to/scontrol"):
        result = which_scontrol()
        assert result == "/fake/path/to/scontrol"


def test_which_scontrol_not_found():
    with patch("shutil.which", return_value=None), pytest.raises(RuntimeError, match="scontrol not found"):
        which_scontrol()


# Test for get_nodes function
@patch("os.getenv")
@patch("subprocess.check_output")
@patch("RosettaPy.node.mpi.which_scontrol", return_value="/fake/path/to/scontrol")
def test_get_nodes_success(mock_which_scontrol, mock_check_output, mock_getenv):
    mock_getenv.return_value = "node1,node2"
    mock_check_output.return_value = b"node1\nnode2\n"

    result = get_nodes()
    assert result == ["node1", "node2"]


@patch("os.getenv")
@patch("RosettaPy.node.mpi.which_scontrol", return_value="/fake/path/to/scontrol")
def test_get_nodes_no_slurm_job_nodelist(mock_which_scontrol, mock_getenv):
    mock_getenv.return_value = None

    with pytest.raises(ValueError, match="SLURM_JOB_NODELIST environment variable is not set"):
        get_nodes()


@patch("os.getenv")
@patch("subprocess.check_output")
@patch("RosettaPy.node.mpi.which_scontrol", return_value="/fake/path/to/scontrol")
def test_get_nodes_subprocess_error(mock_which_scontrol, mock_check_output, mock_getenv):
    mock_getenv.return_value = "node1,node2"
    mock_check_output.side_effect = subprocess.CalledProcessError(returncode=1, cmd="scontrol")

    with pytest.raises(RuntimeError, match="Failed to get nodes: Command 'scontrol' returned non-zero exit status 1."):
        get_nodes()


def test_mpi_node_initialization_without_node_matrix():
    with patch("shutil.which", return_value="/usr/bin/mpirun"):
        mpi_node = MpiNode(nproc=4)
        assert mpi_node.nproc == 4
        assert mpi_node.node_matrix is None
        assert mpi_node.mpi_executable == "/usr/bin/mpirun"
        assert mpi_node.local == [mpi_node.mpi_executable, "--use-hwthread-cpus", "-np", "4"]


def test_mpi_node_initialization_with_node_matrix(tmp_path):
    with patch("shutil.which", return_value="/usr/bin/mpirun"):
        node_matrix = {"node1": 2, "node2": 2}
        mpi_node = MpiNode(node_matrix=node_matrix)
        assert mpi_node.nproc == 4
        assert mpi_node.node_matrix == node_matrix
        assert mpi_node.node_file is not None
        node_file_path = tmp_path / mpi_node.node_file
        # Simulate the creation of node file
        with open(node_file_path, "w") as f:
            f.write("node1 slots=2\nnode2 slots=2\n")
        assert mpi_node.host_file == [mpi_node.mpi_executable, "--hostfile", mpi_node.node_file]


@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_mpi_node_apply():
    with patch("shutil.which", return_value="/usr/bin/mpirun"):
        mpi_node = MpiNode(nproc=4)
        cmd = ["rosetta_scripts", "-s", "input.pdb"]
        with mpi_node.apply(cmd) as updated_cmd:
            expected_cmd = mpi_node.local + cmd
            assert updated_cmd == expected_cmd


@patch.dict(
    os.environ, {"SLURM_JOB_NODELIST": "node01\nnode02", "SLURM_CPUS_PER_TASK": "2", "SLURM_NTASKS_PER_NODE": "1"}
)
@patch("subprocess.check_output")
def test_mpi_node_from_slurm(mock_check_output):
    mock_check_output.return_value = b"node01\nnode02\n"
    with patch("shutil.which", return_value="/usr/bin/mpirun"):
        mpi_node = MpiNode.from_slurm()
        assert mpi_node.nproc == 4
        assert mpi_node.node_matrix == {"node01": 2, "node02": 2}
