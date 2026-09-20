"""
The Rosetta compiler.

:class:`RosettaCompiler` is the only component that translates Rosetta semantics
into backend-independent task descriptions. It is a dedicated object rather than
a set of backend-specific branches inside :class:`RosettaInvocation`.

The compiler never starts processes, mounts filesystems, inspects container
images, invokes MPI, queries a scheduler, or mutates user input files. It does
not require the requested Rosetta executable to exist, which is what makes
compilation a pure, unit-testable function of an invocation and a compile
context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

from ..core._json import freeze_string_mapping
from ..core._naming import validate_logical_identifier
from ..core.artifact import ArtifactExpectation, ArtifactRole
from ..core.errors import CompilationError
from ..core.task import ResourceRequest, TaskSpec
from .invocation import NStructMode, RosettaInvocation

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..core._json import JSONValue

_SUFFIX_OPTION = "-suffix"
_SCOREFILE_OPTION = "-out:file:scorefile"
_OUTPUT_PDB_OPTION = "-out:path:pdb"
_OUTPUT_SCORE_OPTION = "-out:path:score"
_MUTE_OPTION = "-mute"
_VARIABLE_OPTION = "-parser:script_vars"
_NO_NSTRUCT_LABEL_OPTION = "-no_nstruct_label"

_REPLICA_WIDTH = 5
"""Zero-padding width of an external replica index."""


@dataclass(frozen=True, slots=True)
class CompileContext:
    """
    Run-local filesystem and identity information supplied to the compiler.

    Execution-environment choices do not belong to the invocation; they also do
    not belong here. A compile context describes *where in the host filesystem*
    one run happens, so compilation never needs container, MPI, WSL, or
    scheduler information.

    Attributes:
        run_id: Logical identifier of the run. It is safe to use as a file name
            component and must not be a timestamp-derived value that the
            compiler relies on for uniqueness.
        work_dir: Host-canonical working directory for compiled tasks.
        output_dir: Host-canonical root under which per-task output roots live.
        env: Environment overlay applied to compiled tasks. It is an overlay,
            not a complete environment.
        inputs: Host-canonical input paths the run depends on.
    """

    run_id: str
    work_dir: Path
    output_dir: Path
    env: Mapping[str, str] = field(default_factory=dict)
    inputs: tuple[Path, ...] = ()

    def __post_init__(self) -> None:
        validate_logical_identifier(self.run_id, where="CompileContext.run_id")
        if isinstance(self.inputs, (str, bytes)):
            raise TypeError("CompileContext.inputs must be a sequence of paths, not a string")
        object.__setattr__(self, "work_dir", Path(self.work_dir))
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        object.__setattr__(self, "inputs", tuple(Path(item) for item in self.inputs))
        object.__setattr__(self, "env", freeze_string_mapping(self.env, where="CompileContext.env"))

    def as_dict(self) -> dict[str, JSONValue]:
        """Return the JSON-serializable representation of this context."""
        return {
            "run_id": self.run_id,
            "work_dir": str(self.work_dir),
            "output_dir": str(self.output_dir),
            "env": dict(self.env),
            "inputs": [str(item) for item in self.inputs],
        }


class RosettaCompiler:
    """
    Compiles a :class:`RosettaInvocation` into immutable task descriptions.

    The compiler is stateless. Its public semantic contract is:

    .. code-block:: python

        compile(invocation, context) -> tuple[TaskSpec, ...]

    The return type is always a tuple, even when a single task is produced.

    ``RosettaCompiler`` imports no concrete executor and holds no reference to
    one: the same compiled tasks are valid input for a native, container, or
    distributed executor.
    """

    identity = "rosetta_compiler"
    """Stable identity of this compiler, for provenance and logging."""

    def compile(self, invocation: RosettaInvocation, context: CompileContext) -> tuple[TaskSpec, ...]:
        """
        Compile one invocation into one or more tasks.

        Rendering order is fixed so that identical inputs produce identical
        argument vectors:

        ``binary``, flag references, options, RosettaScripts variables, output
        path options, output options, ``-nstruct`` and replication options, and
        finally ``-mute``.

        Args:
            invocation: The Rosetta computation to compile.
            context: Run-local filesystem and identity information.

        Returns:
            A tuple of immutable tasks. ``NStructMode.NATIVE`` yields exactly one
            task; ``NStructMode.EXTERNAL`` yields one task per replica.

        Raises:
            CompilationError: If the invocation cannot be compiled. Compilation
                never fails because a binary, flag file, or input file is absent.
        """
        if not isinstance(invocation, RosettaInvocation):
            raise TypeError(f"compile() expects a RosettaInvocation, got {type(invocation).__name__}")
        if not isinstance(context, CompileContext):
            raise TypeError(f"compile() expects a CompileContext, got {type(context).__name__}")

        invocation.validate_for_compilation()

        base_arguments = self._render_base_arguments(invocation)
        metadata_common = self._render_metadata(invocation, context)

        if invocation.nstruct_mode is NStructMode.NATIVE:
            return (self._compile_native(invocation, context, base_arguments, metadata_common),)

        return tuple(
            self._compile_external_replica(invocation, context, base_arguments, metadata_common, replica_index)
            for replica_index in range(1, invocation.nstruct + 1)
        )

    # ----------------------------------------------------------------- rendering

    def _render_base_arguments(self, invocation: RosettaInvocation) -> list[str]:
        """
        Render the environment-independent leading arguments.

        Binary lookup is deliberately absent: the requested executable token is
        preserved verbatim and resolved later by the executor in its own launch
        environment. Flag files are referenced, never read or rewritten.
        """
        arguments = [invocation.binary.token]

        for flag in invocation.flags:
            arguments.append(f"@{flag}")

        arguments.extend(invocation.options)
        arguments.extend(self._render_script_vars(invocation))

        if invocation.mute:
            arguments.extend([_MUTE_OPTION, "all"])

        return arguments

    @staticmethod
    def _render_script_vars(invocation: RosettaInvocation) -> list[str]:
        """
        Render RosettaScripts variables in deterministic order.

        The order is the insertion order of the invocation mapping. Variable
        expansion happens inside Rosetta through ``-parser:script_vars``; the
        compiler never edits the script XML.
        """
        rendered: list[str] = []
        for key, value in invocation.script_vars.items():
            rendered.extend([_VARIABLE_OPTION, f"{key}={value}"])
        return rendered

    @staticmethod
    def _strip_option(arguments: list[str], option: str) -> list[str] | None:
        """
        Remove every ``option value`` pair from ``arguments`` and return the last value.

        Used to fold a caller-provided value into the compiler's own output
        policy without duplicating scalar options whose last occurrence wins.
        The input list is copied; the invocation itself is never mutated.
        """
        last_value: str | None = None
        result: list[str] = []
        index = 0
        while index < len(arguments):
            if arguments[index] == option and index + 1 < len(arguments):
                last_value = arguments[index + 1]
                index += 2
                continue
            result.append(arguments[index])
            index += 1
        if last_value is not None:
            arguments[:] = result
        return last_value

    def _render_output_arguments(self, output_root: Path, scorefile_name: str) -> list[str]:
        """
        Render output-path and output-name options for one task.

        Paths are host canonical. A container or WSL executor owns any namespace
        translation and must translate the produced artifact paths back before
        returning a result.
        """
        return [
            _OUTPUT_PDB_OPTION,
            str(output_root),
            _OUTPUT_SCORE_OPTION,
            str(output_root),
            _SCOREFILE_OPTION,
            scorefile_name,
        ]

    @staticmethod
    def _render_metadata(invocation: RosettaInvocation, context: CompileContext) -> dict[str, JSONValue]:
        """Render the task metadata shared by every compiled replica."""
        return {
            "compiler": RosettaCompiler.identity,
            "run_id": context.run_id,
            "binary_request": invocation.binary.as_dict(),
            "flags": [str(flag) for flag in invocation.flags],
            "script_vars": dict(invocation.script_vars),
            "nstruct": invocation.nstruct,
            "nstruct_mode": invocation.nstruct_mode.value,
        }

    def _compile_native(
        self,
        invocation: RosettaInvocation,
        context: CompileContext,
        base_arguments: list[str],
        metadata_common: dict[str, JSONValue],
    ) -> TaskSpec:
        """
        Compile native replication: one task holding ``-nstruct N``.

        The policy does not change with executor selection, so a container or
        distributed executor receives exactly the same single task.
        """
        arguments = list(base_arguments)
        output_root = context.output_dir / context.run_id
        scorefile_name = f"{context.run_id}.scorefile.sc"

        self._strip_option(arguments, _SCOREFILE_OPTION)
        arguments.extend(self._render_output_arguments(output_root, scorefile_name))
        if invocation.nstruct > 1:
            arguments.extend(["-nstruct", str(invocation.nstruct)])

        metadata = dict(metadata_common)
        metadata.update({"replica_index": 1, "scorefile": scorefile_name})

        return TaskSpec(
            task_id=context.run_id,
            argv=tuple(arguments),
            cwd=context.work_dir,
            env=context.env,
            inputs=context.inputs,
            output_root=output_root,
            expected_artifacts=self._expected_artifacts(scorefile_name),
            resources=self._resources(invocation),
            metadata=metadata,
        )

    def _compile_external_replica(
        self,
        invocation: RosettaInvocation,
        context: CompileContext,
        base_arguments: list[str],
        metadata_common: dict[str, JSONValue],
        replica_index: int,
    ) -> TaskSpec:
        """
        Compile one replica of an externally fanned-out run.

        Each replica gets a stable task id derived from ``run_id`` and the
        replica index, its own output namespace, and a ``-suffix`` that prevents
        output-name collisions. A caller-provided suffix is merged rather than
        discarded.
        """
        replica_tag = f"{replica_index:0{_REPLICA_WIDTH}d}"
        arguments = list(base_arguments)
        user_suffix = self._strip_option(arguments, _SUFFIX_OPTION)
        suffix = f"{user_suffix}_{replica_tag}" if user_suffix else f"_{replica_tag}"

        output_root = context.output_dir / f"{context.run_id}-{replica_tag}"
        scorefile_name = f"{context.run_id}.scorefile.{replica_tag}.sc"

        self._strip_option(arguments, _SCOREFILE_OPTION)
        arguments.extend([_SUFFIX_OPTION, suffix, _NO_NSTRUCT_LABEL_OPTION])
        arguments.extend(self._render_output_arguments(output_root, scorefile_name))

        metadata = dict(metadata_common)
        metadata.update(
            {
                "replica_index": replica_index,
                "replica_suffix": suffix,
                "scorefile": scorefile_name,
                "user_suffix": user_suffix,
            }
        )

        return TaskSpec(
            task_id=f"{context.run_id}-{replica_tag}",
            argv=tuple(arguments),
            cwd=context.work_dir,
            env=context.env,
            inputs=context.inputs,
            output_root=output_root,
            expected_artifacts=self._expected_artifacts(scorefile_name),
            resources=self._resources(invocation),
            metadata=metadata,
        )

    # ------------------------------------------------------------------ policies

    @staticmethod
    def _expected_artifacts(scorefile_name: str) -> tuple[ArtifactExpectation, ...]:
        """
        Declare the Rosetta output expectations for a compiled task.

        Patterns are relative to the task output root. Expected artifacts are not
        marked required: a missing artifact is recorded in structured provenance
        and may be promoted to a workflow-level failure by a workflow, but it does
        not turn a launched process into an infrastructure error.
        """
        return (
            ArtifactExpectation(role=ArtifactRole.STRUCTURE, pattern="*.pdb"),
            ArtifactExpectation(role=ArtifactRole.SCOREFILE, pattern=scorefile_name),
            ArtifactExpectation(role=ArtifactRole.SILENT_FILE, pattern="*.silent"),
        )

    @staticmethod
    def _resources(invocation: RosettaInvocation) -> ResourceRequest:
        """
        Derive the resource request for a compiled task.

        Rosetta's own ``-nstruct`` replication reuses one process, so it does not
        multiply the requested CPU cores. External fan-out expresses parallelism
        as separate tasks.
        """
        return ResourceRequest()

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return f"{type(self).__name__}()"


__all__ = ["CompileContext", "RosettaCompiler"]
