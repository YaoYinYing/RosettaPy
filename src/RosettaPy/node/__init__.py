"""
Node classes for Rosetta Runs.
"""

# pylint: disable=too-few-public-methods

from typing import Literal, Optional, TypeVar, Union

from .dockerized import RosettaContainer
from .mpi import MpiNode
from .native import Native
from .wsl import WslWrapper

NodeT = TypeVar("NodeT", Native, MpiNode, RosettaContainer, WslWrapper)
NodeHintT = Literal["docker", "docker_mpi", "mpi", "wsl", "wsl_mpi", "native"]
NodeClassType = Union[Native, MpiNode, RosettaContainer, WslWrapper]


def node_picker(node_type: Optional[NodeHintT] = None, **kwargs) -> NodeClassType:
    """Choose the node to run the tests on."""

    if node_type == "docker":
        return RosettaContainer(image="rosettacommons/rosetta:mpi", prohibit_mpi=True, **kwargs)

    if node_type == "docker_mpi":
        return RosettaContainer(image="rosettacommons/rosetta:mpi", prohibit_mpi=False, mpi_available=True, **kwargs)

    if node_type == "wsl":
        return WslWrapper(**kwargs)

    if node_type == "wsl_mpi":
        return WslWrapper(**kwargs)

    if node_type == "mpi":
        return MpiNode(nproc=kwargs.get("nproc", 4))

    return Native(nproc=kwargs.get("nproc", 4))


__all__ = ["NodeT", "NodeHintT", "Native", "MpiNode", "RosettaContainer", "WslWrapper", "node_picker"]
