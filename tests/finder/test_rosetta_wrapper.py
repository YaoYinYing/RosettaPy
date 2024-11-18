import os
import shutil
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from RosettaPy import RosettaBinary, RosettaFinder

# Import the classes from your module
from RosettaPy.node.native import Native
from RosettaPy.rosetta import MpiIncompatibleInputWarning, MpiNode, Rosetta
from RosettaPy.utils import (
    RosettaCmdTask,
    RosettaScriptsVariable,
    RosettaScriptsVariableGroup,
    timing,
)
from RosettaPy.utils.task import execute
from tests.conftest import github_rosetta_test


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


def test_timing(capfd):
    import time

    with timing("Test timing"):
        time.sleep(0.1)  # Sleep for 100 ms

    out, err = capfd.readouterr()
    assert "Test timing" in out
    assert "Started" in out
    assert "Finished" in out


@patch("shutil.which", return_value=None)
@patch("subprocess.Popen")
def test_rosetta_run_local(mock_popen, mock_which, mock_rosetta_bin):
    os.environ["ROSETTA_BIN"] = os.path.dirname(mock_rosetta_bin)

    nstruct = 10

    # Create the RosettaBinary manually
    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")
    # Mock the process
    mock_process = MagicMock()
    mock_popen.return_value = mock_process

    rosetta = Rosetta(
        bin=rosetta_binary,
        run_node=Native(
            nproc=2,
        ),
        flags=["tests/data/flag_ending/ddG_relax.lf.flag"],
        opts=["-in:file:s", "tests/data/3fap_hf3_A_short.pdb"],
        verbose=True,
    )
    cmd = rosetta.compose()

    assert cmd == [
        rosetta_binary.full_path,
        f"@{os.path.abspath('tests/data/flag_ending/ddG_relax.lf.flag')}",
        "-in:file:s",
        "tests/data/3fap_hf3_A_short.pdb",
    ]

    ret = rosetta.run(nstruct=nstruct)

    assert len(ret) == nstruct
    assert all(isinstance(r, RosettaCmdTask) for r in ret)


# Test RosettaBinary.from_filename with valid filenames
@pytest.mark.parametrize(
    "user,uid,userstring",
    [("root", 0, "--allow-run-as-root"), ("debian", 8964, "")],
)
@patch("os.path.isfile", return_value=True)
@patch("subprocess.Popen")
@pytest.mark.skipif(github_rosetta_test(), reason="No need to run this test in Dockerized Rosetta.")
def test_rosetta_run_mpi(mock_popen, mock_isfile, mock_rosetta_mpi_bin, user, uid, userstring):
    os.environ["ROSETTA_BIN"] = os.path.dirname(mock_rosetta_mpi_bin)

    # Mock the Rosetta binary with MPI mode
    rosetta_binary = RosettaBinary(
        os.path.dirname(mock_rosetta_mpi_bin), "rosetta_scripts", "mpi", "linux", "gcc", "release"
    )
    with patch("shutil.which", return_value="/usr/bin/mpirun"):
        mpi_node = MpiNode(nproc=4)
        mpi_node.user = uid

        rosetta = Rosetta(bin=rosetta_binary, run_node=mpi_node, verbose=True, use_mpi=True)

    # Mock the process
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("Output", "")
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    base_cmd = rosetta.compose()

    if user == "root":
        with pytest.warns(UserWarning, match="Running Rosetta with MPI as Root User"):
            tasks = rosetta.setup_tasks_with_node(base_cmd=base_cmd, nstruct=2)

    else:
        tasks = rosetta.setup_tasks_with_node(base_cmd=base_cmd, nstruct=2)
    mpi_node.run(tasks=tasks)

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
def test_rosetta_init_no_mpi_executable(mock_which, mock_rosetta_static_bin):
    os.environ["ROSETTA_BIN"] = os.path.dirname(mock_rosetta_static_bin)

    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")

    with pytest.raises(RuntimeError, match="No supported MPI executable found in PATH"):
        Rosetta(bin=rosetta_binary, run_node=MpiNode(nproc=0, node_matrix={"node1": 1}))


@pytest.mark.parametrize(
    "flag_basename,contains_crlf",
    [("ddG_relax.lf.flag", False), ("ddG_relax.crlf.flag", True)],
)
def test_rosetta_compose(flag_basename, contains_crlf, mock_rosetta_bin):
    os.environ["ROSETTA_BIN"] = os.path.dirname(mock_rosetta_bin)

    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")

    rosetta = Rosetta(
        bin=rosetta_binary,
        flags=[f"tests/data/flag_ending/{flag_basename}"],
        opts=["-in:file:s", "tests/data/3fap_hf3_A_short.pdb"],
        verbose=True,
    )

    expected_cmd = [
        rosetta_binary.full_path,
        f"@{os.path.abspath(f'tests/data/flag_ending/{flag_basename}')}",
        "-in:file:s",
        "tests/data/3fap_hf3_A_short.pdb",
    ]

    if contains_crlf:
        with pytest.warns(UserWarning):
            cmd = rosetta.compose()
        # Verify the command structure while allowing for line ending differences
        assert len(cmd) == len(expected_cmd)
        assert cmd[0] == expected_cmd[0]  # Binary path should match
        assert cmd[2:] == expected_cmd[2:]  # Options after flag file should match
        # Flag file path might differ due to line ending conversion
        assert cmd[1].startswith("@") and cmd[1].endswith(flag_basename)
        return

    cmd = rosetta.compose()
    assert cmd == expected_cmd


def test_rosetta_use_implicit_mpi_binary(mock_rosetta_bin_container):
    os.environ["ROSETTA_BIN"] = os.path.dirname(mock_rosetta_bin_container)
    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")
    assert rosetta_binary.mode is None

    with patch("shutil.which", return_value="/usr/bin/mpirun"):
        mpi_node = MpiNode(nproc=4)

    assert mpi_node.mpi_available

    with pytest.warns(
        UserWarning,
        match="MPI nodes are configured and called, yet the binary does not explicitly support MPI mode. ",
    ):
        Rosetta(bin=rosetta_binary, run_node=mpi_node, use_mpi=True)


def test_rosetta_mpi_disabled_warning(mock_rosetta_mpi_bin):
    os.environ["ROSETTA_BIN"] = os.path.dirname(mock_rosetta_mpi_bin)

    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")
    assert rosetta_binary.mode == "mpi"

    with pytest.warns(
        UserWarning,
        match="The binary supports MPI mode, yet the job is not configured to use MPI.",
    ):
        rosetta = Rosetta(bin=rosetta_binary, use_mpi=False)
        assert not rosetta.use_mpi


@patch("shutil.which", return_value="/usr/bin/mpirun")
@patch("subprocess.Popen")
def test_rosetta_execute_failure(mock_popen, mock_which, mock_rosetta_static_bin):
    os.environ["ROSETTA_BIN"] = os.path.dirname(mock_rosetta_static_bin)

    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")

    rosetta = Rosetta(bin=rosetta_binary)

    # Mock a process that returns a non-zero exit code
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("Output", "Error")
    mock_process.wait.return_value = 1
    mock_popen.return_value = mock_process

    with pytest.raises(RuntimeError):
        invalid_task = RosettaCmdTask(cmd=["invalid_command"])
        execute(invalid_task)

    # Verify that the command was attempted
    mock_popen.assert_called_once()


@patch("subprocess.Popen")
def test_rosetta_mpi_incompatible_input_warning(mock_popen, mock_rosetta_mpi_bin):
    os.environ["ROSETTA_BIN"] = os.path.dirname(mock_rosetta_mpi_bin)

    rosetta_binary = RosettaFinder().find_binary("rosetta_scripts")

    with patch("shutil.which", return_value="/usr/bin/mpirun"):
        mpi_node = MpiNode(nproc=4)

    rosetta = Rosetta(bin=rosetta_binary, run_node=mpi_node, use_mpi=True)

    # Mock the process
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("Output", "")
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    with pytest.warns(
        MpiIncompatibleInputWarning,
        match="Customized inputs for MPI nodes will be flattened and passed to the master node",
    ):
        rosetta.run(inputs=[{"-in:file:s": "input1.pdb"}, {"-in:file:s": "input2.pdb"}])
