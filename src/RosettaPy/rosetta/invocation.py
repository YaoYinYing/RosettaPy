"""
The Rosetta invocation: what computation is requested, independent of where it
runs.

A :class:`RosettaInvocation` carries Rosetta semantics only. It MUST NOT contain
a container image, an MPI executable, a scheduler allocation, a WSL
distribution, an executor object, a thread pool, a progress bar, or a scheduler.
Execution-environment choices live in a compile context and in the executor.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Mapping

from ..core._json import ensure_argument_token, freeze_string_mapping
from ..core.errors import CompilationError
from .binary import RosettaBinaryRequest

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..core._json import JSONValue


class NStructMode(str, Enum):
    """
    How ``nstruct`` is realized.

    ``NATIVE`` keeps ``-nstruct N`` inside a single Rosetta process; ``EXTERNAL``
    fans out into ``N`` independently addressable tasks. The policy belongs to
    Rosetta compilation and does not change with executor selection.
    """

    NATIVE = "native"
    EXTERNAL = "external"

    def __str__(self) -> str:  # pragma: no cover - display helper
        return self.value


@dataclass(frozen=True, slots=True)
class RosettaInvocation:
    """
    An immutable, environment-free description of one Rosetta computation.

    Attributes:
        binary: The unresolved request for the Rosetta executable.
        flags: Rosetta flag files, referenced with ``@`` on the command line.
            Flag *contents* are never rewritten by compilation; CRLF-to-LF
            conversion is therefore not an implicit compile side effect.
        options: Additional Rosetta command-line options. A RosettaScripts
            variable group is supplied as its rendered tokens, so compilation
            stays a pure function of the invocation.
        script_vars: RosettaScripts ``-parser:script_vars`` variables. Rendering
            order is the insertion order of the supplied mapping, which is what
            makes compilation deterministic for ordered mappings.
        nstruct: Number of structures to generate. Must be a positive integer.
        nstruct_mode: How ``nstruct`` is realized.
        mute: Whether to suppress Rosetta output with ``-mute all``.
    """

    binary: RosettaBinaryRequest
    flags: tuple[Path, ...] = ()
    options: tuple[str, ...] = ()
    script_vars: Mapping[str, str] = field(default_factory=dict)
    nstruct: int = 1
    nstruct_mode: NStructMode = NStructMode.NATIVE
    mute: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.binary, RosettaBinaryRequest):
            raise TypeError(
                f"RosettaInvocation.binary must be a RosettaBinaryRequest, got {type(self.binary).__name__}"
            )

        object.__setattr__(self, "flags", tuple(Path(flag) for flag in self.flags))
        for flag in self.flags:
            if str(flag) in ("", "."):
                raise ValueError("RosettaInvocation.flags must contain flag file paths, not empty strings")
            if "\x00" in str(flag):
                raise ValueError(f"RosettaInvocation.flags must not contain a NUL byte: {flag!r}")

        object.__setattr__(self, "options", tuple(self.options))
        for index, option in enumerate(self.options):
            ensure_argument_token(option, where=f"RosettaInvocation.options[{index}]")

        object.__setattr__(self, "script_vars", freeze_string_mapping(self.script_vars, where="script_vars"))
        for key in self.script_vars:
            if not key or "=" in key:
                raise ValueError(
                    f"RosettaInvocation.script_vars keys must be non-empty and must not contain '=', got {key!r}"
                )

        if not isinstance(self.nstruct, int) or isinstance(self.nstruct, bool):
            raise TypeError(f"RosettaInvocation.nstruct must be an int, got {type(self.nstruct).__name__}")
        if self.nstruct <= 0:
            raise ValueError(f"RosettaInvocation.nstruct must be a positive integer, got {self.nstruct}")

        if not isinstance(self.nstruct_mode, NStructMode):
            raise TypeError(
                f"RosettaInvocation.nstruct_mode must be an NStructMode, got {type(self.nstruct_mode).__name__}"
            )
        if not isinstance(self.mute, bool):
            raise TypeError(f"RosettaInvocation.mute must be a bool, got {type(self.mute).__name__}")

    @property
    def fan_out(self) -> int:
        """Number of independently addressable tasks this invocation compiles to."""
        if self.nstruct_mode is NStructMode.EXTERNAL:
            return self.nstruct
        return 1

    def with_script_vars(self, variables: Mapping[str, str]) -> "RosettaInvocation":
        """
        Return a copy of this invocation with additional RosettaScripts variables.

        Existing keys are overridden in place so that their position in the
        deterministic rendering order is preserved; new keys are appended.
        """
        merged = dict(self.script_vars)
        for key, value in variables.items():
            merged[key] = value
        return replace(self, script_vars=merged)

    def with_options(self, options: Iterable[str]) -> "RosettaInvocation":
        """Return a copy of this invocation with additional command-line options appended."""
        return replace(self, options=self.options + tuple(options))

    def with_flags(self, flags: Iterable[Any]) -> "RosettaInvocation":
        """Return a copy of this invocation with additional flag files appended."""
        return replace(self, flags=self.flags + tuple(Path(flag) for flag in flags))

    def validate_for_compilation(self) -> None:
        """
        Validate invocation-level constraints that are independent of a run.

        Raises:
            CompilationError: If the invocation cannot be compiled. The
                invocation is validated in addition to its own field checks
                because a contradiction may only be visible once the mode and
                the raw options are considered together.
        """
        if self.nstruct_mode is NStructMode.EXTERNAL and "-nstruct" in self.options:
            raise CompilationError(
                "RosettaInvocation options must not contain '-nstruct' in NStructMode.EXTERNAL; "
                "external fan-out is expressed as separate tasks, not as Rosetta-internal replication"
            )

    def as_dict(self) -> dict[str, JSONValue]:
        """Return the JSON-serializable representation of this invocation."""
        return {
            "binary": self.binary.as_dict(),
            "flags": [str(flag) for flag in self.flags],
            "options": list(self.options),
            "script_vars": dict(self.script_vars),
            "nstruct": self.nstruct,
            "nstruct_mode": self.nstruct_mode.value,
            "mute": self.mute,
        }
