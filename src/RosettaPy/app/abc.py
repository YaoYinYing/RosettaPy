"""
High-level Rosetta application base class
"""

import os
from abc import ABC
from typing import Any, List, Mapping, Optional, Tuple

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
        self.user_opts = user_opts or []
        self._node_hint: NodeHintT = node_hint
        self._node_config = node_config

        self.kwargs = kwargs

        # Create job directory and ensure save directory is absolute path
        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

        self._node = self._get_node(self._node_hint, self._node_config or {})

    @property
    def node(self) -> NodeClassType:

        return self._node

    @node.setter
    def node(self, node_setting: Tuple[Optional[NodeHintT], Optional[Mapping[str, Any]]] = (None, None)):
        """Update the node by (hint, config). Pass None to keep current value."""
        if node_setting == (None, None):
            return
        hint, config = node_setting
        if hint is not None:
            self._node_hint = hint
        if config is not None:
            self._node_config = config
        self._node = self._get_node(self.node_hint, self.node_config)

    @property
    def node_hint(self) -> NodeHintT:
        """
        Get the node hint information

        Returns:
            NodeHintT: The node hint information
        """
        return self._node_hint

    @property
    def node_config(self) -> Mapping[str, Any]:
        """
        Get the node configuration information

        Returns:
            Mapping[str, Any]: Node configuration dictionary, returns empty dict if not set
        """
        return self._node_config or {}

    @staticmethod
    def _get_node(node_hint: NodeHintT, node_config: Mapping[str, Any]) -> NodeClassType:
        """
        Get the appropriate node instance based on hint and configuration

        Args:
            node_hint (NodeHintT): Type of node to create
            node_config (Mapping[str, Any]): Configuration parameters for node creation

        Returns:
            NodeClassType: Initialized node instance
        """
        return node_picker(node_type=node_hint, **node_config)
