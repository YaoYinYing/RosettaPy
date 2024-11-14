import os
import platform
from unittest.mock import MagicMock, patch

import pytest

from RosettaPy.node import MpiNode, Native, RosettaContainer, WslWrapper, node_picker
from RosettaPy.rosetta_finder import RosettaBinary


# Helper function to handle common assertions
def assert_node_attributes(node, expected_class, expected_attributes):
    assert isinstance(node, expected_class)
    for attr_name, expected_value in expected_attributes.items():
        actual_value = getattr(node, attr_name)
        assert actual_value == expected_value, f"Attribute {attr_name} expected {expected_value}, got {actual_value}"


# Helper function to handle common exception checks
def check_exception(node_type, kwargs, expected_exception, match):
    with pytest.raises(expected_exception, match=match):
        node_picker(node_type=node_type, **kwargs)


# A good practice to mock `platform.uname()`
# Test cases
@pytest.mark.parametrize("mock_system_as", [None, "Windows", "Linux", "Darwin"])
@pytest.mark.parametrize(
    "node_type, kwargs, expected_class, expected_attributes",
    [
        (
            "docker",
            {},
            RosettaContainer,
            {
                "image": "rosettacommons/rosetta:latest",
                "prohibit_mpi": True,
                "nproc": 4,
            },
        ),
        (
            "docker",
            {"image": "custom/image", "prohibit_mpi": False, "nproc": 8},
            RosettaContainer,
            {
                "image": "custom/image",
                "prohibit_mpi": False,
                "nproc": 8,
            },
        ),
        (
            "docker_mpi",
            {},
            RosettaContainer,
            {
                "image": "rosettacommons/rosetta:mpi",
                "prohibit_mpi": False,
                "mpi_available": True,
                "nproc": 4,
            },
        ),
        (
            "wsl",
            {"rosetta_bin": "/path/to/rosetta_bin"},
            WslWrapper,
            {
                "rosetta_bin": RosettaBinary.from_filename(
                    dirname=os.path.dirname(os.path.abspath("/path/to/rosetta_bin")),
                    filename=os.path.basename(os.path.abspath("/path/to/rosetta_bin")),
                ),
                "distro": "ubuntu",
                "user": "root",
                "nproc": 4,
                "prohibit_mpi": True,
                "mpi_available": False,
            },
        ),
        (
            "wsl_mpi",
            {"rosetta_bin": "/path/to/rosetta_bin"},
            WslWrapper,
            {
                "rosetta_bin": RosettaBinary.from_filename(
                    dirname=os.path.dirname(os.path.abspath("/path/to/rosetta_bin")),
                    filename=os.path.basename(os.path.abspath("/path/to/rosetta_bin")),
                ),
                "distro": "ubuntu",
                "user": "root",
                "nproc": 4,
                "prohibit_mpi": False,
                "mpi_available": True,
            },
        ),
        (
            "mpi",
            {},
            MpiNode,
            {
                "nproc": 4,
            },
        ),
        (
            None,
            {},
            Native,
            {
                "nproc": 4,
            },
        ),
    ],
)
def test_node_picker(node_type, kwargs, expected_class, expected_attributes, mock_system_as):
    # if needed, fetch a real system name
    real_system = platform.system()
    if node_type is None:
        node_type = "native"

    # do the patch
    with patch(
        "platform.uname",
        return_value=(
            MagicMock(system=mock_system_as) if mock_system_as is not None else MagicMock(system=real_system)
        ),
    ):
        # Check if the mocked system works
        assert platform.system() == mock_system_as if mock_system_as is not None else real_system

        # Handle WSL-specific checks
        # call mocked `platform.system()` as you like
        if str(node_type).startswith("wsl"):
            check_exception(
                node_type,
                kwargs,
                RuntimeError,
                (
                    "WslWrapper is only available on Windows."
                    if platform.system() != "Windows"
                    else "WSL is not available."
                ),
            )
            return

        # Handle native/mpi-specific checks
        if (node_type == "native" or node_type == "mpi") and platform.system() == "Windows":
            check_exception(node_type, kwargs, RuntimeError, "Windows is not supported for")
            return

        with patch("shutil.which", return_value="/usr/local/bin/mpirun"):
            node = node_picker(node_type=node_type, **kwargs)
        assert_node_attributes(node, expected_class, expected_attributes)
