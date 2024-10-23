"""
Wsl Mounter
"""

import os
import subprocess
import warnings
from dataclasses import dataclass
from typing import Callable, List

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

    rosetta_bin_dir: str  # Path to Rosetta binaries in WSL
    user: str = f"{os.geteuid()}:{os.getegid()}"
    nproc: int = 4
    mpi_available: bool = False

    prohibit_mpi: bool = False  # to overide the mpi_available flag

    _mpirun_cache = None

    def __post_init__(self):

        if self.prohibit_mpi:
            self.mpi_available = False

    @property
    def is_root_user_wsl(self) -> bool:
        """
        Determine if the current user is a root user in WSL (Windows Subsystem for Linux).

        Returns:
            bool: True if the user is a root user in WSL, False otherwise.
        """
        try:
            # Check if the environment is WSL
            if "WSL_DISTRO_NAME" in os.environ:
                # Execute the 'wsl whoami' command
                result = subprocess.run(["wsl", "whoami"], capture_output=True, text=True, check=True)
                # Check if the output is 'root'
                return result.stdout.strip() == "root"
            else:
                return False
        except subprocess.CalledProcessError as e:
            # Log the error for debugging purposes
            print(f"An error occurred while checking if the user is a root user in WSL: {e}")
            return False
        except Exception as e:
            # Log any other unexpected exceptions
            print(f"An unexpected error occurred: {e}")
            return False

    @property
    def does_wsl_have_mpirun(self) -> bool:
        """
        Check if WSL has mpirun installed.

        Returns:
            bool: True if mpirun is installed, False otherwise.
        """
        if self._mpirun_cache is not None:
            return self._mpirun_cache

        try:
            # Execute the command to check if mpirun is installed
            result = subprocess.run(["wsl", "which", "mpirun"], capture_output=True, text=True, check=True)
            self._mpirun_cache = result.returncode == 0
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
        if not self.mpi_available or not self.does_wsl_have_mpirun:
            warnings.warn(RuntimeWarning("MPI is not available for this task."))
            return cmd

        # Recompose the command for MPI execution
        user = [] if not self.is_root_user_wsl else ["--allow-run-as-root"]
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

        return runner(mounted_task)
