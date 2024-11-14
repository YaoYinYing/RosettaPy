"""
Node classes for Rosetta Runs.
"""

# pylint: disable=too-few-public-methods
import os
from typing import Any, Literal, Optional, TypeVar, Union

from ..rosetta_finder import RosettaBinary
from .dockerized import RosettaContainer
from .mpi import MpiNode
from .native import Native
from .wsl import WslWrapper

NodeT = TypeVar("NodeT", Native, MpiNode, RosettaContainer, WslWrapper)
NodeHintT = Literal["docker", "docker_mpi", "mpi", "wsl", "wsl_mpi", "native"]
NodeClassType = Union[Native, MpiNode, RosettaContainer, WslWrapper]


def node_picker(node_type: Optional[NodeHintT] = None, **kwargs) -> NodeClassType:
    """
    Choose the node to run the tests on.

    Parameters:
    - node_type (Optional[NodeHintT]): A hint specifying the type of node to be chosen. If not provided,
      the function will choose a default node based on the available options.
    - kwargs: Additional keyword arguments that may be used to configure the chosen node.

    Returns:
    - NodeClassType: An instance of the chosen node class.

    The function uses the provided `node_type` and `kwargs` to select and configure the appropriate node.
    If `node_type` is not provided, the function will choose a default node based on the available options.
    The function supports the following `node_type` hints:
    - "docker": Selects a Docker-based Rosetta node.
    - "docker_mpi": Selects a Docker-based Rosetta node with MPI support.
    - "wsl": Selects a WSL (Windows Subsystem for Linux) wrapper for Rosetta.
    - "wsl_mpi": Selects a WSL wrapper for Rosetta with MPI support.
    - "mpi": Selects a native MPI node.
    - If `node_type` is not provided, the function will choose a default node based on the available options.

    The `kwargs` parameter allows for additional configuration options to be passed to the chosen node.
    The available configuration options depend on the chosen `node_type`.
    """

    def pop_if(key: str, default: Any):
        """
        Removes the specified key from the kwargs dictionary if it exists and returns its value.
        If the key does not exist, returns the default value.

        Parameters:
        key (str): The key to be removed from the kwargs dictionary.
        default (Any): The value to return if the key is not found in the kwargs dictionary.

        Returns:
        Any: The value associated with the key if it exists, otherwise the default value.
        """
        if key in kwargs:
            return kwargs.pop(key)
        return default

    if node_type == "docker":
        return RosettaContainer(
            image=pop_if("image", "rosettacommons/rosetta:latest"),
            prohibit_mpi=pop_if("prohibit_mpi", True),
            nproc=pop_if("nproc", 4),
        )

    if node_type == "docker_mpi":
        return RosettaContainer(
            image=pop_if("image", "rosettacommons/rosetta:mpi"),
            prohibit_mpi=pop_if("prohibit_mpi", False),
            mpi_available=pop_if("mpi_available", True),
            nproc=pop_if("nproc", 4),
        )

    if node_type == "wsl":
        rosetta_bin = os.path.abspath(kwargs.pop("rosetta_bin"))
        return WslWrapper(
            rosetta_bin=RosettaBinary.from_filename(
                dirname=os.path.dirname(rosetta_bin), filename=os.path.basename(rosetta_bin)
            ),
            distro=pop_if("distro", "ubuntu"),
            user=pop_if("user", "root"),
            nproc=pop_if("nproc", 4),
            prohibit_mpi=pop_if("prohibit_mpi", True),
            mpi_available=False,
        )

    if node_type == "wsl_mpi":
        rosetta_bin = os.path.abspath(kwargs.pop("rosetta_bin"))
        return WslWrapper(
            rosetta_bin=RosettaBinary.from_filename(
                dirname=os.path.dirname(rosetta_bin), filename=os.path.basename(rosetta_bin)
            ),
            distro=pop_if("distro", "ubuntu"),
            user=pop_if("user", "root"),
            nproc=pop_if("nproc", 4),
            prohibit_mpi=pop_if("prohibit_mpi", False),
            mpi_available=True,
        )

    if node_type == "mpi":
        return MpiNode(nproc=pop_if("nproc", 4))

    return Native(nproc=pop_if("nproc", 4))


__all__ = ["NodeT", "NodeHintT", "Native", "MpiNode", "RosettaContainer", "WslWrapper", "node_picker"]
