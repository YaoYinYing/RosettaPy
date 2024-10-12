import os
import copy
import subprocess
import functools
import warnings
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Union
from datetime import datetime

from joblib import Parallel, delayed


# internal imports
from .rosetta_finder import RosettaBinary, RosettaFinder
from .utils import (
    isolate,
    RosettaScriptsVariableGroup,
    RosettaCmdTask,
    IgnoreMissingFileWarning,
)
from .node import MPI_node, RosettaContainer
from .node.mpi import MPI_IncompatibleInputWarning


@dataclass
class Rosetta:
    """
    A wrapper class for running Rosetta command-line applications.

    Attributes:
        bin (RosettaBinary): The Rosetta binary to execute.
        nproc (int): Number of processors to use.
        flags (List[str]): List of flag files to include.
        opts (List[str]): List of command-line options.
        use_mpi (bool): Whether to use MPI for execution.
        mpi_node (MPI_node): MPI node configuration.
    """

    bin: Union[RosettaBinary, str]
    nproc: Union[int, None] = field(default_factory=os.cpu_count)

    flags: Optional[List[str]] = field(default_factory=list)
    opts: Optional[List[Union[str, RosettaScriptsVariableGroup]]] = field(default_factory=list)
    use_mpi: bool = False
    run_node: Optional[Union[MPI_node, RosettaContainer]] = None

    job_id: str = "default"
    output_dir: str = ""
    save_all_together: bool = False

    isolation: bool = False
    verbose: bool = False

    @staticmethod
    def expand_input_dict(d: Dict[str, Union[str, RosettaScriptsVariableGroup]]) -> List[str]:
        """
        Expands a dictionary containing strings and variable groups into a flat list.

        :param d: Dictionary with keys and values that can be either strings or variable groups.
        :return: A list of expanded key-value pairs.
        """

        opt_list = []
        for k, v in d.items():
            if not isinstance(v, RosettaScriptsVariableGroup):
                opt_list.extend([k, v])
            else:
                opt_list.extend(v.aslonglist)
        return opt_list

    @property
    def output_pdb_dir(self) -> str:
        """
        Returns the path to the PDB output directory, creating it if necessary.

        :return: Path to the PDB output directory.
        """
        if not self.output_dir:
            raise ValueError("Output directory not set.")
        p = os.path.join(self.output_dir, self.job_id, "pdb" if not self.save_all_together else "all")
        os.makedirs(p, exist_ok=True)
        return p

    @property
    def output_scorefile_dir(self) -> str:
        """
        Returns the path to the score file output directory, creating it if necessary.

        :return: Path to the score file output directory.
        """
        if not self.output_dir:
            raise ValueError("Output directory not set.")
        p = os.path.join(self.output_dir, self.job_id, "scorefile" if not self.save_all_together else "all")
        os.makedirs(p, exist_ok=True)
        return p

    def __post_init__(self):
        """
        Post-initialization setup for the Rosetta job configuration.
        """

        if self.flags is None:
            self.flags = []
        if self.opts is None:
            self.opts = []

        if isinstance(self.bin, str):
            if not isinstance(self.run_node, RosettaContainer):
                # local direct runs
                self.bin = RosettaFinder().find_binary(self.bin)
            else:
                # to container
                self.bin = RosettaBinary(dirname="/usr/local/bin/", binary_name=self.bin)

        if self.run_node is not None:
            if self.bin.mode != "mpi":
                warnings.warn(
                    UserWarning("MPI nodes are given yet not supported. Maybe in Dockerized Rosetta container?")
                )

            self.use_mpi = True
            return

        else:
            warnings.warn(UserWarning("Using MPI binary as static build."))
            self.use_mpi = False

    @staticmethod
    def _isolated_execute(task: RosettaCmdTask, func: Callable[[RosettaCmdTask], RosettaCmdTask]) -> RosettaCmdTask:
        """
        Executes a given task in an isolated environment.

        This method is used to run a specific function within an isolated context,
        ensuring that the execution of the task is separated from the global environment.
        It is typically used for scenarios requiring a clean or restricted execution context.

        Parameters:
        - task (RosettaCmdTask): A task object containing necessary information.
        - func (Callable[[RosettaCmdTask], RosettaCmdTask]): A function that takes and returns a RosettaCmdTask object,
        which will be executed within the isolated environment.

        Returns:
        - RosettaCmdTask: The task object after execution.

        Raises:
        - ValueError: If the task label (task_label) or base directory (base_dir) is missing.
        """
        # Check if the task label exists; raise an exception if it does not
        if not task.task_label:
            raise ValueError("Task label is required when executing the command in isolated mode.")

        # Check if the base directory exists; raise an exception if it does not
        if not task.base_dir:
            raise ValueError("Base directory is required when executing the command in isolated mode.")

        with isolate(save_to=task.runtime_dir):
            return func(task)

    @staticmethod
    def execute(
        task: RosettaCmdTask, func: Optional[Callable[[RosettaCmdTask], RosettaCmdTask]] = None
    ) -> RosettaCmdTask:
        """
        Executes the given task with support for both non-isolated and isolated execution modes,
        which can be customized via the provided function argument.

        :param task: The task object to be executed, encapsulating the specific content to run.
        :param func: An optional parameter specifying the function to execute the task. If not provided,
                     defaults to a non-isolated execution mode.
        :return: The task object after execution.

        Notes:
        - If no task label (task_label) is specified, the task is executed directly using the specified function.
        - Otherwise, the task is executed in an isolated mode.
        - If the function argument func is not provided, a default non-isolated execution mode is used.
        """
        # Use the default non-isolated execution mode if no function is provided
        if func is None:
            func = Rosetta._non_isolated_execute
        if not task.task_label:
            return func(task)
        return Rosetta._isolated_execute(task, func)

    @staticmethod
    def _non_isolated_execute(task: RosettaCmdTask) -> RosettaCmdTask:
        """
        Executes a command and handles its output and errors.

        :param task: The command task to execute, containing the command and its configuration.
        :return: Returns the command task object after execution, including the command execution results.
        """
        # Use subprocess.Popen to execute the command, redirecting output and setting encoding to UTF-8.
        process = subprocess.Popen(
            task.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf-8"
        )

        # Print command execution information.
        print(f'Launching command: {" ".join(task.cmd)}')
        # Communicate to get the command's output and error.
        stdout, stderr = process.communicate()
        # Wait for the command to complete and get the return code.
        retcode = process.wait()

        if retcode:
            # If the command fails, print the failure message and raise an exception.
            print(f"Command failed with return code {retcode}")
            print(stdout)
            warnings.warn(RuntimeWarning(stderr))
            raise RuntimeError(f"Command failed with return code {retcode}")

        return task

    def setup_tasks_local(
        self,
        base_cmd: List[str],
        inputs: Optional[List[Dict[str, Union[str, RosettaScriptsVariableGroup]]]] = None,
        nstruct: Optional[int] = None,
    ) -> List[RosettaCmdTask]:
        """
        Setups a command locally, possibly in parallel.

        :param cmd: Base command to be executed.
        :param inputs: List of input dictionaries.
        :param nstruct: Number of structures to generate.
        :return: List of RosettaCmdTask.
        """
        _base_cmd = copy.copy(base_cmd)

        now = datetime.now().strftime("%Y%m%d_%H%M%S")  # formatted date-time

        if nstruct and nstruct > 0:
            # if inputs are given and nstruct is specified, flatten and pass inputs to all tasks
            if inputs:
                for i, _i in enumerate(inputs):
                    __i = self.expand_input_dict(_i)
                    _base_cmd.extend(__i)
                    print(f"Additional input args is passed: {__i}")

            cmd_jobs = [
                RosettaCmdTask(
                    cmd=_base_cmd
                    + [
                        "-suffix",
                        f"_{i:05}",
                        "-no_nstruct_label",
                        "-out:file:scorefile",
                        f"{self.job_id}.score.{i:05}.sc",
                    ],
                    task_label=f"task_{self.job_id}-{i:05}" if self.isolation else None,
                    base_dir=os.path.join(self.output_dir, f"{now}-{self.job_id}-runtimes"),
                )
                for i in range(1, nstruct + 1)
            ]
            warnings.warn(UserWarning(f"Processing {len(cmd_jobs)} commands on {nstruct} decoys."))
            return cmd_jobs
        if inputs:
            # if nstruct is not given and inputs are given, expand input and distribute them as task payload
            cmd_jobs = [
                RosettaCmdTask(
                    cmd=_base_cmd + self.expand_input_dict(input_arg),
                    task_label=f"task-{self.job_id}-no-{i}" if self.isolation else None,
                    base_dir=os.path.join(self.output_dir, f"{now}-{self.job_id}-runtimes"),
                )
                for i, input_arg in enumerate(inputs)
            ]
            warnings.warn(UserWarning(f"Processing {len(cmd_jobs)} commands"))
            return cmd_jobs

        cmd_jobs = [RosettaCmdTask(cmd=_base_cmd)]

        warnings.warn(UserWarning("No inputs are given. Running single job."))
        return cmd_jobs

    def setup_tasks_mpi(
        self,
        base_cmd: List[str],
        inputs: Optional[List[Dict[str, Union[str, RosettaScriptsVariableGroup]]]] = None,
        nstruct: Optional[int] = None,
        dockerized: bool = False,
    ) -> List[RosettaCmdTask]:
        """
        Setup a command using MPI.

        :param cmd: Base command to be executed.
        :param inputs: List of input dictionaries.
        :param nstruct: Number of structures to generate.
        :return: List of RosettaCmdTask
        """
        assert isinstance(
            self.run_node, (MPI_node, RosettaContainer)
        ), "MPI node/RosettaContainer instance is not initialized."

        _base_cmd = copy.copy(base_cmd)
        if inputs:
            for i, _i in enumerate(inputs):
                _base_cmd.extend(self.expand_input_dict(_i))

        if nstruct:
            _base_cmd.extend(["-nstruct", str(nstruct)])

        if dockerized:
            # skip setups of MPI_node because we have already recomposed.
            return [RosettaCmdTask(cmd=_base_cmd)]

        assert isinstance(self.run_node, (MPI_node)), "MPI node instance is required for MPI run."

        with self.run_node.apply(_base_cmd) as updated_cmd:
            if self.isolation:
                warnings.warn(RuntimeWarning("Ignoring isolated mode for MPI run."))
            return [RosettaCmdTask(cmd=updated_cmd)]

    def run_mpi(
        self,
        tasks: List[RosettaCmdTask],
    ) -> List[RosettaCmdTask]:
        """
        Execute tasks using MPI.

        This method is designed to execute a given list of tasks using MPI (Message Passing Interface), which is a programming model for distributed memory systems that allows developers to write highly scalable parallel applications.

        Parameters:
        - self: Instance reference, allowing access to other methods and attributes of the class.
        - tasks: A list of RosettaCmdTask objects representing the tasks to be executed.

        Returns:
        - A list containing RosettaCmdTask objects representing the results of the executed tasks.

        Note:
        - This method is particularly suitable for tasks requiring execution in a parallel computing environment.
        - The current implementation only executes the first task in the list, ignoring the rest.
        """

        # Execute the first task non-isolately
        ret = Rosetta._non_isolated_execute(tasks[0])

        # Return the result as a list
        return [ret]

    def run_local(
        self,
        tasks: List[RosettaCmdTask],
    ) -> List[RosettaCmdTask]:
        """
        Execute a list of Rosetta command tasks locally in parallel.

        This method runs the provided Rosetta command tasks concurrently using multiple processors
        to improve efficiency and speed up the execution of large sets of tasks.

        Parameters:
        - self: The instance of the class.
        - tasks (List[RosettaCmdTask]): A list of Rosetta command tasks to be executed.

        Returns:
        - List[RosettaCmdTask]: A list of executed Rosetta command tasks.
        """
        ret = Parallel(n_jobs=self.nproc, verbose=100)(delayed(Rosetta.execute)(cmd_job) for cmd_job in tasks)
        return list(ret)  # type: ignore

    def run_local_docker(
        self,
        tasks: List[RosettaCmdTask],
    ) -> List[RosettaCmdTask]:
        """
        Executes a list of Rosetta command tasks using a local Docker container.

        Parameters:
            tasks (List[RosettaCmdTask]): A list of Rosetta command tasks to be executed.

        Returns:
            List[RosettaCmdTask]: The results of the executed tasks.
        """
        # Ensure that the run_node is an instance of RosettaContainer
        assert isinstance(
            self.run_node, RosettaContainer
        ), "To run with local docker container, you need to initialize RosettaContainer instance as self.run_node"

        # Define a partial function to execute tasks using the run_node
        run_func = functools.partial(Rosetta.execute, func=self.run_node.run_single_task)

        # Execute tasks in parallel using multiple jobs
        ret = Parallel(n_jobs=self.nproc, verbose=100)(delayed(run_func)(cmd_job) for cmd_job in tasks)

        # Convert the result to a list and return
        return list(ret)  # type: ignore

    def run(
        self,
        inputs: Optional[List[Dict[str, Union[str, RosettaScriptsVariableGroup]]]] = None,
        nstruct: Optional[int] = None,
    ) -> List[RosettaCmdTask]:
        """
        Runs the command either using MPI or locally based on configuration.

        :param inputs: List of input dictionaries.
        :param nstruct: Number of structures to generate.
        :return: List of RosettaCmdTask.
        """
        cmd = self.compose(opts=self.opts)
        if self.use_mpi and isinstance(self.run_node, MPI_node):
            if inputs is not None:
                warnings.warn(
                    MPI_IncompatibleInputWarning(
                        "Customized Inputs for MPI nodes will be flattened and passed to master node"
                    )
                )
            tasks = self.setup_tasks_mpi(base_cmd=cmd, inputs=inputs, nstruct=nstruct)
            return self.run_mpi(tasks)

        if isinstance(self.run_node, RosettaContainer):
            recomposed_cmd = self.run_node.recompose(cmd)
            print(f"Recomposed Command: \n{recomposed_cmd}")
            if self.run_node.mpi_available:
                tasks = self.setup_tasks_mpi(base_cmd=recomposed_cmd, inputs=inputs, nstruct=nstruct, dockerized=True)
                assert len(tasks) == 1, "Only one task should be returned from setup_tasks_mpi"
                return [self.run_node.run_single_task(task=tasks[0])]
            else:
                tasks = self.setup_tasks_local(base_cmd=recomposed_cmd, inputs=inputs, nstruct=nstruct)
                return self.run_local_docker(tasks)

        tasks = self.setup_tasks_local(cmd, inputs, nstruct)
        return self.run_local(tasks)

    def compose(self, **kwargs) -> List[str]:
        """
        Composes the full command based on the provided options.

        :return: The composed command as a list of strings.
        """
        assert isinstance(self.bin, RosettaBinary), "Rosetta binary must be a RosettaBinary object"

        cmd = [
            (
                self.bin.full_path
                if not isinstance(self.run_node, RosettaContainer)
                else f"/usr/local/bin/{self.bin.binary_name}"
            )
        ]
        if self.flags:
            for flag in self.flags:
                if not os.path.isfile(flag):
                    warnings.warn(IgnoreMissingFileWarning(f"Ignore Flag - {flag}"))
                    continue
                cmd.append(f"@{os.path.abspath(flag)}")

        if self.opts:
            cmd.extend([opt for opt in self.opts if isinstance(opt, str)])

            any_rosettascript_vars = [opt for opt in self.opts if isinstance(opt, RosettaScriptsVariableGroup)]
            if any(any_rosettascript_vars):
                for v in any_rosettascript_vars:
                    _v = v.aslonglist
                    print(f"Composing command with {_v}")
                    cmd.extend(_v)

        if self.output_dir:
            cmd.extend(
                [
                    "-out:path:pdb",
                    os.path.abspath(self.output_pdb_dir),
                    "-out:path:score",
                    os.path.abspath(self.output_scorefile_dir),
                ]
            )
        if not self.verbose:
            cmd.extend(["-mute", "all"])

        return cmd
