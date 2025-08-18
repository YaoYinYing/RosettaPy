import os
from abc import ABC
from typing import Any, List, Mapping, Optional

from RosettaPy.node import NodeClassType, NodeHintT, node_picker


class RosettaAppBase(ABC):
    """
    Base class for Rosetta applications
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

        self.job_id = job_id
        self.save_dir = save_dir
        self.user_opts = user_opts or {}

        self.kwargs = kwargs
        self.node: NodeClassType = self._get_node(node_hint, node_config or {})

        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

    def _get_node(self, node_hint: NodeHintT, node_config: Mapping[str, Any]) -> NodeClassType:
        return node_picker(node_type=node_hint, **node_config)
