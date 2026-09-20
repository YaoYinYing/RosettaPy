# RosettaPy v2 implementation contract

Status: **Normative — decisions in this document are not open to incidental
implementation-time redesign**

This document converts the architecture in [ARCHITECTURE.md](ARCHITECTURE.md)
into concrete first-version contracts. The Python spelling may receive small
ergonomic adjustments during implementation, but semantic changes require a
dedicated design change.

The examples below are interface sketches, not copy-paste implementation.

## 1. Normative language

- **MUST**: required for v2 compatibility.
- **MUST NOT**: prohibited.
- **SHOULD**: expected unless a documented technical reason prevents it.
- **MAY**: optional.

## 2. Immutability

Core task-description objects MUST be immutable from the perspective of
consumers. Frozen dataclasses with tuple-based collections are the preferred
implementation.

Metadata mappings do not need a custom persistent-map dependency, but code MUST
treat them as read-only after construction.

## 3. Rosetta invocation

The first v2 invocation model is conceptually:

```python
@dataclass(frozen=True, slots=True)
class RosettaInvocation:
    binary: RosettaBinaryRequest
    flags: tuple[Path, ...] = ()
    options: tuple[str, ...] = ()
    script_vars: Mapping[str, str] = field(default_factory=dict)
    nstruct: int = 1
    nstruct_mode: NStructMode = NStructMode.NATIVE
    mute: bool = True
```

Rules:

- `RosettaInvocation` MUST contain Rosetta semantics only.
- It MUST NOT contain a Docker image, MPI executable, SLURM allocation, WSL
  distribution, executor object, thread pool, progress bar, or scheduler.
- `nstruct` MUST be a positive integer.
- RosettaScripts variables MUST have a deterministic rendering order. The
  compiler SHOULD preserve insertion order of the supplied mapping.
- The invocation MUST NOT mutate flag files or input files.

### 3.1 Binary request

The binary request represents intent, not a backend-resolved executable.

Conceptually:

```python
@dataclass(frozen=True, slots=True)
class RosettaBinaryRequest:
    name: str | None = None
    path: Path | None = None
```

Exactly one of `name` or `path` MUST be provided.

A logical name such as `rosetta_scripts` is preferred when the same task is
expected to run in different execution environments.

## 4. Compile context

Execution-environment choices do not belong in the invocation. Run-local
filesystem and identity information are supplied separately.

Conceptually:

```python
@dataclass(frozen=True, slots=True)
class CompileContext:
    run_id: str
    work_dir: Path
    output_dir: Path
    env: Mapping[str, str] = field(default_factory=dict)
    inputs: tuple[Path, ...] = ()
```

Rules:

- paths MUST be represented in the host canonical namespace;
- `run_id` MUST be safe to use as a logical identifier, but the compiler MUST
  NOT rely on timestamp-based uniqueness;
- compilation MUST NOT require Docker, MPI, SLURM, or WSL information.

## 5. Compiler

The v2 design uses an independent `RosettaCompiler`.

The public semantic contract is:

```python
class RosettaCompiler:
    def compile(
        self,
        invocation: RosettaInvocation,
        context: CompileContext,
    ) -> tuple[TaskSpec, ...]:
        ...
```

The return type is always a tuple, even when one task is produced.

The compiler MUST:

- render Rosetta options deterministically;
- render each flag reference as a command argument without modifying the file;
- render RosettaScripts variables;
- add output-path options according to the compile context;
- implement `nstruct` mode;
- declare expected Rosetta artifacts;
- remain executable in unit tests without Rosetta installed.

The compiler MUST NOT:

- call `subprocess`;
- search Docker images;
- query MPI or SLURM;
- branch on executor type;
- create containers;
- mutate input files;
- require the requested Rosetta executable to exist at compile time.

## 6. `nstruct` contract

`NStructMode` initially has two values:

```python
class NStructMode(Enum):
    NATIVE = "native"
    EXTERNAL = "external"
```

### 6.1 Native mode

`NATIVE` is the v2 default.

For `nstruct=N`, the compiler MUST emit exactly one `TaskSpec` containing
`-nstruct N` when `N > 1`.

The compiler MUST NOT change this policy based on executor selection.

### 6.2 External mode

For `nstruct=N`, the compiler MUST emit `N` independently addressable
`TaskSpec` objects.

Each external task MUST have:

- a stable deterministic task id derived from `run_id` and the replica index;
- an independently writable score/output namespace;
- Rosetta arguments that prevent output-name collisions.

The exact Rosetta suffix spelling is implementation detail, but it MUST be
covered by compiler tests.

For `nstruct=1`, either mode produces one task.

## 7. Task specification

The first v2 task contract is conceptually:

```python
@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str]
    inputs: tuple[Path, ...]
    output_root: Path
    expected_artifacts: tuple[ArtifactExpectation, ...]
    resources: ResourceRequest
    metadata: Mapping[str, JSONValue]
```

Rules:

- `argv` MUST be shell-free argument tokens. Executors MUST NOT reconstruct a
  shell command string for normal execution.
- `argv[0]` is the executable request produced by the compiler. It may be a
  logical binary name or an explicit path.
- `cwd` and `output_root` MUST use host canonical paths.
- `env` is an overlay. A native executor merges it onto its inherited base
  environment unless configured otherwise.
- `metadata` MUST be JSON-serializable.
- `TaskSpec` MUST NOT contain an executor instance or backend-specific config.

### 7.1 Resource request

The first version remains intentionally small:

```python
@dataclass(frozen=True, slots=True)
class ResourceRequest:
    cpu_cores: int | None = None
    memory_mb: int | None = None
```

Resources describe requested computation resources. They do not select a
scheduler.

## 8. Artifact expectations and artifacts

Conceptually:

```python
@dataclass(frozen=True, slots=True)
class ArtifactExpectation:
    role: ArtifactRole
    pattern: str
    required: bool = False

@dataclass(frozen=True, slots=True)
class Artifact:
    path: Path
    role: ArtifactRole
    size_bytes: int
    sha256: str | None = None

@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    artifacts: tuple[Artifact, ...]
```

`pattern` is interpreted relative to `TaskSpec.output_root`.

The first semantic roles are:

```text
structure
scorefile
silent_file
log
generic_output
```

`ArtifactManifest` is a sequence, not a one-artifact-per-role mapping. Multiple
structures or scorefiles with the same role are valid.

Checksum calculation is optional in the first milestone and MUST NOT be required
for a successful execution.

## 9. Execution result

Conceptually:

```python
class ExecutionStatus(Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"

@dataclass(frozen=True, slots=True)
class ExecutionResult:
    task_id: str
    status: ExecutionStatus
    exit_code: int | None
    stdout: str
    stderr: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    executor: str
    artifacts: ArtifactManifest
    provenance: Mapping[str, JSONValue]
```

Only `SUCCEEDED` and `FAILED` must be implemented in the first execution PR.
The other states reserve schema space for later work.

## 10. Failure contract

This rule is mandatory:

> **A process failure is a result. An infrastructure failure is an exception.**

If a process is successfully launched and Rosetta exits with a non-zero code,
the executor MUST return `ExecutionResult(status=FAILED, ...)`.

An executor MUST raise `ExecutionError` when it cannot establish or maintain
the execution environment, for example:

- it cannot create the working directory;
- the Docker daemon is unavailable;
- the executable cannot be launched;
- required mount preparation fails.

An `ExecutionError` MAY carry a partial result if a process started before the
infrastructure failure became observable.

Compiler validation failures raise `CompilationError`.

## 11. Executor protocol

The public executor protocol is intentionally small:

```python
class Executor(Protocol):
    @property
    def identity(self) -> str:
        ...

    def execute(self, task: TaskSpec) -> ExecutionResult:
        ...
```

There is **no `execute_many()` requirement in the initial kernel**.

Batch orchestration belongs outside the single-task protocol. A later
orchestration helper may call `Executor.execute()` concurrently.

Executor lifecycle phases such as prepare, launch, collect, and cleanup are
internal implementation structure, not separate public protocol methods in the
first version.

## 12. Native executor

`NativeExecutor` is the reference implementation.

It MUST:

- create `cwd` and `output_root` deterministically when absent;
- execute without `shell=True`;
- resolve a logical executable name using the native launch environment;
- capture stdout and stderr separately;
- record timing and exit status;
- collect artifacts under `output_root`;
- return host-canonical artifact paths;
- avoid global working-directory mutation.

It MUST NOT own task fan-out or joblib batch orchestration.

## 13. Docker executor contract

Docker is not implemented in the first code milestone, but its compatibility
requirements constrain the task model.

`DockerExecutor` MUST consume the same `TaskSpec` type as Native.

Host paths remain canonical. Docker preparation SHOULD use same-path bind mounts
for declared inputs, `cwd`, and `output_root` when practical. If a container
path differs, translation is internal to Docker execution and MUST be reversed
before returning artifacts.

A logical Rosetta binary name is resolved inside the container environment.
Docker-specific binary directories MUST NOT be embedded by the compiler.

## 14. Artifact collection

The executor MUST return an `ArtifactManifest` after a launched process
finishes.

Shared artifact-collection helpers MAY live in `core` because collection
operates on generic expectations and host paths, not on Rosetta workflow
semantics.

Expected artifact classification SHOULD take precedence over extension-based
fallback classification.

Unexpected files under `output_root` MAY be recorded as
`generic_output`. Their presence does not fail execution.

A workflow may perform stricter post-run validation and reject a semantically
incomplete result.

## 15. Run manifest

The first v2 implementation MUST be able to serialize a run result to JSON.

The serialized schema MUST contain a top-level integer `schema_version`.
Initial value: `1`.

The serialized schema is an interoperability contract and MUST NOT simply be
`dataclasses.asdict()` with no schema ownership.

The exact JSON field layout may be finalized in the implementation PR, but it
must preserve the semantics defined in this document and receive dedicated
tests.

## 16. Compatibility facade

The legacy `Rosetta` class may remain while migration proceeds.

Rules:

- it MAY translate old arguments into `RosettaInvocation`,
  `CompileContext`, and an executor;
- it MAY preserve selected legacy defaults such as external local fan-out;
- it MUST NOT be imported by the v2 core;
- it MUST NOT add concrete-executor checks to v2 compiler/core code;
- deprecation warnings SHOULD be introduced only when a functional migration
  path exists.

## 17. Explicit non-decisions deferred beyond the first milestone

The following are intentionally not part of the first implementation contract:

- generic retry policy;
- remote/SSH execution;
- Apptainer/Singularity;
- cache keys;
- task hashing;
- streaming log APIs;
- cancellation implementation;
- full scheduler submission;
- MCP schemas;
- broad workflow rewrites.

A coding agent MUST NOT add these while implementing the first milestone.
