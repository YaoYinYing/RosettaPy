# RosettaPy v2 migration plan

Status: **Normative process plan**

Tracking issue: #125

## 1. Branch policy

RosettaPy v2 develops on the long-lived integration branch:

```text
main
  |
  +-- main_v2_wip
         |
         +-- short-lived v2 PR branches
```

Rules:

- `main` remains the stable 1.x branch.
- Every v2 reconstruction PR MUST target `main_v2_wip`.
- New v2 work branches MUST start from the current `main_v2_wip`.
- `main_v2_wip` MUST NOT be merged into `main` until an explicit v2
  release-candidate review.
- Necessary 1.x fixes MAY be forward-ported from `main` to `main_v2_wip`.
- v2 architectural work MUST NOT be backported to `main` as part of routine
  maintenance.

This policy keeps the stable package releasable while allowing the v2
reconstruction to proceed through small reviewed PRs.

## 2. PR philosophy

The v2 rewrite must not land as one large replacement.

Each PR should prove one architectural claim and preserve a reviewable diff.
Documentation and tests should lead implementation.

A PR must not quietly broaden scope because an adjacent cleanup appears easy.

## 3. PR sequence

### PR 1 — architecture and implementation contract

Scope: **documentation only**

Deliverables:

- v2 architecture;
- normative implementation contract;
- migration and branch policy;
- explicit resolved design decisions;
- non-goals for the first milestone.

No runtime code, package API, dependency, or test behavior should change.

Exit criterion:

> A clean coding-agent session can read the repository documents and implement
> the next milestone without inventing core architecture.

### PR 2 — core models and Rosetta compiler

Implement only:

- `core` task/result/artifact/error models;
- `Executor` protocol;
- `RosettaInvocation`;
- `RosettaCompiler`;
- native/external `nstruct` compilation;
- compiler unit tests;
- JSON manifest schema skeleton if required by the data model.

Do not implement Docker, MPI, WSL, SLURM, or workflow migration.

Exit criterion:

- compilation requires no Rosetta installation;
- one canonical FastRelax-style invocation compiles deterministically;
- compiler code imports no concrete executor.

### PR 3 — NativeExecutor and first end-to-end contract

Implement:

- `NativeExecutor`;
- process/result failure semantics;
- stdout/stderr capture;
- timing;
- artifact collection;
- run-manifest serialization;
- shared executor contract tests;
- one canonical real or fixture-based end-to-end path.

A minimal legacy facade bridge may be introduced only if needed to prove
compatibility.

Exit criterion:

```text
RosettaInvocation
      -> RosettaCompiler
      -> TaskSpec
      -> NativeExecutor
      -> ExecutionResult
      -> ArtifactManifest
```

works without executor-specific logic in the compiler.

### PR 4 — Docker executor

Implement Docker against the unchanged task/result contract.

The core and Rosetta compiler should require no semantic modification. If Docker
requires a core redesign, stop and review the contract rather than patching
backend checks into the center.

Exit criterion:

- the canonical invocation is semantically equivalent under Native and Docker;
- host/container path behavior is contained in Docker execution code;
- Docker passes the shared executor contract suite.

### PR 5 — MPI launcher and SLURM allocation adapter

Implement MPI as distributed launch of one task, not as a fake batch executor.

Move SLURM allocation discovery out of MPI.

Exit criterion:

- `MpiLauncher` owns MPI command rendering and hostfile lifecycle;
- `SlurmAllocation` owns SLURM environment discovery;
- the Rosetta compiler remains unchanged.

### PR 6 — compatibility facade and workflow migration

Migrate retained workflow helpers incrementally:

- FastRelax;
- Cartesian ddG;
- RosettaLigand;
- MutateRelax;
- PROSS;
- Supercharge;
- other retained workflows after review.

Workflow code must produce invocations/tasks and consume results; it must not
select or implement process execution.

Exit criterion:

- legacy common paths have documented v2 equivalents;
- workflow modules do not import concrete executors.

### PR 7 — analysis, packaging, and dependency reduction

Move analyzers onto artifacts/results and split heavy optional dependencies.

Review:

- pandas;
- matplotlib;
- RDKit;
- Biopython;
- Docker SDK;
- Spark support;
- Python-version support;
- unnecessary upper version pins.

Exit criterion:

- installing the execution core does not require unrelated heavy analysis or
  ligand dependencies.

### PR 8 — REvoCompute reference integration

Only after executor contracts are proven stable:

- map `ExecutionResult` to REvoCompute task results;
- map `ArtifactManifest` to the result workspace;
- build a reference Rosetta runner;
- verify that Rosetta command semantics are not duplicated in REvoCompute.

This PR belongs after the RosettaPy contract is mature enough to consume rather
than reinterpret.

## 4. Compatibility strategy

The migration favors architectural integrity over perfect compatibility.

Compatibility priority is:

1. preserve scientifically meaningful Rosetta behavior;
2. preserve common user-facing calls where they can delegate cleanly;
3. provide explicit deprecation and migration guidance;
4. remove behavior that can only be preserved by violating v2 invariants.

The legacy API may survive temporarily as a facade. It must not become a second
implementation.

## 5. Required canonical cases

The reconstruction must keep a small set of canonical cases throughout the PR
series:

- plain Rosetta binary invocation;
- `rosetta_scripts` with script variables;
- FastRelax-style execution;
- `nstruct > 1` in native mode;
- `nstruct > 1` in external mode;
- process non-zero exit;
- paths containing spaces;
- expected/missing artifact behavior.

These cases are more important than broad shallow test expansion during the
kernel reconstruction.

## 6. Review gates

Every implementation PR should answer:

1. Does this change alter a v2 contract?
2. Does core now know about a concrete backend?
3. Does Rosetta compilation depend on execution environment?
4. Is a process failure still represented as a result?
5. Can output artifacts be discovered without guessing undocumented paths?
6. Did this PR add scope that belongs to a later milestone?
7. Could the same behavior be achieved by deleting or simplifying code?

If a PR changes a normative answer, update the design documents first.

## 7. Agent execution protocol

For coding agents:

- read all files under `docs/v2/` before editing runtime code;
- treat normative contracts as constraints, not suggestions;
- implement only the named PR milestone;
- inspect existing behavior before deleting compatibility code;
- prefer deletion and delegation over parallel replacement abstractions;
- do not add speculative extension points for deferred features;
- run the smallest relevant tests continuously;
- summarize any required contract change instead of silently implementing it.

An agent should stop a milestone when it discovers that satisfying the task
requires violating a normative invariant. That is a design-review signal, not a
reason to invent a local exception.

## 8. v2 release gate

`main_v2_wip` becomes eligible for an explicit release-candidate review when:

- Native and Docker pass the same executor contract suite;
- MPI/SLURM no longer leak into Rosetta compilation;
- retained workflows no longer own process execution;
- artifact/result contracts are stable and documented;
- common 1.x migration paths are documented;
- default dependencies have been reduced;
- real Rosetta integration tests cover the canonical path;
- adding a new executor does not require edits to the Rosetta compiler or core.

Only after that review should the project decide how v2 reaches `main` and how
the major version is released.
