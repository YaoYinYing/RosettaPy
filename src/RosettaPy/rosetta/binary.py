"""
The Rosetta binary *request*.

A request represents intent, not a backend-resolved executable. A logical name
such as ``rosetta_scripts`` is preferred when the same task may run in different
execution environments; an explicit path is used when the caller already knows
the launch environment.

The compiler preserves the requested token verbatim. Resolving it in the launch
environment, and recording the resolved executable in provenance, is the
executor's responsibility. This is what allows one compilation to serve both
native and containerized execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..core._naming import validate_logical_identifier

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..core._json import JSONValue


@dataclass(frozen=True, slots=True)
class RosettaBinaryRequest:
    """
    An unresolved request for a Rosetta executable.

    Exactly one of :attr:`name` and :attr:`path` must be provided.

    Attributes:
        name: Logical executable name, for example ``"rosetta_scripts"``. A
            logical name must not contain a path separator.
        path: Explicit path to an executable. The path is not required to exist
            at compile time.
    """

    name: str | None = None
    path: Path | None = None

    def __post_init__(self) -> None:
        if (self.name is None) == (self.path is None):
            raise ValueError(
                "RosettaBinaryRequest requires exactly one of 'name' or 'path', "
                f"got name={self.name!r}, path={self.path!r}"
            )
        if self.name is not None:
            validate_logical_identifier(self.name, where="RosettaBinaryRequest.name")
        if self.path is not None:
            object.__setattr__(self, "path", Path(self.path))

    @property
    def token(self) -> str:
        """
        The executable token passed to an executor as ``argv[0]``.

        For a logical request this is the bare name, which a native executor
        resolves through its launch environment and a container executor
        resolves inside its container. For an explicit request this is the path
        as given, without resolution or normalization.
        """
        return self.name if self.name is not None else str(self.path)

    @property
    def is_logical(self) -> bool:
        """Whether this request uses a logical name rather than an explicit path."""
        return self.name is not None

    @classmethod
    def from_name(cls, name: str) -> "RosettaBinaryRequest":
        """Build a request for a logical executable name."""
        return cls(name=name)

    @classmethod
    def from_path(cls, path: Any) -> "RosettaBinaryRequest":
        """Build a request for an explicit executable path."""
        return cls(path=Path(path))

    def as_dict(self) -> dict[str, JSONValue]:
        """Return the JSON-serializable representation of this request."""
        return {"name": self.name, "path": str(self.path) if self.path is not None else None}
