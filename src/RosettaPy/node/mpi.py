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


class MpiIncompatibleInputWarning(RuntimeWarning):
    """
    Incompatible Input matrix against MPI execution.
    """


@dataclass
class MpiNode:
    """
    MpiNode class for configuring and running MPI tasks.

    Attributes:
        nproc (int): Total number of processors.
        node_matrix (Optional[Dict[str, int]]): Mapping of node IDs to the number of processors.
    """

    nproc: int = 0
    node_matrix: Optional[Dict[str, int]] = None  # Node ID: nproc
    node_file = f"nodefile_{random.randint(1, 9_999_999_999)}.txt"

    user = os.getuid() if platform.system() != "Windows" else None

    def __post_init__(self):
        """
        Post-initialization method to configure MPI executable and node file.
        """
        for mpi_exec in ["mpirun", ...]:
            self.mpi_excutable = shutil.which(mpi_exec)
            if self.mpi_excutable is not None:
                break

        if not isinstance(self.node_matrix, dict):
            return

        with open(self.node_file, "w", encoding="utf-8") as f:
            for node, nproc in self.node_matrix.items():
                f.write(f"{node} slots={nproc}\n")
        # fix nproc to real node matrix
        self.nproc = sum(self.node_matrix.values())

    @property
    def local(self) -> List[str]:
        """
        Property to generate a list of arguments for local execution.

        Returns:
            List[str]: Arguments for local execution.
        """
        return [self.mpi_excutable, "--use-hwthread-cpus", "-np", str(self.nproc)]

    @property
    def host_file(self) -> List[str]:
        """
        Property to generate a list of arguments for host file execution.

        Returns:
            List[str]: Arguments for host file execution.
        """
        return [self.mpi_excutable, "--hostfile", self.node_file]

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
            which_scontrol = shutil.which("scontrol")
            if which_scontrol is None:
                raise RuntimeError("scontrol not found")
            nodes = (
                subprocess.check_output([which_scontrol, "show", "hostnames", os.environ["SLURM_JOB_NODELIST"]])
                .decode()
                .strip()
                .split("\n")
            )
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
        return cls(total_nproc, node_dict)
