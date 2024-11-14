"""
Container module for run Rosetta via docker.
"""

# pylint: disable=too-many-statements
# pylint: disable=no-member


import contextlib
import functools
import os
import platform
import signal
import warnings
from dataclasses import dataclass
from typing import List, Optional

import docker
from docker import types
from joblib import Parallel, delayed

from RosettaPy.node.utils import Mounter, mount

from ..utils.escape import print_diff, render
from ..utils.task import RosettaCmdTask, execute
from ..utils.tools import squeeze


@dataclass
class RosettaPyMount(Mounter):
    """
    Mount point for docker container.
    """

    name: str
    source: str
    target: str
    mounted: str
    readonly: bool = False

    @property
    def mount(self) -> types.Mount:
        """
        Creates and returns a `types.Mount` object for configuring a mount point.

        Parameters:
        - self: The instance of the class containing the method.

        Returns:
        - A `types.Mount` object with the specified target, source, read-only status, and type.
        """
        # Create a Mount object with the specified attributes
        return types.Mount(
            target=self.target,
            source=self.source,
            read_only=self.readonly,
            type="bind",
        )

    @classmethod
    def from_path(
        cls,
        path_to_mount: str,
    ) -> "RosettaPyMount":
        """
        Create a Mount instance from the given path.

        This method first normalizes the given path to ensure consistent formatting across different operating systems.
        It then retrieves the mounted name using the normalized path and finally creates and returns a Mount instance.

        Parameters:
        - path_to_mount (str): The path that needs to be mounted.

        Returns:
        - Mount: A Mount instance created based on the given path.
        """

        # Normalize the given mount path to ensure consistent formatting
        normalized_path = os.path.normpath(path_to_mount)

        # Retrieve the mounted name using the normalized path
        mounted_name = cls.get_mounted_name(normalized_path)

        # Create and return a Mount instance
        return cls._create_mount(mounted_name, normalized_path)

    @classmethod
    def _create_mount(cls, mount_name: str, path: str, read_only=False) -> "RosettaPyMount":
        """
        Create a mount point for each file and directory used by the model.

        Parameters:
        - mount_name (str): The name of the mount point.
        - path (str): The path to the file or directory.
        - read_only (bool): Whether the mount point is read-only. Defaults to False.

        Returns:
        - RosettaPyMount: The created mount point object.
        """
        # Get the absolute path and the target mount path
        path = os.path.abspath(path)
        # skipcq: BAN-B108
        target_path = os.path.join("/tmp/", mount_name)

        # Determine the source path and mounted path based on whether the path points to a directory or a file
        if os.path.isdir(path):
            source_path = path
            mounted_path = target_path
        else:
            source_path = os.path.dirname(path)
            mounted_path = os.path.join(target_path, os.path.basename(path))

        # Ensure the source path exists
        if not os.path.exists(source_path):
            os.makedirs(source_path)

        # Print mount information
        print_diff(
            title="Mount:",
            labels={"source": source_path, "target": target_path},
            title_color="yellow",
        )

        # Create and return the mount object and mounted path

        return cls(
            name=mount_name,
            source=str(source_path),
            target=str(target_path).replace("\\", "/"),
            mounted=str(mounted_path).replace("\\", "/"),
            readonly=read_only,
        )

    @staticmethod
    def get_mounted_name(path: str) -> str:
        """
        Returns a formatted name suitable for mounting based on the given path.

        This method first validates the provided path to ensure it exists in the file system,
        raising an exception if it does not.

        It then obtains the absolute path and determines whether to use the parent directory or
        the path itself based on whether the path is a file or a directory.

        Finally, it formats the path by replacing slashes (/) with hyphens (-) to create
        a safe name suitable for mounting.

        :param path: str The input file or directory path.
        :return: str A formatted name suitable for mounting.
        """

        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} does not exist.")

        path = os.path.abspath(path)

        if os.path.isfile(path):
            dirname = os.path.dirname(path)
        else:
            dirname = path

        return dirname.replace("/", "-").replace("\\", "-").replace(":", "-").strip("-")

    @classmethod
    def squeeze(cls, mounts: List[types.Mount]) -> List[types.Mount]:
        """
        Removes duplicate `Mount` objects from a list without changing the order of the original list.

        This method does not use a set to avoid hashing issues since `types.Mount` objects are not hashable.
        Instead, it iterates through the list, adding items to a new list only if they are not already present,
        thereby removing duplicates while preserving the original order.

        Parameters:
            mounts (List[types.Mount]): A list of `Mount` objects that may contain duplicates.

        Returns:
            List[types.Mount]: A list of `Mount` objects with duplicates removed.
        """
        # Get squeezed mount list
        mount_set = squeeze(mounts)

        # Get the length of the list before and after duplicate removal
        # If the lengths are different, it means duplicates were removed
        if (len_before := len(mounts)) != (len_after := len(mount_set)):
            # Print the difference in length before and after removing duplicates
            print_diff(
                "Duplicate mounts",
                {
                    "Before": len_before,
                    "After": len_after,
                },
            )
            # Warn the user about duplicate `Mount` objects being removed
            warnings.warn(RuntimeWarning(f"Duplicate mounts is removed: {len_before - len_after}"))

        # Return the list of `Mount` objects with duplicates removed
        return mount_set


@dataclass
class RosettaContainer:
    """
    A class to represent a docker container for Rosetta.
    """

    image: str = "rosettacommons/rosetta:mpi"
    prohibit_mpi: bool = False  # to overide the mpi_available flag
    mpi_available: bool = False
    nproc: int = 0

    # internal variables

    user: Optional[str] = f"{os.geteuid()}:{os.getegid()}" if platform.system() != "Windows" else None

    def __post_init__(self):
        # Automatically set MPI availability based on the image name
        if self.image.endswith("mpi"):
            self.mpi_available = True
        # Set a default number of processors if not specified
        if self.nproc <= 0:
            self.nproc = 4

        # Respect the MPI prohibition flag
        if self.prohibit_mpi:
            self.mpi_available = False

    @contextlib.contextmanager
    def apply(self, cmd: List[str]):
        """
        Context manager to apply MPI configurations to a command.

        This function checks if MPI is available. If not, it issues a warning and returns the original command.
        If MPI is available, it recomposes the command to include MPI execution parameters.

        Parameters:
        - cmd: List[str], the original command list to be recomposed

        Returns:
        - List[str], the recomposed command list including MPI parameters if necessary
        """
        # Check if MPI is available, if not, issue a warning and return the original command
        if not self.mpi_available:
            warnings.warn(RuntimeWarning("This container has static build of Rosetta. Nothing has to be recomposed."))
            yield cmd
        else:
            # Recompose and return the new command list including MPI parameters
            yield ["mpirun", "--use-hwthread-cpus", "-np", str(self.nproc), "--allow-run-as-root"] + cmd

    def run_single_task(self, task: RosettaCmdTask) -> RosettaCmdTask:
        """
        Runs a task within a Docker container.

        This method is responsible for mounting the necessary files and directories
        into the Docker container and executing the task. It handles the creation
        of the Docker container, running the task command, and streaming the logs.
        Additionally, it registers a signal handler to ensure that the running
        container is stopped when a SIGINT (e.g., Ctrl+C) is received.

        Parameters:
        - task: A `RosettaCmdTask` object representing the task to be executed in the Docker container.

        Returns:
        - The original task object for further processing or inspection.
        """

        # Mount the necessary files and directories, then run the task
        mounted_task, mounts = mount(input_task=task, mounter=RosettaPyMount)
        client = docker.from_env()

        print(f"{render('Mounted with: ', 'green-bold-negative')} " f"{render(mounted_task.cmd, 'bold-green')}")
        print(f"{render('Run at ->', 'yellow-bold-negative')} " f"{render(mounted_task.runtime_dir, 'bold-yellow')}")

        container = client.containers.run(
            image=self.image,
            command=mounted_task.cmd,
            remove=True,
            detach=True,
            mounts=mounts,
            user=self.user,
            stdout=True,
            stderr=True,
            working_dir=mounted_task.runtime_dir,
            platform="linux/amd64",
        )

        # Register a signal handler to stop the running container on SIGINT (e.g., Ctrl+C)
        signal.signal(signal.SIGINT, lambda unused_sig, unused_frame: container.kill())

        for line in container.logs(stream=True):
            print(line.strip().decode("utf-8"))

        return task

    def run(self, tasks: List[RosettaCmdTask]) -> List[RosettaCmdTask]:
        """
        Execute multiple tasks in parallel within Docker containers.
        """

        run_func = functools.partial(execute, func=self.run_single_task)

        # Execute tasks in parallel using multiple jobs
        ret = Parallel(n_jobs=self.nproc, verbose=100)(delayed(run_func)(cmd_job) for cmd_job in tasks)

        # Convert the result to a list and return
        return list(ret)  # type: ignore
