"""
The Rosetta layer: Rosetta semantics, independent of execution environment.

This package owns what a Rosetta computation *is*:

- the unresolved :class:`~RosettaPy.rosetta.binary.RosettaBinaryRequest`;
- the environment-free :class:`~RosettaPy.rosetta.invocation.RosettaInvocation`;
- Rosetta command rendering and ``nstruct`` policy in
  :class:`~RosettaPy.rosetta.compiler.RosettaCompiler`;
- Rosetta output expectations.

It may import ``core`` types. It MUST NOT import or branch on concrete
executors, container runtimes, MPI, WSL, or schedulers, and compilation MUST be
testable on a machine without Rosetta installed.
"""

from .binary import RosettaBinaryRequest
from .compiler import CompileContext, RosettaCompiler
from .invocation import NStructMode, RosettaInvocation

__all__ = [
    "CompileContext",
    "NStructMode",
    "RosettaBinaryRequest",
    "RosettaCompiler",
    "RosettaInvocation",
]
