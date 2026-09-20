"""
Artifact expectations, observed artifacts, and artifact manifests.

Outputs are first-class results in v2. A compiler declares *expected* artifacts
(pattern plus semantic role) and an executor reports *observed* artifacts under
the task output root.

Host paths are canonical: an artifact path is always expressed in the host-side
filesystem namespace, even when the executor that produced it ran inside a
container or another namespace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ._json import JSONValue


class ArtifactRole(str, Enum):
    """
    Semantic role of a produced output.

    Roles are semantic, not extensions: an executor or analyzer should be able to
    locate a scorefile without reverse-engineering a directory naming convention.
    """

    STRUCTURE = "structure"
    SCOREFILE = "scorefile"
    SILENT_FILE = "silent_file"
    LOG = "log"
    GENERIC_OUTPUT = "generic_output"

    def __str__(self) -> str:  # pragma: no cover - display helper
        return self.value


@dataclass(frozen=True, slots=True)
class ArtifactExpectation:
    """
    A pattern an executor should look for under a task's output root.

    Attributes:
        role: Semantic role of the expected output.
        pattern: Glob pattern interpreted *relative to* ``TaskSpec.output_root``.
            Absolute patterns and patterns escaping the output root are rejected
            when a task is constructed, so that artifact discovery cannot depend
            on guesses outside the declared output namespace.
        required: Whether the artifact is required for a workflow-level success.
            A missing required artifact does not turn execution into an
            infrastructure failure; it is recorded in the result provenance and
            may be promoted to an error by a workflow.
    """

    role: ArtifactRole
    pattern: str
    required: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.role, ArtifactRole):
            raise TypeError(f"ArtifactExpectation.role must be an ArtifactRole, got {type(self.role).__name__}")
        if not isinstance(self.pattern, str):
            raise TypeError("ArtifactExpectation.pattern must be a str")
        if not self.pattern:
            raise ValueError("ArtifactExpectation.pattern must not be empty")
        if "\x00" in self.pattern:
            raise ValueError("ArtifactExpectation.pattern must not contain a NUL byte")
        if Path(self.pattern).is_absolute():
            raise ValueError(f"ArtifactExpectation.pattern {self.pattern!r} must be relative to the task output root")
        if ".." in Path(self.pattern).parts:
            raise ValueError(f"ArtifactExpectation.pattern {self.pattern!r} must not escape the task output root")
        if not isinstance(self.required, bool):
            raise TypeError("ArtifactExpectation.required must be a bool")

    @property
    def relative_parts(self) -> tuple[str, ...]:
        """The pattern split into path components, for pattern validation."""
        return Path(self.pattern).parts


@dataclass(frozen=True, slots=True)
class Artifact:
    """
    A single observed output file.

    Attributes:
        path: Host-canonical path to the produced file.
        role: Semantic role, either from a matching expectation or from fallback
            classification.
        size_bytes: Size of the file in bytes at collection time.
        sha256: Optional content digest. Checksum calculation is optional in the
            first milestone and MUST NOT be required for a successful execution.
    """

    path: Path
    role: ArtifactRole
    size_bytes: int
    sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            object.__setattr__(self, "path", Path(self.path))
        if not isinstance(self.role, ArtifactRole):
            raise TypeError(f"Artifact.role must be an ArtifactRole, got {type(self.role).__name__}")
        if not isinstance(self.size_bytes, int) or isinstance(self.size_bytes, bool):
            raise TypeError("Artifact.size_bytes must be an int")
        if self.size_bytes < 0:
            raise ValueError("Artifact.size_bytes must not be negative")
        if self.sha256 is not None and not isinstance(self.sha256, str):
            raise TypeError("Artifact.sha256 must be a str or None")

    def as_dict(self) -> dict[str, JSONValue]:
        """Return the JSON-serializable representation of this artifact."""
        return {
            "path": str(self.path),
            "role": self.role.value,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    """
    The observed outputs of one task.

    The manifest is a *sequence*, not a one-artifact-per-role mapping: multiple
    structures or scorefiles may share a single semantic role.

    Attributes:
        artifacts: Observed artifacts, ordered deterministically.
        missing_required: Patterns of required expectations that matched no file.
            Presence of a missing required artifact does not change the
            execution status; it is structured information a workflow may
            validate.
        unexpected_count: Number of collected outputs that were classified by
            fallback rather than by an expectation.
    """

    artifacts: tuple[Artifact, ...] = ()
    missing_required: tuple[str, ...] = ()
    unexpected_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "missing_required", tuple(self.missing_required))
        for artifact in self.artifacts:
            if not isinstance(artifact, Artifact):
                raise TypeError(
                    f"ArtifactManifest.artifacts must contain Artifact instances, got {type(artifact).__name__}"
                )
        for pattern in self.missing_required:
            if not isinstance(pattern, str):
                raise TypeError("ArtifactManifest.missing_required must contain strings")
        if not isinstance(self.unexpected_count, int) or isinstance(self.unexpected_count, bool):
            raise TypeError("ArtifactManifest.unexpected_count must be an int")
        if self.unexpected_count < 0:
            raise ValueError("ArtifactManifest.unexpected_count must not be negative")

    def __len__(self) -> int:
        return len(self.artifacts)

    def __iter__(self):
        return iter(self.artifacts)

    @property
    def complete(self) -> bool:
        """Whether every required expectation matched at least one file."""
        return not self.missing_required

    def by_role(self, role: ArtifactRole) -> tuple[Artifact, ...]:
        """Return all artifacts carrying ``role``."""
        return tuple(artifact for artifact in self.artifacts if artifact.role is role)

    def first(self, role: ArtifactRole) -> Artifact | None:
        """Return the first artifact carrying ``role``, or ``None``."""
        for artifact in self.artifacts:
            if artifact.role is role:
                return artifact
        return None

    def as_dict(self) -> dict[str, JSONValue]:
        """Return the JSON-serializable representation of this manifest."""
        return {
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "missing_required": list(self.missing_required),
            "unexpected_count": self.unexpected_count,
        }

    @classmethod
    def from_artifacts(cls, artifacts: Sequence[Artifact], **kwargs: Any) -> "ArtifactManifest":
        """Build a manifest from any artifact sequence."""
        return cls(artifacts=tuple(artifacts), **kwargs)
