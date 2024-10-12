import contextlib
import shutil
import tempfile
import time
import os
from typing import Optional


@contextlib.contextmanager
def timing(msg: str):
    """
    A context manager for measuring the execution time of a block of code.

    When entering the context manager, it records the start time and logs a message.
    When exiting the context, it records the end time and prints the duration of the operation.

    Parameters:
    msg (str): A description of the operation to be logged.

    Example:
    with timing("My operation"):
        # Perform some operations
        time.sleep(1)  # Simulate a time-consuming task
    """
    print(f"Started {msg}")
    tic = time.time()  # Record the start time
    yield  # Enter the context manager
    toc = time.time()  # Record the end time
    # Print the completion message and the duration of the operation
    print(f"Finished {msg} in {toc - tic:.3f} seconds")


@contextlib.contextmanager
def tmpdir_manager(base_dir: Optional[str] = None):
    """
    Context manager that deletes a temporary directory on exit.

    This function is used to create a temporary directory when needed, and automatically delete it when the task is completed,
    to ensure clean up and avoid pollution to the file system. It uses the `contextlib.contextmanager` decorator to define a context manager.

    Parameters:
    - base_dir: Optional[str], the base directory where the temporary directory is created. If not provided, the system's default temporary directory will be used.

    Returns:
    - Yields the path of the created temporary directory. When the task using this directory is completed, the directory and all its contents will be deleted.
    """
    # Create a temporary directory
    tmpdir = tempfile.mkdtemp(dir=base_dir)
    try:
        # If the code in the try block raises an exception, the finally block will still be executed, ensuring the temporary directory is deleted
        yield tmpdir
    finally:
        # Delete the temporary directory, ignore errors if the directory does not exist
        shutil.rmtree(tmpdir, ignore_errors=True)


@contextlib.contextmanager
def isolate(save_to: str = "./save"):
    """
    A context manager that isolates threads from the file system.

    When entering the context, this manager changes the current working directory
    to the specified save directory, thereby limiting all file operations within
    that directory. This is useful for enhancing the security and reliability of
    the program, especially in a multi-threaded environment.

    Parameters:
    - save_to: str, default is "./save". Specifies the directory where files are saved during the context.

    Returns:
    This function is a context manager that does not directly return a value but yields control using the `yield` statement.
    """
    # Convert the save path to an absolute path for accurate subsequent operations
    save_to = os.path.abspath(save_to)
    # Ensure the save directory exists; if it does not, create it. exist_ok=True means no error is raised if the directory already exists
    os.makedirs(save_to, exist_ok=True)

    # Save the current directory path to restore it later
    curdir = os.getcwd()
    # Change to the save directory; all file operations within the context will occur here
    os.chdir(save_to)
    try:
        # Execute the code block within the context
        yield
    finally:
        # Restore the previous current directory regardless of whether the context code executed successfully
        os.chdir(curdir)
