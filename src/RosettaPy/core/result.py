"""
The execution result contract.

The v2 failure rule is implemented here: a process that starts and exits with a
non-zero code produces an :class:`ExecutionResult` with
:attr:`ExecutionStatus.FAILED`. Only the inability to establish or maintain
execution raises a
:class:`~RosettaPy.core.errors.ExecutionError`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Mapping, Union

from ._json import freeze_json_mapping
from .artifact import ArtifactManifest

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ._json import JSONValue
    from .task import TaskSpec

RUN_MANIFEST_SCHEMA_VERSION = 1
"""Version of the on-disk run manifest schema.

The serialized schema is an interoperability contract that is versioned
independently from the Python object layout, so external consumers (for example
REvoCompute) can read a manifest without importing RosettaPy.
"""


class ExecutionStatus(str, Enum):
    """
    Outcome of one executed task.

    ``TIMED_OUT`` and ``CANCELLED`` reserve schema space for later milestones;
    only ``SUCCEEDED`` and ``FAILED`` are produced by the first execution
    implementation.
    """

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"

    def __str__(self) -> str:  # pragma: no cover - display helper
        return self.value


def _format_timestamp(value: datetime) -> str:
    """Render a timestamp as ISO-8601 in UTC, regardless of local timezone."""
    return value.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """
    The structured outcome of one task.

    Attributes:
        task_id: Identifier of the task this result belongs to.
        status: Execution status.
        exit_code: Process exit code, or ``None`` when the process never
            produced one.
        stdout: Captured standard output.
        stderr: Captured standard error.
        started_at: Timezone-aware start timestamp.
        finished_at: Timezone-aware finish timestamp.
        duration_seconds: Wall-clock duration in seconds.
        executor: Identity of the executor that produced this result.
        artifacts: Artifacts observed under the task output root.
        provenance: JSON-serializable execution provenance, for example the
            resolved executable path, container identity, or detected Rosetta
            revision.
    """

    task_id: str
    status: ExecutionStatus
    exit_code: int | None
    stdout: str
    stderr: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    executor: str
    artifacts: ArtifactManifest = field(default_factory=ArtifactManifest)
    provenance: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._validate_identity()
        self._validate_timing()
        object.__setattr__(self, "duration_seconds", float(self.duration_seconds))
        if not isinstance(self.artifacts, ArtifactManifest):
            raise TypeError("ExecutionResult.artifacts must be an ArtifactManifest")
        object.__setattr__(self, "provenance", freeze_json_mapping(self.provenance, where="ExecutionResult.provenance"))

    def _validate_identity(self) -> None:
        """Validate the task identity, status, and terminator fields."""
        if not isinstance(self.task_id, str) or not self.task_id:
            raise TypeError("ExecutionResult.task_id must be a non-empty str")
        if not isinstance(self.status, ExecutionStatus):
            raise TypeError(f"ExecutionResult.status must be an ExecutionStatus, got {type(self.status).__name__}")
        if self.exit_code is not None and (not isinstance(self.exit_code, int) or isinstance(self.exit_code, bool)):
            raise TypeError("ExecutionResult.exit_code must be an int or None")
        for name in ("stdout", "stderr", "executor"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"ExecutionResult.{name} must be a str, got {type(value).__name__}")
        if not self.executor:
            raise ValueError("ExecutionResult.executor must not be empty")

    def _validate_timing(self) -> None:
        """Validate timestamps and duration."""
        for name in ("started_at", "finished_at"):
            value = getattr(self, name)
            if not isinstance(value, datetime):
                raise TypeError(f"ExecutionResult.{name} must be a datetime")
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                raise ValueError(f"ExecutionResult.{name} must be timezone-aware")
        if not isinstance(self.duration_seconds, (int, float)) or isinstance(self.duration_seconds, bool):
            raise TypeError("ExecutionResult.duration_seconds must be a number")
        if self.duration_seconds < 0:
            raise ValueError("ExecutionResult.duration_seconds must not be negative")

    @property
    def succeeded(self) -> bool:
        """Whether the process completed with status ``SUCCEEDED``."""
        return self.status is ExecutionStatus.SUCCEEDED

    @property
    def failed(self) -> bool:
        """Whether the process completed with status ``FAILED``."""
        return self.status is ExecutionStatus.FAILED

    def as_dict(self, task: TaskSpec | None = None) -> dict[str, JSONValue]:
        """
        Return the JSON-serializable execution payload without a schema version.

        Args:
            task: Optional originating task. When supplied, the task description
                is embedded so a standalone manifest retains the command,
                working directory, environment overlay, input references, and
                expected artifacts that produced this result.

        Returns:
            A plain ``dict`` payload suitable for embedding in a versioned run
            manifest.
        """
        payload: dict[str, JSONValue] = {
            "task_id": self.task_id,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "started_at": _format_timestamp(self.started_at),
            "finished_at": _format_timestamp(self.finished_at),
            "duration_seconds": self.duration_seconds,
            "executor": self.executor,
            "artifacts": self.artifacts.as_dict(),
            "provenance": dict(self.provenance),
        }
        if task is not None:
            payload["task"] = task.as_dict()
        return payload

    def to_manifest(self, task: TaskSpec | None = None) -> dict[str, JSONValue]:
        """
        Return the versioned run manifest for this result.

        The manifest always carries a top-level integer ``schema_version``. It is
        deliberately not ``dataclasses.asdict``: RosettaPy owns this layout, and
        the layout is versioned for external consumers.

        Args:
            task: Optional originating task to embed.

        Returns:
            A plain ``dict`` run manifest.
        """
        return {"schema_version": RUN_MANIFEST_SCHEMA_VERSION, **self.as_dict(task=task)}

    def to_manifest_json(self, task: TaskSpec | None = None, *, indent: int | None = 2) -> str:
        """
        Serialize this result as a run-manifest JSON document.

        Args:
            task: Optional originating task to embed.
            indent: ``json.dumps`` indentation; ``None`` produces a compact
                single-line document.

        Returns:
            The manifest serialized as JSON text.
        """
        return json.dumps(self.to_manifest(task=task), indent=indent, sort_keys=False, ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class RunManifest:
    """
    A versioned, JSON-serializable manifest for a set of execution results.

    The result-level manifest is enough for a single task. This container exists
    so that a multi-task run has one owned, versioned document instead of an ad
    hoc list, and so that schema evolution has a single place to happen.
    """

    results: tuple[ExecutionResult, ...] = ()
    schema_version: int = RUN_MANIFEST_SCHEMA_VERSION
    run_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "results", tuple(self.results))
        for result in self.results:
            if not isinstance(result, ExecutionResult):
                raise TypeError(
                    f"RunManifest.results must contain ExecutionResult instances, got {type(result).__name__}"
                )
        if not isinstance(self.schema_version, int) or isinstance(self.schema_version, bool):
            raise TypeError("RunManifest.schema_version must be an int")
        if self.run_id is not None and (not isinstance(self.run_id, str) or not self.run_id):
            raise TypeError("RunManifest.run_id must be a non-empty str or None")

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self):
        return iter(self.results)

    def as_dict(self) -> dict[str, JSONValue]:
        """Return the JSON-serializable representation of this manifest."""
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "results": [result.as_dict() for result in self.results],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize this manifest as JSON text."""
        return json.dumps(self.as_dict(), indent=indent, sort_keys=False, ensure_ascii=False)


RunManifestLike = Union["RunManifest", "ExecutionResult"]
