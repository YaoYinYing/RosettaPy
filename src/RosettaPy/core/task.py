"""
The task description contract.

A :class:`TaskSpec` is one executable computation: an argument vector, a working
directory, an environment overlay, declared inputs, an output root, expected
artifacts, and requested resources. It is the only thing an executor consumes,
and it contains no executor instance and no backend-specific configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

from ._json import ensure_argument_token, freeze_json_mapping, freeze_string_mapping
from ._naming import validate_logical_identifier
from .artifact import ArtifactExpectation

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ._json import JSONValue


@dataclass(frozen=True, slots=True)
class ResourceRequest:
    """
    Requested computation resources.

    Resources describe *how much* computation a task asks for. They never select
    a scheduler; scheduler allocation discovery belongs to a separate adapter.
    """

    cpu_cores: int | None = None
    memory_mb: int | None = None

    def __post_init__(self) -> None:
        for name in ("cpu_cores", "memory_mb"):
            value = getattr(self, name)
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"ResourceRequest.{name} must be an int or None, got {type(value).__name__}")
            if value <= 0:
                raise ValueError(f"ResourceRequest.{name} must be positive when given, got {value}")

    def as_dict(self) -> dict[str, JSONValue]:
        """Return the JSON-serializable representation of this request."""
        return {"cpu_cores": self.cpu_cores, "memory_mb": self.memory_mb}


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """
    An immutable, backend-independent description of one computation.

    Attributes:
        task_id: Stable logical identifier for this task.
        argv: Shell-free argument tokens. ``argv[0]`` is the executable request
            produced by a compiler; it may be a logical binary name or an
            explicit path. Executors MUST NOT rebuild a shell command string.
        cwd: Host-canonical working directory for the process.
        env: Environment *overlay*, not a complete environment. An executor
            merges it onto its inherited base environment.
        inputs: Host-canonical input paths the task depends on.
        output_root: Host-canonical directory under which artifacts are produced
            and collected.
        expected_artifacts: Patterns the executor should look for under
            ``output_root`` after the process finishes.
        resources: Requested computation resources.
        metadata: JSON-serializable task metadata for provenance and
            interoperability.
    """

    task_id: str
    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str] = field(default_factory=dict)
    inputs: tuple[Path, ...] = ()
    output_root: Path = Path(".")
    expected_artifacts: tuple[ArtifactExpectation, ...] = ()
    resources: ResourceRequest = field(default_factory=ResourceRequest)
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_logical_identifier(self.task_id, where="TaskSpec.task_id")

        if isinstance(self.argv, str):
            raise TypeError("TaskSpec.argv must be a sequence of tokens, not a string")
        argv = tuple(self.argv)
        if not argv:
            raise ValueError("TaskSpec.argv must contain at least the executable request token")
        for index, token in enumerate(argv):
            ensure_argument_token(token, where=f"TaskSpec.argv[{index}]")
        object.__setattr__(self, "argv", argv)

        object.__setattr__(self, "cwd", Path(self.cwd))
        object.__setattr__(self, "output_root", Path(self.output_root))
        object.__setattr__(self, "inputs", tuple(Path(item) for item in self.inputs))
        object.__setattr__(self, "expected_artifacts", tuple(self.expected_artifacts))
        for expectation in self.expected_artifacts:
            if not isinstance(expectation, ArtifactExpectation):
                raise TypeError(
                    "TaskSpec.expected_artifacts must contain ArtifactExpectation instances, "
                    f"got {type(expectation).__name__}"
                )
        if not isinstance(self.resources, ResourceRequest):
            raise TypeError("TaskSpec.resources must be a ResourceRequest")
        object.__setattr__(self, "env", freeze_string_mapping(self.env, where="TaskSpec.env"))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, where="TaskSpec.metadata"))

    @property
    def executable_request(self) -> str:
        """The unresolved executable request, i.e. ``argv[0]``."""
        return self.argv[0]

    @property
    def arguments(self) -> tuple[str, ...]:
        """The argument tokens following the executable request."""
        return self.argv[1:]

    def as_dict(self) -> dict[str, JSONValue]:
        """Return the JSON-serializable representation of this task."""
        return {
            "task_id": self.task_id,
            "argv": list(self.argv),
            "cwd": str(self.cwd),
            "env": dict(self.env),
            "inputs": [str(item) for item in self.inputs],
            "output_root": str(self.output_root),
            "expected_artifacts": [
                {"role": expectation.role.value, "pattern": expectation.pattern, "required": expectation.required}
                for expectation in self.expected_artifacts
            ],
            "resources": self.resources.as_dict(),
            "metadata": dict(self.metadata),
        }
