from dataclasses import dataclass
import os
import signal
import warnings
from docker import types
from typing import List, Tuple
import docker

from ..utils import RosettaCmdTask
from ..utils.escape import Colors as C


_ROOT_MOUNT_DIRECTORY = os.path.abspath("/tmp/")
os.makedirs(_ROOT_MOUNT_DIRECTORY, exist_ok=True)


@dataclass
class RosettaContainer:
    """
    A class to represent a docker container for Rosetta.
    """

    image: str = "rosettacommons/rosetta:mpi"
    root_mount_directory: str = _ROOT_MOUNT_DIRECTORY
    mpi_available: bool = False
    user: str = f"{os.geteuid()}:{os.getegid()}"
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
    def mounted_name(path: str) -> str:
        """
        Returns a formatted name suitable for mounting based on the given path.

        This method first validates the provided path to ensure it exists in the file system, raising an exception if it does not.
        It then obtains the absolute path and determines whether to use the parent directory or the path itself based on whether the path is a file or a directory.
        Finally, it formats the path by replacing slashes (/) with hyphens (-) to create a safe name suitable for mounting.

        :param path: str The input file or directory path.
        :return: str A formatted name suitable for mounting.
        """

        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} does not exist.")
        path = os.path.abspath(path)
        dir = os.path.dirname(path) if os.path.isfile(path) else path

        return dir.replace("/", "-").strip("-")

    def mount(self, input_task: RosettaCmdTask) -> Tuple[RosettaCmdTask, List[types.Mount]]:
        """
        Prepares the mounting environment for a single task.

        This function is responsible for mounting files and directories required by the given task.

        Parameters:
            input_task (RosettaCmdTask): The task object containing the command and runtime directory information.

        Returns:
            Tuple[RosettaCmdTask, List[types.Mount]]: A tuple containing the updated task object with mounted paths and a list of mounts.
        """

        _mounts = []
        _mounted_paths = []
        mounted_cmd = []

        def unique_mount(
            path_to_mount: str,
        ) -> str:
            """
            Normalize the given mount path and create a unique mount point.

            This function first normalizes the received mount path to ensure a consistent format.
            Then, it checks the existing mounts, and if the mount point does not already exist,
            it creates a new mount point and records it.
            Finally, it returns the normalized mount path or the existing one if it was already mounted.

            Parameters:
            - path_to_mount (str): The path to be mounted.

            Returns:
            - str: The normalized mount path.
            """
            normalized_path = os.path.normpath(path_to_mount)
            mount, mounted = self._create_mount(self.mounted_name(normalized_path), normalized_path)
            if not any(m == mount for m in _mounts):
                _mounts.append(mount)
                _mounted_paths.append(mounted)

            return mounted

        for i, _cmd in enumerate(input_task.cmd):
            try:
                # Handle general options
                if _cmd.startswith("-"):
                    mounted_cmd.append(_cmd)
                    continue

                # Handle option input
                if os.path.isfile(_cmd) or os.path.isdir(_cmd):
                    mounted = unique_mount(_cmd)
                    mounted_cmd.append(mounted)
                    continue

                # Handle Rosetta flag files
                if _cmd.startswith("@"):
                    _flag_file = _cmd[1:]
                    mounted = unique_mount(_flag_file)
                    mounted_cmd.append(f"@{mounted}")
                    continue

                # Handle Rosetta Scripts variables
                if "=" in _cmd and input_task.cmd[i - 1] == "-parser:script_vars":
                    script_vars = _cmd.split("=")
                    script_vars_v = "=".join(script_vars[1:])

                    print(
                        f"{C.PURPLE}{C.NEGATIVE}{C.BOLD}Parsing:{C.RESET} {C.BLUE}{C.NEGATIVE}{script_vars[0]}{C.RESET}={C.RED}{C.NEGATIVE}{script_vars_v}{C.RESET}"
                    )
                    # normal file input
                    if os.path.isfile(script_vars_v) or os.path.isdir(script_vars_v):
                        mounted = unique_mount(script_vars_v)
                        mounted_cmd.append(f"{script_vars[0]}={mounted}")

                    # xml file block with file input
                    # eg.
                    # '<AddOrRemoveMatchCsts name="cstadd" cstfile="/my/example.cst" cst_instruction="add_new"/>'
                    elif " " in script_vars_v and ("<" in script_vars_v):  # xml fragment
                        vf_list = []

                        vf_split = script_vars_v.split('"')
                        for i, vf in enumerate(vf_split):
                            if os.path.isfile(vf) or os.path.isdir(vf):
                                mounted = unique_mount(vf)
                                vf_list.append(mounted)
                                continue
                            vf_list.append(vf)

                        joined_vf = '"'.join(vf_list)
                        if not joined_vf.startswith("'"):
                            joined_vf = "'" + joined_vf

                        if not joined_vf.endswith("'"):
                            joined_vf += "'"

                        print(
                            f"{C.BLUE}{C.NEGATIVE}{C.BOLD}Original:{C.RESET} {C.BLUE}{C.NEGATIVE}{script_vars_v}{C.RESET}"
                        )
                        print(
                            f"{C.PURPLE}{C.NEGATIVE}{C.BOLD}Rewrited:{C.RESET} {C.PURPLE}{C.NEGATIVE}{joined_vf}{C.RESET}\n"
                        )
                        mounted_cmd.append(f"{script_vars[0]}={joined_vf}")
                    else:
                        mounted_cmd.append(_cmd)
                    continue

                mounted_cmd.append(_cmd)

            except Exception as e:
                print(f"Error processing command '{_cmd}': {e}")
                mounted_cmd.append(_cmd)

        os.makedirs(input_task.runtime_dir, exist_ok=True)
        mounted_runtime_dir = unique_mount(input_task.runtime_dir)

        mounted_task = RosettaCmdTask(
            cmd=mounted_cmd,
            base_dir=mounted_runtime_dir,
        )

        return mounted_task, _mounts

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
        mounted_task, mounts = self.mount(input_task=task)
        client = docker.from_env()

        print(
            f"{C.GREEN}{C.BOLD}{C.NEGATIVE}Mounted with Command: {C.RESET} {C.BOLD}{C.GREEN}{mounted_task.cmd}{C.RESET}"
        )
        print(
            f"{C.YELLOW}{C.BOLD}{C.NEGATIVE}Working directory ->{C.RESET} {C.BOLD}{C.YELLOW}{mounted_task.runtime_dir}{C.RESET}"
        )

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
        )

        # Register a signal handler to stop the running container on SIGINT (e.g., Ctrl+C)
        signal.signal(signal.SIGINT, lambda unused_sig, unused_frame: container.kill())

        for line in container.logs(stream=True):
            print(line.strip().decode("utf-8"))

        return task

    def _create_mount(self, mount_name: str, path: str, read_only=False) -> Tuple[types.Mount, str]:
        """
        Create a mount point for each file and directory used by the model.

        Parameters:
        - mount_name (str): The name of the mount point.
        - path (str): The path to the file or directory.
        - read_only (bool): Whether the mount point is read-only. Defaults to False.

        Returns:
        - types.Mount: The created mount point object.
        - str: The path of the mounted point within the container.
        """
        # Get the absolute path and the target mount path
        path = os.path.abspath(path)
        target_path = os.path.join(self.root_mount_directory, mount_name)

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
        print(
            f"{C.YELLOW}{C.BOLD}Mount:{C.RESET} \n{C.RED}{C.BOLD}- {source_path}{C.RESET} {C.BOLD}{C.PURPLE}{C.NEGATIVE}->{C.RESET} \n{C.GREEN}{C.BOLD}+ {target_path}{C.RESET}\n"
        )

        # Create and return the mount object and mounted path
        mount = types.Mount(
            target=str(target_path),
            source=str(source_path),
            type="bind",
            read_only=read_only,
        )
        return mount, str(mounted_path)
