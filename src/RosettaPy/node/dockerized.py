"""
Container module for run Rosetta via docker.
"""

# pylint: disable=too-many-statements
# pylint: disable=no-member


import os
import platform
import signal
import warnings
from dataclasses import dataclass
from typing import List, Optional, Tuple

import docker
from docker import types

from ..utils.escape import print_diff, render
from ..utils.task import RosettaCmdTask


@dataclass
class RosettaPyMount:
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

        mount = cls(
            name=mount_name,
            source=str(source_path),
            target=str(target_path).replace("\\", "/"),
            mounted=str(mounted_path),
            readonly=read_only,
        )

        return mount

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
        # Initialize an empty list to store unique `Mount` objects
        mount_set = []
        # will not use Set here bcs `types.Mount` is not hashable
        for mount in mounts:
            # Check if the current `Mount` object is already in `mount_set`
            if mount in mount_set:
                # If so, skip it to remove duplicates
                continue
            # If not, add it to `mount_set`
            mount_set.append(mount)

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


def get_quoted(text: str) -> str:
    """
    Ensures the input string is enclosed in single quotes.

    If the input string does not start with a single quote, one is added at the beginning.
    If the input string does not end with a single quote, one is added at the end.

    Parameters:
    text (str): The string to be processed.

    Returns:
    str: The string enclosed in single quotes.
    """

    text = text.replace("\n", "")
    # Ensure the result starts and ends with single quotes
    if not text.startswith("'"):
        text = "'" + text

    if not text.endswith("'"):
        text += "'"

    return text


@dataclass
class RosettaContainer:
    """
    A class to represent a docker container for Rosetta.
    """

    image: str = "rosettacommons/rosetta:mpi"
    mpi_available: bool = False
    user: Optional[str] = f"{os.geteuid()}:{os.getegid()}" if platform.system() != "Windows" else None
    nproc: int = 0
    prohibit_mpi: bool = False  # to overide the mpi_available flag

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

    @staticmethod
    def _process_xml_fragment(script_vars_v: str) -> Tuple[str, List[RosettaPyMount]]:
        """
        Process an XML fragment to handle file and directory paths.

        This function takes a string containing paths potentially mixed with other text,
        identifies the paths, and creates RosettaPyMount objects for them. It also
        reconstructs the input string with the mounted paths, preserving the original
        structure as much as possible.

        Parameters:
        - script_vars_v (str): A string containing paths mixed with other text.

        Returns:
        - Tuple[str, List[RosettaPyMount]]: A tuple containing the reconstructed string
        and a list of RosettaPyMount objects created from the paths.
        """

        # Initialize lists to store processed paths and RosettaPyMount objects
        vf_list = []
        mounts = []

        # Split the input string by double quotes and process each segment
        vf_split = script_vars_v.split('"')
        for _, vf in enumerate(vf_split):
            # Check if the segment is a valid file or directory path
            if os.path.isfile(vf) or os.path.isdir(vf):
                # Create a RosettaPyMount object from the path and add it to the mounts list
                mount = RosettaPyMount.from_path(vf)
                mounts.append(mount)
                # Add the mounted path representation to vf_list
                vf_list.append(mount.mounted)
                continue
            # Add the unmodified segment to vf_list
            vf_list.append(vf)

        # Join the processed segments back together
        joined_vf = get_quoted('"'.join(vf_list))

        # Print a comparison between the original and processed strings
        print_diff(
            title="Mounted",
            labels={"Original": script_vars_v, "Rewrited": joined_vf},
            label_colors=["blue", "purple"],
            title_color="light_purple",
        )

        # Return the reconstructed string and the list of mounts
        return joined_vf, mounts

    @staticmethod
    def _mount_from_xml_variable(_cmd: str) -> Tuple[str, List[RosettaPyMount]]:
        """
        Processes XML variable commands, parsing and mounting file paths or XML fragments.

        This function is designed to handle strings that may represent direct file paths or XML fragments containing
        file paths. It identifies the type of command and processes it accordingly, either by mounting the file path
        or parsing the XML fragment.

        Parameters:
        - _cmd (str): The command string to be processed, typically containing a variable assignment or an XML fragment.

        Returns:
        - Tuple[str, List[RosettaPyMount]]: A tuple containing the processed command string and a list of mounted
        objects.
        """
        # Split the command by the '=' to separate the variable name from its value
        script_vars = _cmd.split("=")
        # Rejoin any parts that follow the first '=' as they constitute the variable's value
        script_vars_v = "=".join(script_vars[1:])

        # Print the parsing information for debugging purposes
        print(
            f"{render('Parsing:', 'purple-negative-bold')} "
            f"{render(script_vars[0], 'blue-negative')}="
            f"{render(script_vars_v, 'red-negative')}"
        )

        # Normal file input handling
        if os.path.isfile(script_vars_v) or os.path.isdir(script_vars_v):
            # If the value is a valid file or directory path, create a RosettaPyMount object from it
            mount = RosettaPyMount.from_path(script_vars_v)
            # Return the variable assignment with the mounted path and a list containing the mount object
            return f"{script_vars[0]}={mount.mounted}", [mount]

        # Handling of XML file blocks with file inputs
        # Example: '<AddOrRemoveMatchCsts name="cstadd" cstfile="/my/example.cst" cst_instruction="add_new"/>'
        if " " in script_vars_v and "<" in script_vars_v:  # Indicates an XML fragment
            # If the value appears to be an XML fragment, process it using the _process_xml_fragment method
            joined_vf, mounts = RosettaContainer._process_xml_fragment(script_vars_v)
            # Return the variable assignment with the processed XML fragment and the list of mount objects
            return f"{script_vars[0]}={joined_vf}", mounts

        # If the value does not match any of the above conditions, return the original command and an empty list
        return _cmd, []

    @staticmethod
    def mount(input_task: RosettaCmdTask) -> Tuple[RosettaCmdTask, List[types.Mount]]:
        """
        Prepares the mounting environment for a single task.

        This function is responsible for mounting files and directories required by the given task.

        Parameters:
            input_task (RosettaCmdTask): The task object containing the command and runtime directory information.

        Returns:
            Tuple[RosettaCmdTask, List[types.Mount]]: A tuple containing the updated task object
            with mounted paths and a list of mounts.
        """

        all_mounts: List[RosettaPyMount] = []
        updated_cmd_with_mounts = []

        for i, cmd_segment in enumerate(input_task.cmd):
            try:
                # Handle general options
                if cmd_segment.startswith("-"):
                    updated_cmd_with_mounts.append(cmd_segment)
                    continue

                # Handle option input
                if os.path.isfile(cmd_segment) or os.path.isdir(cmd_segment):
                    mount = RosettaPyMount.from_path(cmd_segment)
                    all_mounts.append(mount)
                    updated_cmd_with_mounts.append(mount.mounted)
                    continue

                # Handle Rosetta flag files
                if cmd_segment.startswith("@"):
                    mount = RosettaPyMount.from_path(cmd_segment[1:])
                    all_mounts.append(mount)
                    updated_cmd_with_mounts.append(f"@{mount.mounted}")
                    continue

                # Handle Rosetta Scripts variables
                if "=" in cmd_segment and input_task.cmd[i - 1] == "-parser:script_vars":
                    updated_cmd_segment, partial_mounts = RosettaContainer._mount_from_xml_variable(cmd_segment)
                    all_mounts.extend(partial_mounts)
                    updated_cmd_with_mounts.append(updated_cmd_segment)
                    continue

                updated_cmd_with_mounts.append(cmd_segment)

            except Exception as e:
                # handle exceptions without breaking the loop
                print(f"Error processing command '{cmd_segment}': {e}")
                updated_cmd_with_mounts.append(cmd_segment)
        try:
            if not os.path.exists(input_task.runtime_dir):
                os.makedirs(input_task.runtime_dir)
        except FileExistsError:
            warnings.warn(
                RuntimeWarning(
                    f"{input_task.runtime_dir} already exists. This might be a leftover from a previous run. "
                    "If you are sure that this is not the case, please delete the directory and try again."
                )
            )

        mounted_runtime_dir = RosettaPyMount.from_path(input_task.runtime_dir)
        all_mounts.append(mounted_runtime_dir)

        mounted_task = RosettaCmdTask(
            cmd=updated_cmd_with_mounts,
            base_dir=mounted_runtime_dir.mounted,
        )

        return mounted_task, RosettaPyMount.squeeze([mount.mount for mount in all_mounts])

    def recompose(self, cmd: List[str]) -> List[str]:
        """
        If necessary, recompose the command for MPI runs.

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
            return cmd

        # Recompose and return the new command list including MPI parameters
        return ["mpirun", "--use-hwthread-cpus", "-np", str(self.nproc), "--allow-run-as-root"] + cmd

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
        mounted_task, mounts = RosettaContainer.mount(input_task=task)
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
