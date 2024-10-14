import os
import shutil
import subprocess
from git import Repo, exc
from RosettaPy.utils import timing


class RosettaRepoManager:
    """
    RosettaRepoManager is responsible for managing the cloning of specific subdirectories from large GitHub repositories
    using shallow clone, partial clone, and sparse checkout techniques. It ensures that the repository is only cloned
    if it hasn't been already, and sets an environment variable pointing to the cloned directory.

    Attributes:
        repo_url (str): The URL of the repository to clone from.
        subdirectory (str): The specific subdirectory to fetch from the repository.
        target_dir (str): The local directory where the subdirectory will be cloned.
        depth (int): The depth of the shallow clone (i.e., the number of recent commits to fetch).

    Methods:
        ensure_git(required_version): Ensures Git is installed and meets the required version.
        _compare_versions(installed_version, required_version): Compares two version strings.
        is_cloned(): Checks if the repository has already been cloned into the target directory.
        clone_subdirectory(): Clones the specific subdirectory using Git sparse checkout.
        set_env_variable(env_var): Sets an environment variable to the subdirectory's path.
    """

    def __init__(self, repo_url: str, subdirectory: str, target_dir: str, depth: int = 1):
        """
        Initializes the RosettaRepoManager to manage the cloning of a specific subdirectory from a GitHub repository.

        :param repo_url: The URL of the repository to clone from.
        :param subdirectory: The subdirectory to be checked out (relative to the repository root).
        :param target_dir: The local directory to clone the subdirectory into.
        :param depth: The number of recent commits to clone (shallow clone depth).
        """
        self.repo_url = repo_url
        self.subdirectory = subdirectory
        self.target_dir = target_dir
        self.depth = depth

    def ensure_git(self, required_version: str = "2.34.1"):
        """
        Ensures that Git is installed and is at least the required version.

        :param required_version: The minimum Git version required.
        :raises RuntimeError: If Git is not installed or the version is less than the required version.
        """
        try:
            # Get the installed git version
            git_version_output = subprocess.check_output(["git", "--version"], stderr=subprocess.STDOUT)
            git_version = git_version_output.decode("utf-8").strip().split()[-1]

            # Compare versions
            if self._compare_versions(git_version, required_version) < 0:
                raise RuntimeError(
                    f"Git version {git_version} is less than the required version {required_version}. Please upgrade Git."
                )

            print(f"Git version {git_version} is sufficient.")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError("Git is not installed or could not be found. Please install Git and try again.") from e

    @staticmethod
    def _compare_versions(installed_version: str, required_version: str) -> int:
        """
        Compares two version strings.

        :param installed_version: The installed version of Git.
        :param required_version: The required version of Git.
        :return: -1 if installed_version < required_version, 0 if they are equal, 1 if installed_version > required_version.
        """
        installed_parts = list(map(int, installed_version.split(".")))
        required_parts = list(map(int, required_version.split(".")))

        # Compare corresponding version numbers
        for installed, required in zip(installed_parts, required_parts):
            if installed < required:
                return -1
            elif installed > required:
                return 1

        # If we reach here, they are equal in the compared parts
        return 0

    def is_cloned(self) -> bool:
        """
        Checks if the repository has already been cloned into the target directory.
        It verifies that the directory exists, contains a valid Git repository, and
        optionally checks that the remote URL matches the expected repository URL.

        :return: True if the repository is already cloned, False otherwise.
        """
        if not os.path.exists(self.target_dir):
            return False

        # Check if the directory is a valid Git repository
        try:
            repo = Repo(self.target_dir)
            # Verify that the repository has the correct remote URL
            origin = repo.remotes.origin.url
            if origin == self.repo_url and os.path.isdir(os.path.join(self.target_dir, self.subdirectory)):
                return True
            else:
                print(f"Remote URL {origin} does not match expected {self.repo_url}.")
                return False
        except (exc.InvalidGitRepositoryError, exc.NoSuchPathError):
            return False

    def clone_subdirectory(self):
        """
        Clones only the specified subdirectory from the repository using shallow clone and sparse checkout.
        If cloning fails or is interrupted, it removes the target directory to clean up the partial clone.

        This is done using GitPython's repo.git interface to handle the sparse checkout and
        perform Git commands such as 'fetch', 'config', and 'sparse-checkout'.

        :raises GitCommandError: If there is any issue running the git commands.
        :raises KeyboardInterrupt: If the cloning process is interrupted by the user.
        """
        if self.is_cloned():
            print("Repository already cloned.")
            return

        try:
            if not os.path.exists(self.target_dir):
                print(f"Creating directory: {self.target_dir}")
                # Ensure the target directory exists
                os.makedirs(self.target_dir)

            # Initialize the repository using GitPython
            repo = Repo.init(self.target_dir)

            # Add the remote repository
            repo.git.remote("add", "origin", self.repo_url)

            # Enable partial clone support
            repo.git.config("extensions.partialClone", "true")

            # Perform a shallow fetch with partial clone
            repo.git.fetch("origin", f"--depth={self.depth}", "--filter=blob:none")  # Shallow + Partial clone

            # Enable sparse checkout
            repo.git.config("core.sparseCheckout", "true")

            # Write the subdirectory we want to fetch into the sparse-checkout file
            sparse_checkout_file = os.path.join(self.target_dir, ".git", "info", "sparse-checkout")
            with open(sparse_checkout_file, "w") as f:
                f.write(f"{self.subdirectory}\n")

            # Pull only the specified subdirectory
            repo.git.pull("origin", "main")

        except (exc.GitCommandError, KeyboardInterrupt) as e:
            # Handle Git errors or interruptions
            print(f"Error during git operation: {e}")
            if os.path.exists(self.target_dir):
                shutil.rmtree(self.target_dir)
            raise RuntimeError("Cloning failed or interrupted. Cleaned up partial clone.") from e

    def set_env_variable(self, env_var: str) -> str:
        """
        Sets an environment variable to the subdirectory's path.

        :param env_var: Name of the environment variable to set.
        """
        full_path = os.path.abspath(os.path.join(self.target_dir, self.subdirectory))
        os.environ[env_var] = full_path
        print(f"Environment variable {env_var} set to: {full_path}")
        return full_path


def setup_rosetta_python_scripts(target_dir: str = "rosetta_subdir_clone"):
    """
    Set up the Rosetta Python scripts by cloning the specific subdirectory
    and setting an environment variable pointing to the cloned path.

    This will clone 'source/scripts/python/public' from the Rosetta repository
    and set the 'ROSETTA_PYTHON_SCRIPTS' environment variable to the directory.
    """
    repo_url = "https://github.com/RosettaCommons/rosetta"
    subdirectory = "source/scripts/python/public"

    manager = RosettaRepoManager(repo_url, subdirectory, target_dir)

    # Ensure Git is installed and the correct version
    manager.ensure_git()

    # Use the timing context manager to track the cloning process
    with timing("cloning"):
        manager.clone_subdirectory()

    return manager.set_env_variable("ROSETTA_PYTHON_SCRIPTS")


def main():
    """
    Main function that sets up the Rosetta Python scripts.
    This function can be used as an entry point for testing or execution.
    """
    setup_rosetta_python_scripts()


if __name__ == "__main__":
    main()
