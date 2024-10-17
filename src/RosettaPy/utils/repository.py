"""
RosettaRepoManager Module

This module provides functionality for managing the cloning of specific subdirectories from large GitHub repositories
using shallow clone, partial clone, and sparse checkout techniques. It ensures that only the necessary portions of a
repository are cloned to minimize disk usage, and optionally allows skipping submodule updates to further reduce the
cloned size. Additionally, it supports setting environment variables to point to the cloned directories.

Key Classes:
-------------
- RosettaRepoManager:
    Manages the process of cloning specific subdirectories and setting up environment variables to point to the
    cloned paths. Includes methods to verify Git installation, perform shallow and sparse checkouts, and
    optionally skip submodule updates.

Key Functions:
--------------
- partial_clone:
    A utility function that creates an instance of RosettaRepoManager, ensures Git is installed, and clones the
    specified subdirectory from a repository. It also sets the specified environment variable to the cloned path.

Main Features:
--------------
- Ensures minimal repository size by cloning only necessary subdirectories.
- Supports shallow cloning with a specified depth to reduce download time and disk usage.
- Allows skipping submodule initialization and updates for further size and complexity reduction.
- Sets environment variables to point to the cloned directories for ease of use in subsequent scripts or applications.

Usage Example:
--------------
To clone a specific subdirectory and set an environment variable, call the `partial_clone` function:

    partial_clone(
        repo_url="https://github.com/RosettaCommons/rosetta",
        subdirectory_to_clone="source/scripts/python/public",
        subdirectory_as_env="source/scripts/python/public",
        target_dir="rosetta_subdir_clone",
        env_variable="ROSETTA_PYTHON_SCRIPTS",
        skip_submodule=False
    )
"""

import os
import re
import shutil
import subprocess
import warnings
from typing import Dict, Optional

from git import Repo, exc

from .tools import timing


class RosettaLicenseWarning(UserWarning):
    """Warning for abtaing a license for the Rosetta source code."""


class RosettaRepoManager:
    """
    RosettaRepoManager is responsible for managing the cloning of specific subdirectories from large GitHub
    repositories using shallow clone, partial clone, and sparse checkout techniques. It ensures that the
    repository is only cloned if it hasn't been already, and sets an environment variable pointing to the
    cloned directory.

    RosettaRepoManager is responsible for managing the cloning of specific
    subdirectories from large GitHub repositories using shallow clone,
    partial clone, and sparse checkout techniques. It ensures that the
    repository is only cloned if it hasn't been already, and sets an
    environment variable pointing to the cloned directory.

    Attributes:
        repo_url (str): The URL of the repository to clone from.
        subdirectory_to_clone (str): The minimum subdirectory to fetch from the repository.
        subdirectory_as_env (str): The specific subdirectory to set as an environment variable.
        target_dir (str): The local directory where the subdirectory will be cloned.
        depth (int): The depth of the shallow clone (i.e., the number of recent commits to fetch).
        skip_submodule (bool): A flag to determine whether to skip submodule updates.

    Methods:
        ensure_git(required_version): Ensures Git is installed and meets the required version.
        _compare_versions(installed_version, required_version): Compares two version strings.
        is_cloned(): Checks if the repository has already been cloned into the target directory.
        clone_subdirectory(): Clones the specific subdirectory using Git sparse checkout.
        set_env_variable(env_var, subdirectory_as_env): Sets an environment variable to the subdirectory's path.
    """

    def __init__(self, repo_url: str, subdirectory_to_clone: str, subdirectory_as_env: str, target_dir: str):
        """
        Initializes the RosettaRepoManager to manage the cloning of a specific subdirectory from a GitHub repository.

        :param repo_url: The URL of the repository to clone from.
        :param subdirectory_to_clone: The minimum subdirectory to be checked out (relative to the repository root).
        :param subdirectory_as_env: The subdirectory to set as an environment variable.
        :param target_dir: The local directory to clone the subdirectory into.
        :param depth: The number of recent commits to clone (shallow clone depth).
        :param skip_submodule: A flag to skip submodule initialization and updates.
        """
        self.repo_url = repo_url
        self.subdirectory_to_clone = subdirectory_to_clone
        self.subdirectory_as_env = subdirectory_as_env
        self.target_dir = target_dir
        self.depth = 1
        self.skip_submodule = False

        if "rosettacommons" in self.repo_url:
            warnings.warn(
                RosettaLicenseWarning("Please make sure you have abtained a valid license for the Rosetta suite.")
            )

    def ensure_git(self, required_version: str = "2.34.1"):
        """
        Ensures that Git is installed and is at least the required version.

        :param required_version: The minimum Git version required.
        :raises RuntimeError: If Git is not installed or the version is less than the required version.
        """
        try:
            which_git = shutil.which("git")
            if which_git is None:
                raise FileNotFoundError("Git is not installed.")

            git_version_output = subprocess.check_output([which_git, "--version"], stderr=subprocess.STDOUT)
            git_version = git_version_output.decode("utf-8").strip()

            if not self._compare_versions(git_version, required_version):
                raise RuntimeError(f"Git version {git_version} < {required_version}. Please upgrade Git.")

            print(f"Git version {git_version} is sufficient.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            _e_msg = "Git is not installed or could not be found. Please install Git and try again."
            raise RuntimeError(_e_msg) from e
        except RuntimeError as e:
            raise RuntimeError(f"Git version is not supported. Please upgrade Git to {required_version}.") from e

    @staticmethod
    def _compare_versions(installed_version: str, required_version: str) -> bool:
        """
        Compares two version strings.

        :param installed_version: The installed version of Git.
        :param required_version: The required version of Git.
        :return: bool: True if the installed version is greater than or equal to the required version,
        False otherwise.
        """
        version_regex = r".*(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*"

        def extract_version_parts(version):
            match = re.match(version_regex, version)
            if match:
                return (int(match.group("major")), int(match.group("minor")), int(match.group("patch")))
            raise ValueError(f"Version string '{version}' is not in a valid format.")

        installed_parts = extract_version_parts(installed_version)
        required_parts = extract_version_parts(required_version)

        for installed, required in zip(installed_parts, required_parts):
            if installed == required:
                continue
            return installed > required
        return True

    def is_cloned(self) -> bool:
        """
        Checks if the repository has already been cloned into the target directory.
        It verifies that the directory exists, contains a valid Git repository, and
        optionally checks that the remote URL matches the expected repository URL.

        :return: True if the repository is already cloned, False otherwise.
        """
        if not os.path.exists(self.target_dir):
            return False

        try:
            repo = Repo(self.target_dir)
            origin = repo.remotes.origin.url
            if origin == self.repo_url and os.path.isdir(os.path.join(self.target_dir, self.subdirectory_to_clone)):
                return True

            print(f"Remote URL {origin} does not match expected {self.repo_url}.")
            return False
        except (exc.InvalidGitRepositoryError, exc.NoSuchPathError):
            return False

    def clone_subdirectory(self):
        """
        Clones only the specified subdirectory from the repository using shallow clone and sparse checkout.
        Optionally skips submodule updates if the `skip_submodule` attribute is set to True.

        If cloning fails or is interrupted, it removes the target directory to clean up the partial clone.

        :raises GitCommandError: If there is any issue running the git commands.
        :raises KeyboardInterrupt: If the cloning process is interrupted by the user.
        """
        if self.is_cloned():
            print("Repository already cloned.")
            return

        try:
            if not os.path.exists(self.target_dir):
                os.makedirs(self.target_dir)

            repo = Repo.init(self.target_dir)
            repo.git.remote("add", "origin", self.repo_url)
            repo.git.config("extensions.partialClone", "true")
            repo.git.fetch("origin", f"--depth={self.depth}", "--filter=blob:none")
            repo.git.config("core.sparseCheckout", "true")

            sparse_checkout_file = os.path.join(self.target_dir, ".git", "info", "sparse-checkout")
            with open(sparse_checkout_file, "w", encoding="utf-8") as f:
                f.write(f"{self.subdirectory_to_clone}\n")

            repo.git.pull("origin", "main")

            if not self.skip_submodule:
                self._update_submodules_in_subdir(repo)

        except (exc.GitCommandError, KeyboardInterrupt) as e:
            print(f"Error during git operation: {e}")
            if os.path.exists(self.target_dir):
                shutil.rmtree(self.target_dir)
            raise RuntimeError("Cloning failed or interrupted. Cleaned up partial clone.") from e

    def _update_submodules_in_subdir(self, repo):
        """
        Initialize and update only the submodules located within the specified subdirectory, unless
        skip_submodule is True.

        :param repo: The cloned Git repository.
        """
        gitmodules_path = os.path.join(self.target_dir, ".gitmodules")

        if not os.path.exists(gitmodules_path):
            print("No submodules found.")
            return

        with open(gitmodules_path, encoding="utf-8") as gitmodules_file:
            lines = gitmodules_file.readlines()

        submodules_to_update = []
        current_submodule: Optional[Dict[str, str]] = None

        for line in lines:
            if line.startswith("[submodule"):
                current_submodule = {}

            if "path" in line and isinstance(current_submodule, dict):
                submodule_path = line.split("=", 1)[1].strip()
                if submodule_path.startswith(self.subdirectory_to_clone):
                    current_submodule.update({"path": submodule_path})
                    submodules_to_update.append(current_submodule)

        if not submodules_to_update:
            print(f"No submodules found in {self.subdirectory_to_clone}")
            return

        for submodule in submodules_to_update:
            submodule_path = submodule["path"]
            print(f"Initializing and updating submodule at {submodule_path}")
            repo.git.submodule("init", submodule_path)
            repo.git.submodule("update", "--recursive", submodule_path)

    def set_env_variable(self, env_var: str, subdirectory_as_env: str) -> str:
        """
        Sets an environment variable to the subdirectory's path.

        :param env_var: Name of the environment variable to set.
        :param subdirectory_as_env: The subdirectory whose path will be set as the environment variable.
        """
        full_path = os.path.abspath(os.path.join(self.target_dir, subdirectory_as_env))
        os.environ[env_var] = full_path
        print(f"Environment variable {env_var} set to: {full_path}")
        return full_path


def partial_clone(
    repo_url: str = "https://github.com/RosettaCommons/rosetta",
    target_dir: str = "rosetta_db_clone",
    subdirectory_to_clone: str = "database",
    subdirectory_as_env: str = "database",
    env_variable: str = "ROSETTA3_DB",
):
    """
    Partially cloning the specific subdirectory
    and setting an environment variable pointing to the cloned path.

    """
    warnings.warn(UserWarning(f"Fetching {env_variable}:{subdirectory_as_env} from Rosetta GitHub Repository ..."))
    manager = RosettaRepoManager(repo_url, subdirectory_to_clone, subdirectory_as_env, target_dir)

    manager.ensure_git()

    with timing(f"cloning {subdirectory_to_clone} as {env_variable}"):
        manager.clone_subdirectory()

    warnings.warn(UserWarning(f"Cloned {subdirectory_to_clone} to {target_dir}."))

    return manager.set_env_variable(env_variable, subdirectory_as_env)


def clone_db_relax_script():
    """
    A example for cloning the relax scripts from the Rosetta database.

    This function uses the `partial_clone` function to clone specific relax scripts from the RosettaCommons
    GitHub repository.
    It sets an environment variable to specify the location of the cloned subdirectory and prints the value of
    the environment variable after cloning.
    """
    # Clone the relax scripts from the Rosetta repository to a specified directory
    partial_clone(
        repo_url="https://github.com/RosettaCommons/rosetta",
        target_dir="rosetta_db_clone_relax_script",
        subdirectory_as_env="database",
        subdirectory_to_clone="database/sampling/relax_scripts",
        env_variable="ROSETTA3_DB",
    )

    # Print the value of the environment variable after cloning
    print(f'ROSETTA3_DB={os.environ.get("ROSETTA3_DB")}')


def main():
    """
    Main function that sets up the Rosetta Python scripts.
    This function can be used as an entry point for testing or execution.
    """

    clone_db_relax_script()


if __name__ == "__main__":
    main()
