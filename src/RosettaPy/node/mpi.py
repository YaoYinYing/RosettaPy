"""
MPI module for run Rosetta (extra=mpi) on local machine.
"""

import contextlib
import copy
import os
import platform
import random
import shutil
import subprocess
import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional

from RosettaPy.utils.task import RosettaCmdTask, _non_isolated_execute


class MpiIncompatibleInputWarning(RuntimeWarning):
    """
    Incompatible Input matrix against MPI execution.
    """


def which_scontrol() -> str:
    """
    Find the path to the scontrol executable.

    Returns:
    - str: The path to the scontrol executable.
    """
    scontrol_bin = shutil.which("scontrol")
    if not scontrol_bin:
        raise RuntimeError("scontrol not found")
    return scontrol_bin


def get_nodes() -> List[str]:
    """
    Retrieve the list of nodes allocated for a SLURM job.

    This function obtains the node list by calling the `scontrol` command,
    specifically using the `SLURM_JOB_NODELIST` environment variable to get the nodes.
    It returns the names of the nodes as a string, with each node name separated by a newline.
    """
    # Determine the path of the scontrol command
    this_scontrol = which_scontrol()

    # Validate and sanitize the SLURM_JOB_NODELIST environment variable
    slurm_job_nodelist = os.getenv("SLURM_JOB_NODELIST")
    if not slurm_job_nodelist:
        raise ValueError("SLURM_JOB_NODELIST environment variable is not set")

    # Use shlex.split to safely split the command into a list of arguments
    command = [this_scontrol, "show", "hostnames", slurm_job_nodelist]

    try:
        # Execute the command and get the list of node names
        nodes = subprocess.check_output(command).decode().strip().split("\n")
    except subprocess.CalledProcessError as e:
        # If the command execution fails, raise a RuntimeError with the error message
        raise RuntimeError(f"Failed to get nodes: {e}") from e

    return nodes


@dataclass
class MpiNode:
    """
    MpiNode class for configuring and running MPI tasks.

    Attributes:
        nproc (int): Total number of processors.
        node_matrix (Optional[Dict[str, int]]): Mapping of node IDs to the number of processors.
    """

    nproc: int = 0
    mpi_executable: str = ""
    node_matrix: Optional[Dict[str, int]] = None  # Node ID: nproc

    # internal variables
    node_file = f"nodefile_{random.randint(1, 9_999_999_999)}.txt"
    user = os.getuid() if platform.system() != "Windows" else None

    mpi_available = True

    def get_mpiexecutable(self):
        """
        Attempts to find and set the path to the MPI executable.

        This method first tries to get the MPI executable path from the MPIEXEC environment variable.
        If the environment variable is not set or the path is invalid, it will try to find common MPI
        executables in the system's PATH.
        If no supported MPI executable can be found, it raises a RuntimeError.
        """
        if self.mpi_executable and os.path.isfile(self.mpi_executable):
            return

        # Try to get the MPI executable path from the MPIEXEC environment variable
        mpi_exec = os.environ.get("MPIEXEC")
        if mpi_exec and (which_mpi_exec := shutil.which(mpi_exec)):
            # If the path exists, set the self.mpi_executable attribute and print the path
            self.mpi_executable = which_mpi_exec
            print(f"Using MPI executable from MPIEXEC: {self.mpi_executable}")
            return

        # Attempt to locate a supported MPI executable
        for mpi_exec in ["mpirun", "mpiexec", "mpiexec.hydra", "orterun", "prun"]:
            # Set the found MPI executable path to the self.mpi_executable attribute
            if (mpi_executable := shutil.which(mpi_exec)) is not None:
                self.mpi_executable = mpi_executable
                # If a supported MPI executable is found, set the path and exit the loop
                return

        # If no supported MPI executable is found, raise an exception
        raise RuntimeError(
            "No supported MPI executable found in PATH. Searched: "
            f"{', '.join(['mpirun', 'mpiexec', 'mpiexec.hydra', 'orterun', 'prun'])}"
        )

    def __post_init__(self):
        """
        Post-initialization method for additional setup after instance initialization.

        This method performs several critical tasks:
        1. Checks the operating system, and if it's Windows, raises an exception as Windows is not supported.
        2. Attempts to locate a supported MPI executable in the system PATH.
        3. If `node_matrix` is a dictionary, writes the node information to `node_file`.
        4. Calculates and updates the `nproc` attribute based on `node_matrix`.
        """

        # Check if the operating system is Windows, and if so, raise a runtime error
        if platform.system() == "Windows":
            raise RuntimeError("Windows is not supported for mpi runs.")

        self.get_mpiexecutable()

        # If `node_matrix` is not a dictionary, no further action is required
        if not isinstance(self.node_matrix, dict):
            return

        # Write node information to `node_file`
        try:
            with open(self.node_file, "w", encoding="utf-8") as f:
                for node, nproc in self.node_matrix.items():
                    f.write(f"{node} slots={nproc}\n")
        except OSError as e:
            raise RuntimeError(f"Failed to write node file: {e}") from e

        # Update `nproc` attribute based on `node_matrix`
        self.nproc = sum(self.node_matrix.values())

    @property
    def local(self) -> List[str]:
        """
        Property to generate a list of arguments for local execution.

        Returns:
            List[str]: Arguments for local execution.
        """
        return [self.mpi_executable, "--use-hwthread-cpus", "-np", str(self.nproc)]

    @property
    def host_file(self) -> List[str]:
        """
        Property to generate a list of arguments for host file execution.

        Returns:
            List[str]: Arguments for host file execution.
        """
        return [self.mpi_executable, "--hostfile", self.node_file]

    @contextlib.contextmanager
    def apply(self, cmd: List[str]):
        """
        Context manager to apply MPI configurations to a command.

        Args:
            cmd (List[str]): Command to be executed.

        Yields:
            List[str]: Modified command with MPI configurations.
        """
        cmd_copy = copy.copy(cmd)
        m = self.local if not self.node_matrix else self.host_file
        if self.user == 0:
            m.append("--allow-run-as-root")
            warnings.warn(UserWarning("Running Rosetta with MPI as Root User"))

        yield m + cmd_copy

        if os.path.exists(self.node_file):
            os.remove(self.node_file)

    @classmethod
    def from_slurm(cls) -> "MpiNode":
        """
        Class method to create an MpiNode instance from Slurm environment variables.

        Returns:
            MpiNode: Instance configured using Slurm environment variables.
        """
        try:
            nodes = get_nodes()
        except RuntimeError as e:
            raise RuntimeError(f"Expected scontrol not found. {e}") from e
        except KeyError as e:
            raise RuntimeError(f"Environment variable {e} not set") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get node list: {e.output}") from e

        slurm_cpus_per_task = os.environ.get("SLURM_CPUS_PER_TASK", "1")
        slurm_ntasks_per_node = os.environ.get("SLURM_NTASKS_PER_NODE", "1")

        if int(slurm_cpus_per_task) < 1:
            print(f"Fixing $SLURM_CPUS_PER_TASK from {slurm_cpus_per_task} to 1.")
            slurm_cpus_per_task = "1"

        if int(slurm_ntasks_per_node) < 1:
            print(f"Fixing $SLURM_NTASKS_PER_NODE from {slurm_ntasks_per_node} to 1.")
            slurm_ntasks_per_node = "1"

        node_dict = {i: int(slurm_ntasks_per_node) * int(slurm_cpus_per_task) for i in nodes}

        total_nproc = sum(node_dict.values())
        return cls(nproc=total_nproc, node_matrix=node_dict)

    @staticmethod
    def run(
        tasks: List[RosettaCmdTask],
    ) -> List[RosettaCmdTask]:
        """
        Execute tasks using MPI.

        This method is designed to execute a given list of tasks using MPI (Message Passing Interface),
        which is a programming model for distributed memory systems that allows developers to write
        highly scalable parallel applications.

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
        ret = _non_isolated_execute(tasks[0])

        # Return the result as a list
        return [ret]
