"""
Finder module for Rosetta binary
"""

import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

ALL_MODES = ["static", "mpi", "default", "cxx11threadserialization", "cxx11threadmpiserialization"]
ALL_OS = ["linux", "macos"]
ALL_COMPILERS = ["gcc", "clang"]
ALL_RELEASES = ["release", "debug"]


ModeType = Literal["static", "mpi", "default", "cxx11threadserialization", "cxx11threadmpiserialization"]
OsType = Literal["linux", "macos"]
CompilerType = Literal["gcc", "clang"]
ReleaseType = Literal["release", "debug"]


@dataclass
class RosettaBinary:
    """
    Represents a Rosetta binary executable.

    Attributes:
        dirname (str): The directory where the binary is located.
        binary_name (str): The base name of the binary (e.g., 'rosetta_scripts').
        mode (Optional[Literal['static', 'mpi', 'default']]): The build mode.
        os (Literal['linux', 'macos']): The operating system.
        compiler (Literal['gcc', 'clang']): The compiler used.
        release (Literal['release', 'debug']): The build type.

    Properties:
        filename (str): Reconstructed filename from the binary components.
        full_path (str): Full path to the binary executable.

    Methods:
        from_filename(cls, dirname: str, filename: str): Creates an instance by parsing the filename.
    """

    dirname: str
    binary_name: str
    mode: Optional[ModeType] = None
    os: Optional[OsType] = None
    compiler: Optional[CompilerType] = None
    release: Optional[ReleaseType] = None

    _regex_subfix = rf"""
            (
                (
                    \.(?P<mode>{'|'.join(ALL_MODES)})
                )?
                (
                    \.(?P<os>{'|'.join(ALL_OS)})
                    (?P<compiler>{'|'.join(ALL_COMPILERS)})
                    (?P<release>{'|'.join(ALL_RELEASES)})
                )
            )?$
        """

    @property
    def filename(self) -> str:
        """
        Reconstruct the filename from the binary components.

        Returns:
            str: The reconstructed filename.
        """
        parts = [self.binary_name]
        if self.mode:
            parts.append(f"{self.mode}")
        if self.os:
            parts.append(f"{self.os}{self.compiler}{self.release}")
        filename = ".".join(parts)
        return filename

    @property
    def full_path(self) -> str:
        """
        Get the full path to the binary executable.

        Returns:
            str: The full path combining dirname and filename.
        """
        return os.path.join(self.dirname, self.filename)

    @classmethod
    def from_filename(cls, dirname: str, filename: str):
        """
        Create a RosettaBinary instance by parsing the filename.

        Parameters:
            dirname (str): The directory where the binary is located.
            filename (str): The name of the binary file.

        Returns:
            RosettaBinary: An instance of RosettaBinary with parsed attributes.

        Raises:
            ValueError: If the filename does not match the expected pattern.
        """
        # Regular expression to parse the filenam
        regex = rf"""
            (?P<binary_name>[\w]+)
            (
                (
                    \.(?P<mode>{'|'.join(ALL_MODES)})
                )?
                (
                    \.(?P<os>{'|'.join(ALL_OS)})
                    (?P<compiler>{'|'.join(ALL_COMPILERS)})
                    (?P<release>{'|'.join(ALL_RELEASES)})
                )
            )?$
        """
        pattern = re.compile(regex, re.VERBOSE)
        match = pattern.match(filename)
        if not match:
            raise ValueError(f"Filename '{filename}' does not match the expected pattern.")

        binary_name = match.group("binary_name")
        mode = match.group("mode")
        os_name = match.group("os")
        compiler = match.group("compiler")
        release = match.group("release")

        return cls(dirname, binary_name, mode, os_name, compiler, release)  # type: ignore


class RosettaFinder:
    """
    Searches for Rosetta binaries in specified directories.

    Methods:
        __init__(self, search_path=None): Initializes the RosettaFinder with an optional search path.
        find_binary(self, binary_name='rosetta_scripts'): Searches for the Rosetta binary.
    """

    def __init__(self, search_path=None):
        """
        Initialize the RosettaFinder with an optional search path.

        Parameters:
            search_path (str or Path): Custom path to search for the binary.
        """
        self.search_path = Path(search_path) if search_path else None

        # OS check: Raise an error if not running on Linux or macOS
        if not sys.platform.startswith(("linux", "darwin")):
            raise OSError("Unsupported OS. This script only runs on Linux or macOS.")

        # Determine the search paths
        self.search_paths: list[Path] = self.get_search_paths()

    @staticmethod
    def build_regex_pattern(binary_name):
        """
        Build the regex pattern to search for the Rosetta binary.

        Parameters:
            binary_name (str): Name of the Rosetta binary to search for.

        Returns:
            re.Pattern: Compiled regular expression pattern.
        """
        regex_string = rf"""
        ({binary_name})
        (
            (\.(?P<mode>{'|'.join(ALL_MODES)}))?
            (\.
                (?P<os>{'|'.join(ALL_OS)})
                (?P<compiler>{'|'.join(ALL_COMPILERS)})
                (?P<release>{'|'.join(ALL_RELEASES)})
            )
        )?$"""
        return re.compile(regex_string, re.VERBOSE)

    def get_search_paths(self):
        """
        Determine the paths to search for the binary.

        Returns:
            list of Path: List of paths to search.
        """
        paths = []

        # 0. Customized path
        if self.search_path:
            paths.append(self.search_path)

        # 1. ROSETTA_BIN environment variable
        rosetta_bin_env = os.environ.get("ROSETTA_BIN")
        if rosetta_bin_env:
            paths.append(Path(rosetta_bin_env))

        # 2. ROSETTA3/bin
        paths.append(Path("ROSETTA3") / "bin")

        # 3. ROSETTA/main/source/bin/
        paths.append(Path("ROSETTA") / "main" / "source" / "bin")

        return paths

    def find_binary(self, binary_name="rosetta_scripts"):
        """
        Search for the Rosetta binary in the specified paths.

        Parameters:
            binary_name (str): Name of the Rosetta binary to search for.
                               Default is 'rosetta_scripts'.

        Returns:
            Path: Path to the found binary.

        Raises:
            FileNotFoundError: If the binary is not found.
        """
        bin_in_path = shutil.which(binary_name)

        if bin_in_path is not None:
            return RosettaBinary.from_filename(os.path.dirname(bin_in_path), os.path.basename(bin_in_path))

        pattern = self.build_regex_pattern(binary_name)
        for path in self.search_paths:
            if not (path.exists() and path.is_dir()):
                continue
            for file in path.iterdir():
                if not file.is_file():
                    continue
                if not pattern.match(file.name):
                    continue
                try:
                    rosetta_binary = RosettaBinary.from_filename(str(path), file.name)
                    if rosetta_binary.binary_name == binary_name:
                        return rosetta_binary
                except ValueError:
                    continue

        raise FileNotFoundError(f"{binary_name} binary not found in the specified paths.")


def main() -> None:
    """
    Main function to find the Rosetta binary.

    Returns:
        None
    """

    bin_str = sys.argv[1]
    bin_path = sys.argv[2] if len(sys.argv) > 2 else None

    which_bin = shutil.which(bin_str)

    if which_bin and os.path.isfile(which_bin):
        # dockerized
        print(which_bin)
        return

    finder = RosettaFinder(bin_path)
    binary_path = finder.find_binary(bin_str)
    if not os.path.isfile(binary_path.full_path):
        raise FileNotFoundError(f"Binary '{binary_path.full_path}' does not exist.")

    print(binary_path.full_path)
