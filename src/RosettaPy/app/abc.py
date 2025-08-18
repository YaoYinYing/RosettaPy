"""
High-level Rosetta application base class
"""

import os
from abc import ABC
from typing import Any, List, Mapping, Optional

from RosettaPy.node import NodeClassType, NodeHintT, node_picker


class RosettaAppBase(ABC):
    """
    Base class for Rosetta applications

    This class serves as the foundation for all Rosetta applications, providing
    common functionality for job management, directory setup, and node configuration.
    """

    def __init__(
        self,
        job_id: str,
        save_dir: str,
        user_opts: Optional[List[str]] = None,
        node_hint: NodeHintT = "native",
        node_config: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> None:
        """
        Initialize the Rosetta application base class

        Args:
            job_id (str): Unique identifier for the job
            save_dir (str): Directory path where job results will be saved
            user_opts (Optional[List[str]]): List of user-specified options, defaults to None
            node_hint (NodeHintT): Hint for node type selection, defaults to "native"
            node_config (Optional[Mapping[str, Any]]): Configuration parameters for the node, defaults to None
            **kwargs: Additional keyword arguments for extended functionality

        Returns:
            None
        """

        self.job_id = job_id
        self.save_dir = save_dir
        self.user_opts = user_opts or {}

        self.kwargs = kwargs
        self.node: NodeClassType = self._get_node(node_hint, node_config or {})

        # Create job directory and ensure save directory is absolute path
        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

    def _get_node(self, node_hint: NodeHintT, node_config: Mapping[str, Any]) -> NodeClassType:
        """
        Get the appropriate node instance based on hint and configuration

        Args:
            node_hint (NodeHintT): Type of node to create
            node_config (Mapping[str, Any]): Configuration parameters for node creation

        Returns:
            NodeClassType: Initialized node instance
        """
        return node_picker(node_type=node_hint, **node_config)
