"""
This module provides a class for running Rosetta command-line applications. It supports both local and containerized
"""

# pylint: disable=too-many-statements
# pylint: disable=too-many-instance-attributes

import copy
import os
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Union

import tree
from joblib_progress import joblib_progress

from .node import MpiNode, Native, NodeClassType, RosettaContainer, WslWrapper
from .node.mpi import MpiIncompatibleInputWarning

# internal imports
from .rosetta_finder import RosettaBinary, RosettaFinder
from .utils import (
    IgnoreMissingFileWarning,
    RosettaCmdTask,
    RosettaScriptsVariableGroup,
    expand_input_dict,
)
from .utils.tools import convert_crlf_to_lf


@dataclass
class Rosetta:
    """
    A wrapper class for running Rosetta command-line applications.

    Attributes:
        bin (RosettaBinary): The Rosetta binary to execute.
        flags (List[str]): List of flag files to include.
        opts (List[str]): List of command-line options.
        use_mpi (bool): Whether to use MPI for execution.
        run_node (MpiNode|RosettaContainer): Run node configuration.
    """

    bin: Union[RosettaBinary, str]

    flags: Optional[List[str]] = field(default_factory=list)
    opts: Optional[List[Union[str, RosettaScriptsVariableGroup]]] = field(default_factory=list)
    use_mpi: bool = False
    run_node: NodeClassType = field(default_factory=Native)

    job_id: str = "default"
    output_dir: str = ""
    save_all_together: bool = False

    isolation: bool = False
    verbose: bool = False

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
            if isinstance(self.run_node, RosettaContainer):
                # to container
                self.bin = RosettaBinary(dirname="/usr/local/bin/", binary_name=self.bin)
            elif isinstance(self.run_node, WslWrapper):
                self.bin = self.run_node.rosetta_bin
            else:
                # local direct runs
                self.bin = RosettaFinder().find_binary(self.bin)

        if isinstance(self.run_node, MpiNode):
            if self.bin.mode != "mpi":
                warnings.warn(
                    UserWarning(
                        "MPI nodes are configured but the binary doesn't support MPI mode. "
                        "This might occur in Dockerized Rosetta container. The job will run in non-MPI mode."
                    )
                )
            self.use_mpi = True
            return

        warnings.warn(
            UserWarning(
                "Using MPI binary in static build mode. This may impact performance compared to true MPI execution."
            )
        )
        self.use_mpi = False

    def setup_tasks_native(
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
        base_cmd_copy = copy.copy(base_cmd)

        now = datetime.now().strftime("%Y%m%d_%H%M%S")  # formatted date-time

        if nstruct and nstruct > 0:
            # if inputs are given and nstruct is specified, flatten and pass inputs to all tasks
            if inputs:
                base_cmd_copy.extend(tree.flatten([expand_input_dict(input_dict) for input_dict in inputs]))

            cmd_jobs = [
                RosettaCmdTask(
                    cmd=base_cmd_copy
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
                    cmd=base_cmd_copy + expand_input_dict(input_arg),
                    task_label=f"task-{self.job_id}-no-{i}" if self.isolation else None,
                    base_dir=os.path.join(self.output_dir, f"{now}-{self.job_id}-runtimes"),
                )
                for i, input_arg in enumerate(inputs)
            ]
            warnings.warn(UserWarning(f"Processing {len(cmd_jobs)} commands"))
            return cmd_jobs

        cmd_jobs = [RosettaCmdTask(cmd=base_cmd_copy)]

        warnings.warn(UserWarning("No inputs are given. Running single job."))
        return cmd_jobs

    def setup_tasks_with_node(
        self,
        base_cmd: List[str],
        inputs: Optional[List[Dict[str, Union[str, RosettaScriptsVariableGroup]]]] = None,
        nstruct: Optional[int] = None,
    ) -> List[RosettaCmdTask]:
        """
        Setup a command with run node.

        :param cmd: Base command to be executed.
        :param inputs: List of input dictionaries.
        :param nstruct: Number of structures to generate.
        :return: List of RosettaCmdTask
        """
        if not isinstance(self.run_node, (MpiNode, RosettaContainer, WslWrapper)):
            raise RuntimeError(
                f"Invalid run_node type: {type(self.run_node)}. "
                "Expected an initialized instance of MpiNode, RosettaContainer, or WslWrapper."
            )

        # make a copy command list
        base_cmd_copy = copy.copy(base_cmd)
        # if inputs are given, flatten and attach them to the command
        if inputs:
            for _, input_dict in enumerate(inputs):
                base_cmd_copy.extend(expand_input_dict(input_dict))

        # if nstruct is given, attach it to the command
        if nstruct:
            base_cmd_copy.extend(["-nstruct", str(nstruct)])

        with self.run_node.apply(base_cmd_copy) as updated_cmd:
            if self.isolation:
                warnings.warn(RuntimeWarning("Ignoring isolated mode for MPI run."))
            return [RosettaCmdTask(cmd=updated_cmd)]

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
        cmd = self.compose()

        if self.use_mpi and isinstance(self.run_node, (RosettaContainer, WslWrapper, MpiNode)):
            if inputs:
                warnings.warn(
                    MpiIncompatibleInputWarning(
                        "Customized inputs for MPI nodes will be flattened and passed to the master node. "
                        "This may affect how inputs are distributed across worker nodes. "
                        "Consider restructuring your inputs if node-specific customization is required."
                    )
                )

            tasks = self.setup_tasks_with_node(base_cmd=cmd, inputs=inputs, nstruct=nstruct)
            return self.run_node.run(tasks)

        tasks = self.setup_tasks_native(cmd, inputs, nstruct)
        with joblib_progress(f"Processing {self.job_id} via {self.run_node.__class__.__name__}...", total=len(tasks)):
            return self.run_node.run(tasks)

    @property
    def _rosetta_bin_path(self) -> str:
        """
        Selects the appropriate Rosetta binary path based on the current runtime environment.

        This method first checks if `self.bin` is an instance of `RosettaBinary`. If not, it raises a runtime error.
        Then, depending on the type of `self.run_node`, it determines the binary path to return:
        - If `self.run_node` is an instance of `RosettaContainer`, it returns a fixed path within the container.
        - If `self.run_node` is an instance of `WslWrapper` or any other case, it returns the full path of the binary.

        :return: The path to the Rosetta binary.
        :rtype: str
        """
        # Check if self.bin is an instance of RosettaBinary
        if not isinstance(self.bin, RosettaBinary):
            raise RuntimeError(
                f"Invalid binary type: {type(self.bin)}. Expected RosettaBinary object. "
                "Ensure the binary is properly initialized through RosettaFinder or direct instantiation."
            )

        # Determine the binary path based on the type of run_node
        if isinstance(self.run_node, RosettaContainer):
            return f"/usr/local/bin/{self.bin.binary_name}"
        if isinstance(self.run_node, WslWrapper):
            return self.bin.full_path

        return self.bin.full_path

    def compose(self) -> List[str]:
        """
        Composes the full command based on the provided options.

        :return: The composed command as a list of strings.
        """

        cmd = [self._rosetta_bin_path]
        if self.flags:
            for flag in self.flags:
                if not os.path.isfile(flag):
                    warnings.warn(IgnoreMissingFileWarning(f"Ignoring missing flag file: {os.path.abspath(flag)}"))
                    continue
                with convert_crlf_to_lf(os.path.abspath(flag)) as new_flag:
                    cmd.append(f"@{new_flag}")

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
