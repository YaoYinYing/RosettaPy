"""
Wsl Mounter
"""

import subprocess
import warnings
from dataclasses import dataclass
from typing import Callable, List

from RosettaPy.rosetta_finder import RosettaBinary
from RosettaPy.utils.escape import print_diff
from RosettaPy.utils.task import RosettaCmdTask

from .utils import Mounter, mount


@dataclass
class WslMount(Mounter):
    """
    Represents a WSL mount point, inheriting from Mounter.
    This class is responsible for converting Windows paths to WSL paths and mounting them.
    """

    source: str  # The original Windows path
    target: str  # The converted WSL path

    @property
    def mounted(self) -> str:
        """
        Returns the mounted target path.

        Returns:
        - str: The target path.
        """
        return self.target

    @classmethod
    def from_path(cls, path_to_mount: str) -> "WslMount":
        """
        Converts a Windows path to the corresponding WSL path.

        Parameters:
        - path_to_mount: The original Windows path.

        Returns:
        - str: The converted WSL path.
        """
        # Use wslpath to convert the path
        try:
            wsl_path = subprocess.check_output(["wsl", "wslpath", "-a", path_to_mount]).decode().strip()
            # Print mount information
            print_diff(
                title="Mount:",
                labels={"source": path_to_mount, "target": wsl_path},
                title_color="yellow",
            )
            return WslMount(source=path_to_mount, target=wsl_path)
        except subprocess.CalledProcessError as e:
            # If the conversion fails, throw a runtime exception
            raise RuntimeError(f"Failed to convert Windows path to WSL path: {path_to_mount}") from e


@dataclass
class WslWrapper:
    """
    A class to execute Rosetta commands within the Windows Subsystem for Linux (WSL).
    """

    rosetta_bin: RosettaBinary
    distro: str
    user: str  # user in this distro

    nproc: int = 4

    prohibit_mpi: bool = False  # to overide the mpi_available flag

    # internal
    mpi_available: bool = False
    _mpirun_cache = None

    def __post_init__(self):

        if self.prohibit_mpi:
            self.mpi_available = False

        # get the default distro if not set
        all_installed_distro = self.run_wsl_command(["-l", "-q", "--all"]).strip()

        if self.distro not in all_installed_distro:
            raise RuntimeError(
                f"Failed to get default WSL distribution: {self.distro}\nAll distributions: \n{all_installed_distro}"
            )

    @staticmethod
    def run_wsl_command(cmd: List[str]) -> str:
        """
        Execute a WSL command and return the output.

        This function is used to execute a given WSL (Windows Subsystem for Linux) command and return the
        command's output.
        It is designed to run without an instance of a class (as indicated by the @staticmethod decorator).

        Parameters:
        cmd (List[str]): A list of strings representing the command and its arguments to be executed.

        Returns:
        str: Returns the output of the command as a string.

        Raises:
        RuntimeError: If an error occurs while executing the command, a RuntimeError is raised with a detailed
        error message.
        """

        # Execute the 'wsl' command
        with subprocess.Popen(
            ["wsl"] + cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, encoding="utf-8"
        ) as proc:
            stdout, stderr = proc.communicate()
            retcode = proc.wait()
            if retcode != 0:
                raise RuntimeError(f"Error running command: {cmd}: \nSTDOUT: {stdout}\nSTDERR: {stderr}\n")
            return stdout

    @property
    def has_mpirun(self) -> bool:
        """
        Check if WSL has mpirun installed.

        Returns:
            bool: True if mpirun is installed, False otherwise.
        """
        if self._mpirun_cache is not None:
            return self._mpirun_cache

        try:
            # Execute the command to check if mpirun is installed
            result = self.run_wsl_command(["-d", self.distro, "-u", self.user, "which", "mpirun"]).strip()
            self._mpirun_cache = result != ""
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            # Handle exceptions that may occur
            print(f"An error occurred while checking for mpirun: {e}")
            self._mpirun_cache = False

        return self._mpirun_cache

    def recompose(self, cmd: List[str]) -> List[str]:
        """
        Recompose the command for MPI execution if available.

        Parameters:
        - cmd: The command list.

        Returns:
        - List[str]: The recomposed command with MPI parameters, if applicable.
        """
        if not self.mpi_available or not self.has_mpirun:
            warnings.warn(RuntimeWarning("MPI is not available for this task."))
            return cmd

        # Recompose the command for MPI execution
        user = ["--allow-run-as-root"] if self.user == "root" else []
        return ["mpirun", "--use-hwthread-cpus", "-np", str(self.nproc)] + user + cmd

    def run_single_task(
        self, task: RosettaCmdTask, runner: Callable[[RosettaCmdTask], RosettaCmdTask]
    ) -> RosettaCmdTask:
        """
        Run the RosettaCmdTask in the WSL environment.

        Parameters:
        - task: The task to execute.

        Returns:
        - RosettaCmdTask: The original task for further use.
        """
        # Prepare the command for WSL
        mounted_task, _ = mount(input_task=task, mounter=WslMount)

        # Insert WSL specific run parameters to the task command list
        mounted_task.cmd = [
            "wsl",
            "-d",
            self.distro,
            "-u",
            self.user,
            "--cd",
            mounted_task.runtime_dir,
        ] + mounted_task.cmd

        return runner(mounted_task)
