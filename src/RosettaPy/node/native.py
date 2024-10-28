"""
Wrapper of Native Runs
"""

from dataclasses import dataclass
from functools import partial
from typing import Callable, List

from joblib import Parallel, delayed

from ..utils.task import RosettaCmdTask, _non_isolated_execute, execute


@dataclass
class Native:
    """
    Native class is used to run a list of RosettaCmdTask tasks in parallel without MPI support.

    Attributes:
        nproc: int - The maximum number of processes to use for parallel execution.
        run_func: Callable[[RosettaCmdTask], RosettaCmdTask] - A function that defines how to execute a single
        RosettaCmdTask.
    """

    nproc: int = 4

    run_func: Callable[[RosettaCmdTask], RosettaCmdTask] = _non_isolated_execute

    def run(self, tasks: List[RosettaCmdTask]) -> List[RosettaCmdTask]:
        """
        Run a list of RosettaCmdTask tasks in parallel.

        Args:
            tasks: List[RosettaCmdTask] - A list of RosettaCmdTask tasks to be executed.

        Returns:
            List[RosettaCmdTask] - A list of RosettaCmdTask tasks after execution.
        """
        # Create a new function by partially applying self.run_func to the execute function
        run_func = partial(execute, func=self.run_func)

        # Use joblib's Parallel and delayed functions to run tasks in parallel
        # n_jobs=self.nproc specifies the maximum number of processes to use
        # verbose=100 sets the verbosity level to track the progress of task execution
        ret = Parallel(n_jobs=self.nproc, verbose=100)(delayed(run_func)(task) for task in tasks)

        # Return the list of executed tasks
        return list(ret)  # type: ignore
