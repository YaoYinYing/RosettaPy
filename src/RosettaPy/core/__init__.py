"""
Core execution vocabulary for RosettaPy v2.

This package defines the minimum vocabulary required to describe a reproducible
Rosetta computation: tasks, results, artifacts, resource requests, execution
errors, and the executor protocol.

``core`` is intentionally small and MUST NOT import Rosetta-specific modules,
concrete executors, schedulers, container or MPI support, workflows, or
analyzers. It defines *what* a task and a result are; executors define *how* one
task is run.
"""

from .artifact import Artifact, ArtifactExpectation, ArtifactManifest, ArtifactRole
from .errors import (
    BinaryResolutionError,
    CompilationError,
    ExecutionError,
    RosettaPyError,
)
from .executor import Executor
from .result import (
    RUN_MANIFEST_SCHEMA_VERSION,
    ExecutionResult,
    ExecutionStatus,
    RunManifest,
)
from .task import ResourceRequest, TaskSpec

__all__ = [
    "Artifact",
    "ArtifactExpectation",
    "ArtifactManifest",
    "ArtifactRole",
    "BinaryResolutionError",
    "CompilationError",
    "ExecutionError",
    "ExecutionResult",
    "ExecutionStatus",
    "Executor",
    "ResourceRequest",
    "RosettaPyError",
    "RunManifest",
    "RUN_MANIFEST_SCHEMA_VERSION",
    "TaskSpec",
]
