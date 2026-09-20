"""Unit tests for the v2 executor protocol and shared execution errors."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from RosettaPy.core import (
    BinaryResolutionError,
    CompilationError,
    ExecutionError,
    ExecutionResult,
    ExecutionStatus,
    Executor,
    RosettaPyError,
    TaskSpec,
)


class _ConformingExecutor:
    """A minimal structural implementation of the executor contract."""

    def __init__(self, identity: str = "stub"):
        self._identity = identity
        self.seen: list[TaskSpec] = []

    @property
    def identity(self) -> str:
        return self._identity

    def execute(self, task: TaskSpec) -> ExecutionResult:
        self.seen.append(task)
        now = datetime.now(timezone.utc)
        return ExecutionResult(
            task_id=task.task_id,
            status=ExecutionStatus.SUCCEEDED,
            exit_code=0,
            stdout="",
            stderr="",
            started_at=now,
            finished_at=now,
            duration_seconds=0.0,
            executor=self.identity,
        )


class TestExecutorProtocol:
    def test_protocol_is_runtime_checkable(self):
        assert isinstance(_ConformingExecutor(), Executor)

    def test_protocol_exposes_only_identity_and_execute(self):
        public = {name for name in Executor.__dict__ if not name.startswith("_")}
        assert "execute" in public
        assert "identity" in public

    def test_protocol_does_not_require_batch_execution(self):
        for name in ("execute_many", "run", "run_many"):
            assert name not in Executor.__dict__

    def test_object_without_execute_is_not_an_executor(self):
        class NotAnExecutor:
            @property
            def identity(self) -> str:
                return "nope"

        assert not isinstance(NotAnExecutor(), Executor)

    def test_executor_returns_a_result_for_one_task(self):
        executor = _ConformingExecutor()
        task = TaskSpec(task_id="run-a", argv=("rosetta_scripts",), cwd=".")
        result = executor.execute(task)
        assert isinstance(result, ExecutionResult)
        assert result.executor == "stub"
        assert executor.seen == [task]


class TestExecutionErrors:
    def test_error_hierarchy(self):
        assert issubclass(ExecutionError, RosettaPyError)
        assert issubclass(CompilationError, RosettaPyError)
        assert issubclass(BinaryResolutionError, ExecutionError)

    def test_execution_error_carries_message(self):
        error = ExecutionError("cannot create working directory")
        assert error.message == "cannot create working directory"
        assert str(error) == "cannot create working directory"
        assert error.partial_result is None

    def test_execution_error_may_carry_partial_result(self):
        now = datetime.now(timezone.utc)
        partial = ExecutionResult(
            task_id="run-a",
            status=ExecutionStatus.FAILED,
            exit_code=None,
            stdout="",
            stderr="",
            started_at=now,
            finished_at=now,
            duration_seconds=0.0,
            executor="native",
        )
        error = ExecutionError("collector crashed", partial_result=partial)
        assert error.partial_result is partial
        assert "partial_result=" in repr(error)

    def test_binary_resolution_error_records_the_request(self):
        error = BinaryResolutionError("rosetta_scripts", detail="not on PATH", environment="native")
        assert error.request == "rosetta_scripts"
        assert "Could not resolve executable 'rosetta_scripts'" in str(error)
        assert "'native'" in str(error)
        assert "not on PATH" in str(error)
        assert isinstance(error, ExecutionError)

    def test_binary_resolution_error_without_environment(self):
        assert "in " not in str(BinaryResolutionError("rosetta_scripts"))

    def test_compilation_error_is_not_an_execution_error(self):
        assert not issubclass(CompilationError, ExecutionError)

    def test_errors_are_catchable_by_kernel_type(self):
        with pytest.raises(RosettaPyError):
            raise ExecutionError("boom")
