import contextlib
import copy
from dataclasses import dataclass
import os
import random
import shutil
import subprocess
from typing import Dict, List, Optional
import warnings


class MPI_IncompatibleInputWarning(RuntimeWarning): ...


@dataclass
class MPI_node:
    nproc: int = 0
    node_matrix: Optional[Dict[str, int]] = None  # Node ID: nproc
    node_file = f"nodefile_{random.randint(1,9_999_999_999)}.txt"

    user = os.getuid()

    def __post_init__(self):

        for mpi_exec in ["mpirun", ...]:
            self.mpi_excutable = shutil.which(mpi_exec)
            if self.mpi_excutable is not None:
                break

        if not isinstance(self.node_matrix, dict):
            return

        with open(self.node_file, "w") as f:
            for node, nproc in self.node_matrix.items():
                f.write(f"{node} slots={nproc}\n")
        self.nproc = sum(self.node_matrix.values())  # fix nproc to real node matrix

    @property
    def local(self) -> List[str]:
        return [self.mpi_excutable, "--use-hwthread-cpus", "-np", str(self.nproc)]

    @property
    def host_file(self) -> List[str]:
        return [self.mpi_excutable, "--hostfile", self.node_file]

    @contextlib.contextmanager
    def apply(self, cmd: List[str]):
        cmd_copy = copy.copy(cmd)
        m = self.local if not self.node_matrix else self.host_file
        if self.user == 0:
            m.append("--allow-run-as-root")
            warnings.warn(UserWarning("Running Rosetta with MPI as Root User"))

        yield m + cmd_copy

        if os.path.exists(self.node_file):
            os.remove(self.node_file)

    @classmethod
    def from_slurm(cls) -> "MPI_node":
        try:
            nodes = (
                subprocess.check_output(["scontrol", "show", "hostnames", os.environ["SLURM_JOB_NODELIST"]])
                .decode()
                .strip()
                .split("\n")
            )
        except KeyError as e:
            raise RuntimeError(f"Environment variable {e} not set") from None
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get node list: {e.output}") from None

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
