# RosettaPy v2 design documents

Status: **Normative design baseline for the `main_v2_wip` branch**

Tracking issue: #125

RosettaPy v2 is being developed on the long-lived integration branch
`main_v2_wip`. The `main` branch remains the stable 1.x line until the v2
work reaches an explicit release-candidate gate.

This directory is the entry point for contributors and coding agents working on
the v2 reconstruction. Read these documents in this order:

1. [ARCHITECTURE.md](ARCHITECTURE.md) — system boundaries, dependency
   direction, responsibilities, and invariants.
2. [IMPLEMENTATION_CONTRACT.md](IMPLEMENTATION_CONTRACT.md) — decisions that
   are no longer open to implementation-time interpretation.
3. [MIGRATION_PLAN.md](MIGRATION_PLAN.md) — branch policy, staged PR sequence,
   compatibility strategy, and acceptance gates.

## Authority

The implementation contract is normative. If implementation code and the
contract disagree, the implementation is wrong unless a dedicated design PR
changes the contract first.

Architecture changes must not be smuggled into feature or migration PRs. A PR
that needs to change a core invariant, a public v2 data model, failure
semantics, or executor semantics must update these documents explicitly and
justify the change.

Issue #125 remains the roadmap and discussion record. These repository
documents are the implementation specification.

## Development rule

A coding agent should not be asked to "implement issue #125" as one task.
Instead, it should be given one milestone or one PR-sized slice from
[MIGRATION_PLAN.md](MIGRATION_PLAN.md), with these documents treated as fixed
constraints.

The central design goal is:

> **RosettaPy defines a reproducible Rosetta run, while execution backends
> implement a stable task/result contract.**

The practical success metric is simple: adding a new executor should require
approximately zero changes outside that executor, its configuration, and its
tests.
