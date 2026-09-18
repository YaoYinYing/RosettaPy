# RosettaPy v2 architecture

Status: **Normative**

## 1. Purpose

RosettaPy has accumulated working support for native execution, MPI, Docker,
WSL, Rosetta binary discovery, RosettaScripts variables, `nstruct`,
isolation, parallel execution, SLURM environments, workflow helpers, and result
analysis. The compatibility work is useful, but the current architecture lets
backend-specific behavior leak into central Rosetta logic.

The v2 reconstruction does not start by adding more compatibility. It starts by
defining a small execution contract and placing every existing capability
around that contract.

RosettaPy v2 has one product responsibility:

> **Define, execute, and inspect reproducible Rosetta computations.**

It is not intended to become a general workflow engine, a scheduler, or a
replacement for PyRosetta.

## 2. Architectural problem

The current `Rosetta` object combines several concerns:

- Rosetta binary lookup;
- command composition;
- RosettaScripts variable expansion;
- task fan-out;
- output-path policy;
- native/MPI/container/WSL dispatch;
- progress reporting;
- isolation;
- process execution.

The current node abstraction is also a union of concrete backend classes.
Consequently, adding another backend encourages edits to central dispatch code.

A second problem is the absence of a durable task/result boundary. A command
object is executed and largely returned as the same command object. Process
status, captured output, runtime, provenance, and produced files are not modeled
as a stable result contract.

v2 reverses that dependency direction.

## 3. Target data flow

The canonical flow is:

```text
RosettaInvocation
       |
       | RosettaCompiler
       v
  TaskSpec(s)
       |
       | Executor
       v
ExecutionResult
       |
       v
ArtifactManifest
```

A workflow may construct a `RosettaInvocation`. The compiler converts Rosetta
semantics into one or more backend-independent tasks. An executor runs one task
and returns a structured result. Analysis consumes results and artifacts rather
than inferring files from directory conventions.

## 4. Layer boundaries

### 4.1 `core/`

`core` defines the minimum execution vocabulary required by RosettaPy:

- `TaskSpec`;
- `ExecutionResult`;
- `ExecutionStatus`;
- `Artifact`;
- `ArtifactExpectation`;
- `ArtifactManifest`;
- `ResourceRequest`;
- the `Executor` protocol;
- shared execution errors.

The core layer is intentionally small. It is not a public generic workflow
framework.

**Invariant:** `core` must not import Rosetta-specific modules, concrete
executors, schedulers, Docker, MPI, WSL, workflows, or analyzers.

### 4.2 `rosetta/`

The Rosetta layer owns Rosetta semantics:

- `RosettaInvocation`;
- Rosetta binary request/provenance models;
- Rosetta command compilation;
- RosettaScripts variable rendering;
- `nstruct` compilation policy;
- Rosetta output expectations;
- Rosetta-specific validation and parsing helpers.

It may import `core` types.

**Invariant:** the Rosetta compiler must not import or branch on concrete
executors, Docker, MPI, WSL, or SLURM.

### 4.3 `executors/`

Executors turn a `TaskSpec` into an `ExecutionResult`.

Initial executor families are:

- `NativeExecutor`;
- `DockerExecutor`;
- later MPI-related execution components;
- optional WSL support if it remains justified.

Executors may import `core`, but must not contain Rosetta workflow logic.

**Invariant:** an executor must be usable with a valid `TaskSpec` without
knowing which Rosetta workflow produced it.

### 4.4 `launchers/` and `schedulers/`

Process launch and scheduler allocation are separate concepts.

MPI belongs primarily to a launcher layer: it transforms one executable task
into one distributed process invocation.

SLURM allocation discovery belongs to a scheduler adapter: it interprets the
allocation already granted to the process.

A scheduler adapter must not become a full cluster-submission framework during
the initial v2 reconstruction.

### 4.5 `workflows/`

FastRelax, Cartesian ddG, RosettaLigand, MutateRelax, PROSS, Supercharge, and
similar helpers sit above the Rosetta layer.

A workflow may:

- validate workflow-specific inputs;
- construct a `RosettaInvocation`;
- declare workflow-specific expected artifacts;
- parse workflow-specific outputs.

A workflow must not launch subprocesses or select concrete executors.

### 4.6 `analysis/`

Analysis consumes `Artifact`, `ArtifactManifest`, or `ExecutionResult`.
Path-based entry points may remain temporarily for 1.x compatibility.

Parsing and plotting are separate concerns. Heavy analysis dependencies should
not be required by the execution kernel.

## 5. Dependency direction

The intended dependency graph is:

```text
workflows  --->  rosetta  --->  core  <---  executors
                    |                        ^
                    |                        |
                    v                        |
                 parsing              launchers/schedulers

analysis  <---  ExecutionResult / ArtifactManifest
```

Forbidden directions include:

```text
core      -X-> executors
core      -X-> rosetta
rosetta   -X-> Docker/MPI/WSL/SLURM
workflows -X-> concrete executors
analysis  -X-> executor dispatch
```

No central module may restore the old pattern by switching on executor type.

## 6. Compiler boundary

`RosettaCompiler` is a dedicated object. Compilation is not implemented as
backend-specific branches inside `RosettaInvocation`.

The compiler is responsible for converting Rosetta semantics into immutable
task descriptions. It does not start processes, mount filesystems, inspect
Docker images, invoke MPI, query SLURM, or mutate user input files.

Compilation must be unit-testable on a machine without Rosetta installed.

Binary lookup is not allowed to make compilation backend-dependent. The
compiler preserves the requested executable token. The executor is responsible
for resolving that token in its own launch environment and recording resolved
binary provenance when possible.

## 7. Filesystem and path semantics

A `TaskSpec` uses the host-side filesystem namespace as the canonical namespace
for `cwd`, inputs, output roots, and artifact paths.

Executors that introduce another namespace, such as Docker or WSL, own the
translation. Translation must not mutate the original `TaskSpec`.

Docker should prefer same-path bind mounts when practical so that compiled
arguments can remain unchanged. If translation is required, it is an internal
executor preparation step and produced artifact paths must be translated back
to the host namespace before returning `ExecutionResult`.

The compiler must not silently rewrite user files. In particular, the legacy
CRLF-to-LF behavior must not remain as an implicit compilation side effect.
Validation or explicit staging transformations may be introduced separately.

## 8. Failure semantics

The v2 rule is:

> **A process failure is a result. An infrastructure failure is an exception.**

Examples:

- Rosetta starts and exits with code 1:
  return `ExecutionResult(status=FAILED, exit_code=1, ...)`.
- Rosetta starts and exits with code 0:
  return `ExecutionResult(status=SUCCEEDED, exit_code=0, ...)`.
- The executor cannot create the working directory:
  raise `ExecutionError`.
- Docker cannot contact its daemon:
  raise `ExecutionError`.
- A requested binary cannot be launched:
  raise a structured execution/binary-resolution error.

A non-zero Rosetta exit code must not be converted into a generic
`RuntimeError`.

## 9. `nstruct` semantics

v2 distinguishes Rosetta-native replication from external task fan-out.

The default is **native `nstruct`**:

```text
nstruct = N, mode = NATIVE
        -> one TaskSpec containing -nstruct N
```

External fan-out is explicit:

```text
nstruct = N, mode = EXTERNAL
        -> N TaskSpecs, each representing one independently addressable run
```

This policy is part of Rosetta compilation and must not change because the
selected executor is Native, Docker, MPI, or another backend.

The 1.x compatibility facade may translate legacy behavior to
`mode=EXTERNAL` where needed to preserve established semantics.

## 10. Artifact model

Outputs are first-class results.

The compiler declares expected artifact patterns and semantic roles. After a
process exits, the executor returns an `ArtifactManifest` containing artifacts
observed under the task output root.

Initial semantic roles include:

- `structure`;
- `scorefile`;
- `silent_file`;
- `log`;
- `generic_output`.

Missing required artifacts are represented in structured result/provenance
information and may be promoted to workflow-level validation failures.
Unexpected outputs are collected but do not fail a run by default.

Consumers should not need to reverse-engineer directory naming conventions to
locate scorefiles or structures.

## 11. Provenance

A reproducible result must retain enough information to explain how it was
produced. The result/run manifest should include, where available:

- task identifier;
- original executable request;
- resolved executable path or container identity;
- Rosetta version/revision if detected;
- command arguments;
- working directory;
- executor identity;
- timestamps and duration;
- exit code and execution status;
- relevant environment overlay;
- input references;
- artifact manifest.

The on-disk run manifest is versioned independently from Python object layout so
that REvoCompute and other consumers can read it without importing RosettaPy.

## 12. Compatibility facade

The existing `Rosetta(...)` interface may remain temporarily as a 1.x
compatibility facade.

The facade may translate legacy arguments into v2 objects and preserve selected
legacy defaults. It must not define new v2 behavior and must not cause
backend-specific branches to re-enter the kernel.

Compatibility is subordinate to the v2 invariants. Behavior that cannot be
preserved without violating the new architecture should be deprecated rather
than reintroduced into core.

## 13. Testing architecture

Tests are separated into four classes:

1. **Pure unit tests** — data models, compiler rendering, parsers, path policies.
2. **Executor contract tests** — the same behavioral contract applied to every
   executor.
3. **Backend integration tests** — Docker, MPI, WSL, or scheduler-specific
   behavior.
4. **Licensed Rosetta integration tests** — canonical real Rosetta workflows.

A new executor is not complete until it passes the shared executor contract
suite.

## 14. Proposed package layout

The exact file split may evolve, but dependency direction may not.

```text
src/RosettaPy/
    core/
        artifact.py
        errors.py
        executor.py
        result.py
        task.py

    rosetta/
        binary.py
        compiler.py
        invocation.py
        scripts.py

    executors/
        native.py
        docker.py

    launchers/
        mpi.py

    schedulers/
        slurm.py

    workflows/
        fastrelax.py
        cartesian_ddg.py
        rosettaligand.py
        ...

    analysis/
        scorefile.py
        ddg.py
        ...
```

## 15. Architectural anti-patterns

The following changes should be rejected during review:

- adding `isinstance(executor, ...)` branches to compiler/core code;
- adding Docker/MPI/WSL path rules to `RosettaInvocation`;
- allowing workflows to call `subprocess` directly;
- returning a `TaskSpec` as if it were an execution result;
- treating non-zero Rosetta exit codes as infrastructure exceptions;
- silently mutating user input files during compilation;
- making artifact discovery depend on undocumented directory guesses;
- expanding the first v2 milestone into Apptainer, SSH, retries, caching, or a
  generic scheduler framework.

The reconstruction succeeds by making the center smaller, not by moving the
same branching behind new class names.
