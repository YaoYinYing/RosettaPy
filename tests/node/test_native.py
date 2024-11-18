# Test cases
from unittest.mock import MagicMock, patch

from RosettaPy.node.native import Native
from RosettaPy.utils.task import RosettaCmdTask, _non_isolated_execute
from RosettaPy.utils.tools import tmpdir_manager


def test_native_initialization():
    native = Native()
    assert native.nproc == 4
    assert native.run_func == _non_isolated_execute

    def mock_run_func(task: RosettaCmdTask) -> RosettaCmdTask:
        return task

    native_custom = Native(nproc=2, run_func=mock_run_func)
    assert native_custom.nproc == 2
    assert native_custom.run_func == mock_run_func


def test_native_run():
    # Mock the execute function
    mock_execute = MagicMock(side_effect=lambda task, func: func(task))

    # Create some sample tasks
    with tmpdir_manager() as dir1, tmpdir_manager() as dir2:
        tasks = [
            RosettaCmdTask(cmd=["cmd1"], base_dir=dir1, task_label="label1"),
            RosettaCmdTask(cmd=["cmd2"], base_dir=dir2, task_label="label2"),
        ]

        # Mock the Parallel and delayed functions
        with patch(
            "joblib.Parallel", side_effect=lambda *args, **kwargs: [mock_execute(task, lambda x: x) for task in tasks]
        ) as mock_parallel:
            native = Native(nproc=2, run_func=lambda x: x)
            result = native.run(tasks)

        # Assert that the tasks were executed and returned correctly
        assert len(result) == len(tasks)
        for i, task in enumerate(tasks):
            assert result[i] == task


def test_native_run_with_custom_run_func():
    # Define a custom run function
    def custom_run_func(task: RosettaCmdTask) -> RosettaCmdTask:
        task.task_label = f"custom_{task.task_label}"
        return task

    # Mock the execute function
    mock_execute = MagicMock(side_effect=lambda task, func: func(task))

    with tmpdir_manager() as dir1, tmpdir_manager() as dir2:
        # Create some sample tasks
        tasks = [
            RosettaCmdTask(cmd=["cmd1"], base_dir=dir1, task_label="label1"),
            RosettaCmdTask(cmd=["cmd2"], base_dir=dir2, task_label="label2"),
        ]

        # Mock the Parallel and delayed functions
        with patch(
            "joblib.Parallel",
            side_effect=lambda *args, **kwargs: [mock_execute(task, custom_run_func) for task in tasks],
        ) as mock_parallel:
            native = Native(nproc=2, run_func=custom_run_func)
            result = native.run(tasks)

        # Assert that the tasks were executed with the custom run function and returned correctly
        assert len(result) == len(tasks)
        for i, task in enumerate(tasks):
            assert result[i].task_label == f"custom_{task.task_label}"

    # Assert that the Parallel function was called with the correct arguments
    # mock_parallel.assert_called_once_with(n_jobs=2, verbose=100)
