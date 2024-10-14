import os
import pytest
from unittest import mock
from RosettaPy.utils import timing, tmpdir_manager
from git import exc
from RosettaPy.utils.repository import RosettaRepoManager, main


# Define the repo_manager fixture using tmpdir_manager
@pytest.fixture(scope="function")
def repo_manager():
    """
    Pytest fixture to create an instance of RosettaRepoManager using tmpdir_manager.
    This ensures that the target directory is a temporary directory that is cleaned up afterward.
    """
    with tmpdir_manager() as temp_dir:
        yield RosettaRepoManager(
            repo_url="https://github.com/RosettaCommons/rosetta",
            subdirectory="source/scripts/python/public",
            target_dir=os.path.join(temp_dir, "rosetta"),
        )


@mock.patch("subprocess.check_output")
def test_ensure_git_version_ok(mock_check_output, repo_manager):
    """
    Test that ensure_git correctly verifies the Git version.
    """
    # Mock the Git version output
    mock_check_output.return_value = b"git version 2.34.1"

    # No exception should be raised
    repo_manager.ensure_git()

    # Check that subprocess was called with the correct arguments
    mock_check_output.assert_called_with(["git", "--version"], stderr=mock.ANY)


@mock.patch("subprocess.check_output")
def test_ensure_git_version_too_old(mock_check_output, repo_manager):
    """
    Test that ensure_git raises an error if the Git version is too old.
    """
    # Mock an older Git version
    mock_check_output.return_value = b"git version 2.25.0"

    with pytest.raises(RuntimeError, match="Please upgrade Git."):
        repo_manager.ensure_git()


@pytest.mark.parametrize("path_exists,path_isdir,is_cloned", [(True, False, False), (False, True, False)])
@mock.patch("os.path.isdir")
@mock.patch("os.path.exists")
@mock.patch("git.Repo")
def test_is_cloned(mock_repo, mock_path_exists, mock_path_isdir, path_exists, path_isdir, is_cloned, repo_manager):
    """
    Test that is_cloned returns True if the repository has already been cloned.
    """
    # os.makedirs(os.path.abspath(repo_manager.target_dir), exist_ok=True)
    # Mock the target directory existence
    mock_path_exists.return_value = path_exists
    mock_path_isdir.return_value = path_isdir

    # Mock the repository remote URL to match the expected repo_url
    mock_repo.return_value.remotes.origin.url = repo_manager.repo_url

    assert repo_manager.is_cloned() is is_cloned


@mock.patch("os.path.exists")
@mock.patch("git.Repo")
def test_is_cloned_false_invalid_repo(mock_repo, mock_path_exists, repo_manager):
    """
    Test that is_cloned returns False if the target directory is not a valid Git repository.
    """
    # Mock the target directory existence
    mock_path_exists.return_value = True
    mock_repo.side_effect = exc.InvalidGitRepositoryError

    assert repo_manager.is_cloned() is False


@mock.patch("os.makedirs")
@mock.patch("git.Repo")
def test_clone_subdirectory_already_cloned(mock_repo, mock_makedirs, repo_manager):
    """
    Test that clone_subdirectory does nothing if the repository is already cloned.
    """
    # Mock that the repository is already cloned
    with mock.patch.object(repo_manager, "is_cloned", return_value=True):
        repo_manager.clone_subdirectory()

    # Ensure makedirs and repo initialization are not called
    mock_makedirs.assert_not_called()
    mock_repo.init.assert_not_called()


def test_clone_subdirectory(repo_manager):
    """
    Test the full flow of clone_subdirectory when the repository is not yet cloned.
    """
    # not cloned
    assert repo_manager.is_cloned() == False

    # Ensure the directory does not exist initially
    assert not os.path.exists(repo_manager.target_dir)

    # Now call clone_subdirectory
    repo_manager.clone_subdirectory()

    # Check that the directory was created
    assert os.path.exists(repo_manager.target_dir)

    # cloned
    assert repo_manager.is_cloned() == True

    # dir exists
    assert os.path.exists(os.path.join(repo_manager.target_dir, repo_manager.subdirectory))


@mock.patch("os.path.abspath")
@mock.patch.dict(os.environ, {}, clear=True)
def test_set_env_variable(mock_abspath, repo_manager):
    """
    Test that set_env_variable sets the correct environment variable.
    """
    # Mock the absolute path
    mock_abspath.return_value = "/absolute/path/to/subdir"

    # Call the method to set the environment variable
    repo_manager.set_env_variable("ROSETTA_PYTHON_SCRIPTS")

    # Check that the environment variable was set
    assert os.environ["ROSETTA_PYTHON_SCRIPTS"] == "/absolute/path/to/subdir"

    # Ensure that os.path.abspath was called with the correct arguments
    mock_abspath.assert_called_once_with(os.path.join(repo_manager.target_dir, repo_manager.subdirectory))


def test_main_function():
    """
    Test the main function that sets up the Rosetta Python scripts.
    """
    with mock.patch("RosettaPy.utils.repository.setup_rosetta_python_scripts") as mock_setup:

        main()
        mock_setup.assert_called_once()
