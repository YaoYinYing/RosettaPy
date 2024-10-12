import copy
from dataclasses import dataclass, field
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
        if self.image.endswith("mpi"):
            self.mpi_available = True
        if self.nproc <= 0:
            self.nproc = 4

        if self.prohibit_mpi:
            self.mpi_available = False

    @staticmethod
    def mounted_name(path: str) -> str:
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} does not exist.")
        path = os.path.abspath(path)
        dir = os.path.dirname(path) if os.path.isfile(path) else path

        return dir.replace("/", "-").lstrip("-").rstrip("-")

    def mount(self, input_task: RosettaCmdTask) -> Tuple[RosettaCmdTask, List[types.Mount]]:
        """
        Mount for a single task
        """
        _mounts = []
        _mounted_paths = []

        mounted_cmd = []
        for i, _cmd in enumerate(input_task.cmd):
            # options
            if _cmd.startswith("-"):
                mounted_cmd.append(_cmd)
                continue

            # file and dir exists
            if os.path.isfile(_cmd) or os.path.isdir(_cmd):
                mount, mounted = self._create_mount(self.mounted_name(_cmd), _cmd)
                if all(m != mount for m in _mounts):
                    _mounts.append(mount)
                    _mounted_paths.append(mounted)
                mounted_cmd.append(mounted)

                continue

            # rosetta flags
            if _cmd.startswith("@"):
                _flag_file = _cmd[1:]
                mount, mounted = self._create_mount(self.mounted_name(_flag_file), _flag_file)
                mounted_cmd.append(f"@{mounted}")
                if all(m != mount for m in _mounts):
                    _mounts.append(mount)
                continue

            # Rosetta_script vars input, k=v
            if "=" in _cmd and input_task.cmd[i - 1] == "-parser:script_vars":
                script_vars = _cmd.split("=")
                if os.path.isfile(script_vars[1]) or os.path.isdir(script_vars[1]):

                    mount, mounted = self._create_mount(self.mounted_name(script_vars[1]), script_vars[1])
                    if all(m != mount for m in _mounts):
                        _mounts.append(mount)
                        _mounted_paths.append(mounted)
                    mounted_cmd.append(f"{script_vars[0]}={mounted}")
                else:
                    mounted_cmd.append(_cmd)
                continue

            # binary name, etc.
            mounted_cmd.append(_cmd)

        if input_task.base_dir is not None:
            os.makedirs(input_task.base_dir, exist_ok=True)
            mount, mounted_base_dir = self._create_mount(self.mounted_name(input_task.base_dir), input_task.base_dir)
            if all(m != mount for m in _mounts):
                _mounts.append(mount)
                _mounted_paths.append(mounted_base_dir)
        else:
            mounted_base_dir = ""

        curdir = os.getcwd()
        mount, mounted_curdir = self._create_mount(self.mounted_name(curdir), curdir)
        print(f"Curdir ({curdir}) is mounted as {mounted_curdir}")
        if all(m != mount for m in _mounts):
            _mounts.append(mount)
            _mounted_paths.append(mounted_curdir)

        mounted_task = RosettaCmdTask(cmd=mounted_cmd, task_label=input_task.task_label, base_dir=mounted_base_dir)

        return mounted_task, _mounts

    def recompose(self, cmd: List[str]) -> List[str]:
        if not self.mpi_available:
            warnings.warn(RuntimeWarning("This container has static build of Rosetta. Nothing has to be recomposed."))
            return cmd

        return ["mpirun", "--use-hwthread-cpus", "-np", str(self.nproc), "--allow-run-as-root"] + cmd

    def run_single_task(self, task: RosettaCmdTask) -> RosettaCmdTask:
        """
        Run a task in docker container
        """

        mounted_task, mounts = self.mount(input_task=task)
        client = docker.from_env()
        print(f"Mounted with Command: {mounted_task.cmd}")

        container = client.containers.run(
            image=self.image,
            command=mounted_task.cmd,
            remove=True,
            detach=True,
            mounts=mounts,
            user=self.user,
            stdout=True,
            stderr=True,
            working_dir=(
                mounted_task.runtime_dir
                if mounted_task.base_dir is not None and mounted_task.task_label is not None
                else None
            ),
        )

        # Add signal handler to ensure CTRL+C also stops the running container.
        signal.signal(signal.SIGINT, lambda unused_sig, unused_frame: container.kill())

        for line in container.logs(stream=True):
            print(line.strip().decode("utf-8"))

        return task

    def _create_mount(self, mount_name: str, path: str, read_only=False) -> Tuple[types.Mount, str]:
        """Create a mount point for each file and directory used by the model."""
        path = os.path.abspath(path)
        target_path = os.path.join(self.root_mount_directory, mount_name)

        if os.path.isdir(path):
            source_path = path
            mounted_path = target_path
        else:
            source_path = os.path.dirname(path)
            mounted_path = os.path.join(target_path, os.path.basename(path))
        if not os.path.exists(source_path):
            os.makedirs(source_path)
        print(
            f"{C.YELLOW}{C.BOLD}Mount:{C.RESET} \n{C.RED}{C.BOLD}- {source_path}{C.RESET} {C.BOLD}{C.PURPLE}{C.NEGATIVE}->{C.RESET} \n{C.GREEN}{C.BOLD}+ {target_path}{C.RESET}\n"
        )
        mount = types.Mount(
            target=str(target_path),
            source=str(source_path),
            type="bind",
            read_only=read_only,
        )
        return mount, str(mounted_path)
