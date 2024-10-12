import os
import sys
import shutil
import subprocess
import tempfile
from unittest.mock import patch, MagicMock, mock_open
import warnings

import pytest

# Import the classes from your module
from RosettaPy.rosetta import (
    MPI_node,
    Rosetta,
    MPI_IncompatibleInputWarning,
)
from RosettaPy.utils import timing, RosettaScriptsVariable, RosettaScriptsVariableGroup, RosettaCmdTask
from RosettaPy import RosettaFinder, RosettaBinary

from tests.conftest import github_rosetta_test


### Testing RosettaScriptsVariable ###
@pytest.fixture
def temp_dir():
    # Create a temporary directory
    dirpath = tempfile.mkdtemp()
    yield dirpath
    # Clean up after test
    shutil.rmtree(dirpath)


def test_rosetta_scripts_variable():
    variable = RosettaScriptsVariable(k="input_pdb", v="test.pdb")
    assert variable.k == "input_pdb"
    assert variable.v == "test.pdb"
    assert variable.aslist == ["-parser:script_vars", "input_pdb=test.pdb"]


def test_rosetta_script_variables_empty():
    with pytest.raises(ValueError):
        RosettaScriptsVariableGroup.from_dict({})


def test_rosetta_script_variables_apply_on_xml():
    xml_content = """<Reweight scoretype="coordinate_constraint" weight="%%cst_value%%"/>"""
    rsv = RosettaScriptsVariableGroup.from_dict(var_pair={"cst_value": "0.4"})
    updated_xml_content = rsv.apply_to_xml_content(xml_content)
    assert updated_xml_content == """<Reweight scoretype="coordinate_constraint" weight="0.4"/>"""


def test_rosetta_script_variables_apply_many_on_xml():
    xml_content = """<Reweight scoretype="coordinate_constraint" weight="%%cst_value%%"/>
    <PreventResiduesFromRepacking name="fix_res" reference_pdb_id="%%pdb_reference%%" residues="%%res_to_fix%%"/>"""
    rsv = RosettaScriptsVariableGroup.from_dict(
        var_pair={"cst_value": "0.4", "pdb_reference": "pdb1.pdb", "res_to_fix": "1A,2C"}
    )
    updated_xml_content = rsv.apply_to_xml_content(xml_content)
    assert (
        updated_xml_content
        == """<Reweight scoretype="coordinate_constraint" weight="0.4"/>
    <PreventResiduesFromRepacking name="fix_res" reference_pdb_id="pdb1.pdb" residues="1A,2C"/>"""
    )


def test_rosetta_script_variables():
    variables_dict = {"input_pdb": "test.pdb", "output_pdb": "result.pdb"}
    script_variables = RosettaScriptsVariableGroup.from_dict(variables_dict)
    assert not script_variables.empty
    assert len(script_variables.variables) == 2
    expected_longlist = ["-parser:script_vars", "input_pdb=test.pdb", "-parser:script_vars", "output_pdb=result.pdb"]
    assert script_variables.aslonglist == expected_longlist


### Testing timing context manager ###


def test_timing(capfd):
    import time

    with timing("Test timing"):
        time.sleep(0.1)  # Sleep for 100 ms

    out, err = capfd.readouterr()
    assert "Test timing" in out
    assert "Started" in out
    assert "Finished" in out


### Testing MPI_node ###


def test_mpi_node_initialization_without_node_matrix():
    with patch("shutil.which", return_value="/usr/bin/mpirun"):
        mpi_node = MPI_node(nproc=4)
        assert mpi_node.nproc == 4
        assert mpi_node.node_matrix is None
        assert mpi_node.mpi_excutable == "/usr/bin/mpirun"
        assert mpi_node.local == [mpi_node.mpi_excutable, "--use-hwthread-cpus", "-np", "4"]


def test_mpi_node_initialization_with_node_matrix(tmp_path):
    with patch("shutil.which", return_value="/usr/bin/mpirun"):
        node_matrix = {"node1": 2, "node2": 2}
        mpi_node = MPI_node(node_matrix=node_matrix)
        assert mpi_node.nproc == 4
        assert mpi_node.node_matrix == node_matrix
        assert mpi_node.node_file is not None
        node_file_path = tmp_path / mpi_node.node_file
        # Simulate the creation of node file
        with open(node_file_path, "w") as f:
            f.write("node1 slots=2\nnode2 slots=2\n")
        assert mpi_node.host_file == [mpi_node.mpi_excutable, "--hostfile", mpi_node.node_file]


@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_mpi_node_apply():
    with patch("shutil.which", return_value="/usr/bin/mpirun"):
        mpi_node = MPI_node(nproc=4)
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
        mpi_node = MPI_node.from_slurm()
        assert mpi_node.nproc == 4
        assert mpi_node.node_matrix == {"node01": 2, "node02": 2}


### Testing Rosetta ###


@patch("shutil.which", return_value=None)
@patch("os.path.isfile", return_value=True)
@patch("subprocess.Popen")
def test_rosetta_run_local(mock_popen, mock_isfile, mock_which, temp_dir):

    file_path = os.path.join(temp_dir, "rosetta_scripts.linuxgccrelease")
    os.environ["ROSETTA_BIN"] = temp_dir

    with open(file_path, "w") as f:
        f.write('#!/bin/bash\necho "Mock Rosetta binary"')
    os.chmod(file_path, 0o755)

    nstruct = 10

    # Create the RosettaBinary manually
    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")
    # Mock the process
    mock_process = MagicMock()
    # mock_process.communicate.return_value = None
    # mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    rosetta = Rosetta(bin=rosetta_binary, nproc=2, flags=["flags.txt"], opts=["-in:file:s", "input.pdb"], verbose=True)
    cmd = rosetta.compose()

    assert cmd == [rosetta_binary.full_path, f"@{os.path.abspath('flags.txt')}", "-in:file:s", "input.pdb"]

    ret = rosetta.run(nstruct=nstruct)

    assert len(ret) == nstruct
    assert all(isinstance(r, RosettaCmdTask) for r in ret)


# Test RosettaBinary.from_filename with valid filenames
@pytest.mark.parametrize(
    "user,uid,userstring",
    [("root", 0, "--allow-run-as-root"), ("debian", 8964, "")],
)
@patch("shutil.which", return_value="/usr/bin/mpirun")
@patch("os.path.isfile", return_value=True)
@patch("subprocess.Popen")
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_rosetta_run_mpi(mock_popen, mock_isfile, mock_which, temp_dir, user, uid, userstring):

    file_path = os.path.join(temp_dir, "rosetta_scripts.mpi.linuxgccrelease")
    os.environ["ROSETTA_BIN"] = temp_dir

    with open(file_path, "w") as f:
        f.write("")  # Create an empty file
    os.chmod(str(file_path), 0o755)

    # Mock the Rosetta binary with MPI mode
    rosetta_binary = RosettaBinary(temp_dir, "rosetta_scripts", "mpi", "linux", "gcc", "release")
    mpi_node = MPI_node(nproc=4)
    mpi_node.user = uid
    rosetta = Rosetta(bin=rosetta_binary, run_node=mpi_node, verbose=True)

    # Mock the process
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("Output", "")
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    base_cmd = rosetta.compose()

    if user == "root":
        with pytest.warns(UserWarning) as record:
            tasks = rosetta.setup_tasks_mpi(base_cmd=base_cmd, nstruct=2)

            assert any("Running Rosetta with MPI as Root User" in str(warning.message) for warning in record)

    else:
        tasks = rosetta.setup_tasks_mpi(base_cmd=base_cmd, nstruct=2)
    rosetta.run_mpi(tasks=tasks)

    # Verify that the execute method was called once
    mock_popen.assert_called_once()

    expected_cmd = mpi_node.local + [userstring]
    while "" in expected_cmd:
        expected_cmd.remove("")

    expected_cmd.extend([rosetta_binary.full_path, "-nstruct", "2"])
    mock_popen.assert_called_with(
        expected_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf-8"
    )


@patch("shutil.which", return_value=None)
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_rosetta_init_no_mpi_executable(mock_which, temp_dir):
    file_path = os.path.join(temp_dir, "rosetta_scripts.static.linuxgccrelease")
    os.environ["ROSETTA_BIN"] = temp_dir

    with open(file_path, "w") as f:
        f.write("")  # Create an empty file
    os.chmod(str(file_path), 0o755)

    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")

    with pytest.warns(UserWarning) as record:
        Rosetta(bin=rosetta_binary, run_node=MPI_node(0, {"node1": 1}))

    assert any("MPI nodes are given yet not supported" in str(warning.message) for warning in record)


@patch("os.path.isfile", return_value=True)
def test_rosetta_compose(mock_isfile, temp_dir):
    file_path = os.path.join(temp_dir, "rosetta_scripts.mpi.linuxgccrelease")
    os.environ["ROSETTA_BIN"] = temp_dir

    with open(file_path, "w") as f:
        f.write("")  # Create an empty file
    os.chmod(str(file_path), 0o755)
    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")

    rosetta = Rosetta(bin=rosetta_binary, flags=["flags.txt"], opts=["-in:file:s", "input.pdb"], verbose=True)

    expected_cmd = [rosetta_binary.full_path, f"@{os.path.abspath('flags.txt')}", "-in:file:s", "input.pdb"]
    cmd = rosetta.compose()
    assert cmd == expected_cmd


@patch("shutil.which", return_value="/usr/bin/mpirun")
def test_rosetta_mpi_warning(mock_which, temp_dir):
    file_path = os.path.join(temp_dir, "rosetta_scripts.mpi.linuxgccrelease")
    os.environ["ROSETTA_BIN"] = temp_dir

    with open(file_path, "w") as f:
        f.write("")  # Create an empty file
    os.chmod(str(file_path), 0o755)
    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")

    with pytest.warns(UserWarning) as record:
        rosetta = Rosetta(bin=rosetta_binary)
        assert rosetta.use_mpi is False

    assert any("Using MPI binary as static build." in str(warning.message) for warning in record)


### Testing execution with invalid command ###


@patch("shutil.which", return_value="/usr/bin/mpirun")
@patch("subprocess.Popen")
def test_rosetta_execute_failure(mock_popen, mock_which, temp_dir):
    file_path = os.path.join(temp_dir, "rosetta_scripts.static.linuxgccrelease")
    os.environ["ROSETTA_BIN"] = temp_dir

    with open(file_path, "w") as f:
        f.write("")  # Create an empty file
    os.chmod(str(file_path), 0o755)
    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")

    rosetta = Rosetta(bin=rosetta_binary)

    # Mock a process that returns a non-zero exit code
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("Output", "Error")
    mock_process.wait.return_value = 1
    mock_popen.return_value = mock_process

    with pytest.raises(RuntimeError):
        invalid_task = RosettaCmdTask(cmd=["invalid_command"])
        rosetta.execute(invalid_task)

    # Verify that the command was attempted
    mock_popen.assert_called_once()


### Testing MPI_IncompatibleInputWarning ###


@patch("subprocess.Popen")
@patch("shutil.which", return_value="/usr/bin/mpirun")
def test_rosetta_mpi_incompatible_input_warning(mock_which, mock_popen, temp_dir):
    file_path = os.path.join(temp_dir, "rosetta_scripts.mpi.linuxgccrelease")
    os.environ["ROSETTA_BIN"] = temp_dir

    with open(file_path, "w") as f:
        f.write("")  # Create an empty file
    os.chmod(str(file_path), 0o755)

    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")

    mpi_node = MPI_node(nproc=4)
    rosetta = Rosetta(bin=rosetta_binary, run_node=mpi_node)

    # Mock the process
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("Output", "")
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    with pytest.warns(MPI_IncompatibleInputWarning) as record:
        rosetta.run(inputs=[{"-in:file:s": "input1.pdb"}, {"-in:file:s": "input2.pdb"}])

    assert any(
        "Customized Inputs for MPI nodes will be flattened and passed to master node" in str(warning.message)
        for warning in record
    )
