import copy
from dataclasses import dataclass, field
import shutil
import time
from typing import Dict, List, Optional, Union
import subprocess
import os
import random
import contextlib
import warnings

import pandas as pd

# internal imports
from .rosetta_finder import RosettaBinary, RosettaFinder


class MPI_IncompatibleInputWarning(RuntimeWarning): ...


class RosettaScriptVariableWarning(RuntimeWarning): ...


class RosettaScriptVariableNotExistWarning(RosettaScriptVariableWarning): ...


@dataclass(frozen=True)
class RosettaScriptsVariable:
    k: str
    v: str

    @property
    def aslist(self) -> List[str]:
        return [
            "-parser:script_vars",
            f"{self.k}={self.v}",
        ]


@dataclass(frozen=True)
class RosettaScriptsVariableGroup:
    variables: List[RosettaScriptsVariable]

    @property
    def empty(self):
        return len(self.variables) == 0

    @property
    def aslonglist(self) -> List[str]:
        return [i for v in self.variables for i in v.aslist]

    @property
    def asdict(self) -> Dict[str, str]:
        return {rsv.k: rsv.v for rsv in self.variables}

    @classmethod
    def from_dict(cls, var_pair: Dict[str, str]) -> "RosettaScriptsVariableGroup":
        variables = [RosettaScriptsVariable(k=k, v=str(v)) for k, v in var_pair.items()]
        instance = cls(variables)
        if instance.empty:
            raise ValueError()
        return instance

    def apply_to_xml_content(self, xml_content: str):
        xml_content_copy = copy.deepcopy(xml_content)
        for k, v in self.asdict:
            if f"%%{k}%%" not in xml_content_copy:
                warnings.warn(RosettaScriptVariableNotExistWarning(f"Variable {k} not in Rosetta Script content."))
                continue
            xml_content_copy = xml_content_copy.replace(f"%%{k}%%", v)

        return xml_content_copy


@contextlib.contextmanager
def timing(msg: str):
    print("Started %s", msg)
    tic = time.time()
    yield
    toc = time.time()
    print("Finished %s in %.3f seconds", msg, toc - tic)


@dataclass
class MPI_node:
    nproc: int = 0
    node_matrix: Optional[Dict[str, int]] = None  # Node ID: nproc
    node_file = f"nodefile_{random.randint(1,9_999_999_999)}.txt"

    def __post_init__(self):

        for mpi_exec in ["mpirun", "mpicc", ...]:
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

        yield m + cmd_copy

        if os.path.isfile(self.node_file):
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
    mpi_node: Optional[MPI_node] = None

    job_id: str = "default"
    output_dir: str = ""
    save_all_together: bool = False

    @staticmethod
    def expand_input_dict(d: Dict[str, Union[str, RosettaScriptsVariableGroup]]) -> List[str]:

        l = []
        for k, v in d.items():
            if not isinstance(v, RosettaScriptsVariableGroup):
                l.extend([k, v])
            else:
                l.extend(v.aslonglist)
        return l

    @property
    def output_pdb_dir(self) -> str:
        if not self.output_dir:
            raise ValueError("Output directory not set.")
        p = os.path.join(self.output_dir, self.job_id, "pdb" if self.save_all_together else "all")
        os.makedirs(p, exist_ok=True)
        return p

    @property
    def output_scorefile_dir(self) -> str:
        if not self.output_dir:
            raise ValueError("Output directory not set.")
        p = os.path.join(self.output_dir, self.job_id, "scorefile" if self.save_all_together else "all")
        os.makedirs(p, exist_ok=True)
        return p

    def __post_init__(self):
        if self.flags is None:
            self.flags = []
        if self.opts is None:
            self.opts = []

        if isinstance(self.bin, str):
            self.bin = RosettaFinder().find_binary(self.bin)

        if self.mpi_node is not None:
            if self.bin.mode != "mpi":
                raise ValueError("MPI nodes are given yet not supported.")

            self.use_mpi = True
            return

        else:
            warnings.warn(UserWarning("Using MPI binary as static build."))
            self.use_mpi = False

    @staticmethod
    def execute(cmd: List[str]) -> None:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
        )

        print(f'Lauching command: {" ".join(cmd)}')
        stdout, stderr = process.communicate()
        retcode = process.wait()

        if retcode:
            print(f"Command failed with return code {retcode}")
            print(stdout)
            print(stderr)
            raise RuntimeError(f"Command failed with return code {retcode}")

    def run_mpi(
        self,
        cmd: List[str],
        nstruct: Optional[int] = None,
    ) -> List[None]:
        assert isinstance(self.mpi_node, MPI_node), "MPI node instance is not initialized."

        if nstruct:
            ret = cmd.extend(["-nstruct", str(nstruct)])
        with self.mpi_node.apply(cmd) as updated_cmd:
            ret = self.execute(updated_cmd)

        return [ret]

    def run_local(
        self,
        cmd,
        inputs: Optional[List[Dict[str, Union[str, RosettaScriptsVariableGroup]]]] = None,
        nstruct: Optional[int] = None,
    ) -> List[None]:
        from joblib import Parallel, delayed

        _cmd = copy.copy(cmd)

        if nstruct and nstruct > 0:

            if inputs:
                assert len(inputs) == 1, "For runs with nstruct, use one dictionary in input list"
                input_args = self.expand_input_dict(inputs[0])
                print(f"Additional input args is passed: {input_args}")
            else:
                input_args = []

            cmd_jobs = [_cmd + input_args + ["-suffix", f"_{i:05}", "-no_nstruct_label"] for i in range(1, nstruct + 1)]
            warnings.warn(UserWarning(f"Processing {len(cmd_jobs)} commands on {nstruct} decoys."))
        elif inputs:
            cmd_jobs = [_cmd + self.expand_input_dict(input_arg) for input_arg in inputs]
            warnings.warn(UserWarning(f"Processing {len(cmd_jobs)} commands"))
        else:
            cmd_jobs = [_cmd]

            warnings.warn(UserWarning("No inputs are given. Running single job."))

        ret: List = Parallel(n_jobs=self.nproc)(delayed(self.execute)(cmd_job) for cmd_job in cmd_jobs)  # type: ignore
        # warnings.warn(UserWarning(str(ret)))
        return list(ret)

    def run(
        self,
        inputs: Optional[List[Dict[str, Union[str, RosettaScriptsVariableGroup]]]] = None,
        nstruct: Optional[int] = None,
    ) -> List[None]:
        cmd = self.compose(opts=self.opts)
        if self.use_mpi and isinstance(self.mpi_node, MPI_node):
            if inputs is not None:
                warnings.warn(MPI_IncompatibleInputWarning("Ignore Customized Input for MPI nodes."))
            return self.run_mpi(cmd, nstruct)

        return self.run_local(cmd, inputs, nstruct)

    def compose(self, **kwargs) -> List[str]:
        assert isinstance(self.bin, RosettaBinary), "Rosetta binary must be a RosettaBinary object"

        cmd = [
            self.bin.full_path,
        ]
        if self.flags:
            for flag in self.flags:
                if not os.path.isfile(flag):
                    continue
                cmd.append(f"@{flag}")

        if self.opts:
            cmd.extend([opt for opt in self.opts if isinstance(opt, str)])

            any_rosettascript_vars = [opt for opt in self.opts if isinstance(opt, RosettaScriptsVariableGroup)]
            if any(any_rosettascript_vars):
                for v in any_rosettascript_vars:
                    _v = v.aslonglist
                    print(f"Composing command with {_v}")
                    cmd.extend(_v)

        if self.output_dir:
            cmd.extend(["-out:path:pdb", self.output_pdb_dir, "-out:path:score", self.output_scorefile_dir])

        return cmd


@dataclass
class RosettaEnergyUnitAnalyser:
    score_file: str
    score_term: str = "total_score"

    @staticmethod
    def scorefile2df(score_file: str) -> pd.DataFrame:
        df = pd.read_fwf(score_file, skiprows=1)

        if "SCORE:" in df.columns:
            df.drop("SCORE:", axis=1, inplace=True)

        return df

    def __post_init__(self):
        if os.path.isfile(self.score_file):
            self.df = self.scorefile2df(self.score_file)
        elif os.path.isdir(self.score_file):
            dfs = [
                self.scorefile2df(os.path.join(self.score_file, f))
                for f in os.listdir(self.score_file)
                if f.endswith(".sc")
            ]
            warnings.warn(UserWarning(f"Concatenate {len(dfs)} score files"))
            self.df = pd.concat(dfs, axis=0, ignore_index=True)
        else:
            raise FileNotFoundError(f"Score file {self.score_file} not found.")

        if not self.score_term in self.df.columns:
            raise ValueError(f'Score term "{self.score_term}" not found in score file.')

    @property
    def best_decoy(self) -> Dict[str, Union[str, float]]:
        if self.df.empty:
            return {}
        min_idx = self.df[self.score_term].idxmin()
        min_record = self.df[self.df.index == min_idx]

        return {
            "score": float(min_record[self.score_term].iloc[0]),
            "decoy": str(min_record["description"].iloc[0]),
        }