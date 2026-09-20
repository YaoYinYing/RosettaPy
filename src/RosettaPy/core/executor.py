"""
The executor boundary.

An executor turns one :class:`~RosettaPy.core.task.TaskSpec` into one
:class:`~RosettaPy.core.result.ExecutionResult`. The protocol is deliberately
minimal: there is no ``execute_many`` requirement in the initial kernel. Batch
orchestration belongs outside this protocol and may later call ``execute``
concurrently.

Executor lifecycle phases such as prepare, launch, collect, and cleanup are
internal implementation structure, not public protocol methods, and the entity
identity distinguishes ``core`` (which is generic) from orchestration:

    core      defines what a task and a result are;
    executors implement how one task is run.

Environment errors follow the v2 failure rule: a failure to *launch* raises
:class:`~RosettaPy.core.errors.ExecutionError`, while a process that runs and
exits non-zero returns a ``FAILED`` result.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .result import ExecutionResult
from .task import TaskSpec


@runtime_checkable
class Executor(Protocol):
    """
    Structural contract for anything that can execute a task.

    A conforming executor:

    - declares a stable :attr:`identity` string that is recorded in result
      provenance and the run manifest;
    - accepts any valid ``TaskSpec`` without knowing which Rosetta workflow
      produced it;
    - returns an ``ExecutionResult`` for every process it successfully starts;
    - raises ``ExecutionError`` only when the execution environment cannot be
      established or maintained.
    """

    @property
    def identity(self) -> str:
        """Stable executor identity, for example ``"native"``."""
        ...  # pragma: no cover - protocol declaration

    def execute(self, task: TaskSpec) -> ExecutionResult:
        """
        Execute one task and return a structured result.

        Args:
            task: The task description to run.

        Returns:
            The structured result of the execution.
        """
        ...  # pragma: no cover - protocol declaration
