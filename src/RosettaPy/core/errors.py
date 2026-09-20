"""
Shared execution errors for the RosettaPy v2 kernel.

The v2 failure rule is:

    A process failure is a result. An infrastructure failure is an exception.

Consequently the errors in this module are only raised when the execution
environment itself cannot be established or maintained. A Rosetta process that
starts and exits with a non-zero code MUST be reported as a failed
:class:`~RosettaPy.core.result.ExecutionResult` instead of raising.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .result import ExecutionResult


class RosettaPyError(Exception):
    """Base class for all RosettaPy v2 errors."""


class ExecutionError(RosettaPyError):
    """
    Raised when an executor cannot establish or maintain execution.

    Examples:

    - the executor cannot create the working directory;
    - a container runtime daemon is unavailable;
    - the requested executable cannot be launched;
    - required mount preparation fails.

    A process that was successfully launched but exited with a non-zero code is
    *not* an :class:`ExecutionError`; it is a failed
    :class:`~RosettaPy.core.result.ExecutionResult`.
    """

    def __init__(self, message: str, *, partial_result: ExecutionResult | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.partial_result = partial_result

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r}, partial_result={self.partial_result!r})"


class CompilationError(RosettaPyError):
    """
    Raised when a compiler cannot translate user intent into a valid task.

    Compilation failures are user/input errors. They are detected before any
    execution environment is touched, which is what allows the Rosetta compiler
    to run on a machine without Rosetta installed.
    """


class BinaryResolutionError(ExecutionError):
    """
    Raised when a logical executable request cannot be resolved in a launch
    environment.

    This is an execution-time concern: the compiler preserves the requested
    executable token and never requires the binary to exist while compiling.
    """

    def __init__(
        self,
        request: str,
        *,
        detail: str = "",
        environment: Any | None = None,
        partial_result: ExecutionResult | None = None,
    ) -> None:
        message = f"Could not resolve executable {request!r}"
        if environment is not None:
            message += f" in {environment!r}"
        if detail:
            message += f": {detail}"
        super().__init__(message, partial_result=partial_result)
        self.request = request
        self.detail = detail
        self.environment = environment
