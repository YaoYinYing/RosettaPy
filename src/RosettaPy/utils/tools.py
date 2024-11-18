"""
Tools of running tasks
"""

import contextlib
import os
import shutil
import tempfile
import time
import warnings
from typing import List, Optional, TypeVar

T = TypeVar("T")


# from AlphaFold
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


# from AlphaFold
@contextlib.contextmanager
def tmpdir_manager(base_dir: Optional[str] = None):
    """
    Context manager that deletes a temporary directory on exit.

    This function is used to create a temporary directory when needed,
    and automatically delete it when the task is completed,
    to ensure clean up and avoid pollution to the file system.
    It uses the `contextlib.contextmanager` decorator to define a context manager.

    Parameters:
    - base_dir: Optional[str], the base directory where the temporary directory is created.
                If not provided, the system's default temporary directory will be used.

    Returns:
    - Yields the path of the created temporary directory. When the task using this directory is completed,
        the directory and all its contents will be deleted.
    """
    # Create a temporary directory
    tmpdir = tempfile.mkdtemp(dir=base_dir)
    try:
        # If the code in the try block raises an exception, the finally block will still be executed,
        # ensuring the temporary directory is deleted
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
    This function is a context manager that does not directly return a value but yields control
    using the `yield` statement.
    """
    # Convert the save path to an absolute path for accurate subsequent operations
    save_to = os.path.abspath(save_to)
    # Ensure the save directory exists; if it does not, create it. exist_ok=True means no error is
    # raised if the directory already exists
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


def squeeze(items: List[T]) -> List[T]:
    """
    Squeezes a list of hashable/unhashable dataclass objects by removing duplicates.

    This function iterates through a list of unhashable dataclass objects and removes any duplicates.
    It uses a simple linear search algorithm to compare each item with the items already in the squeezed list.
    If a duplicate is found, it is skipped; otherwise, it is added to the squeezed list.

    Parameters:
    - items (List[T]): A list of unhashable dataclass objects to be squeezed.

    Returns:
    - List[T]: A list of squeezed dataclass objects, with duplicates removed.
    """
    # Pre-check: all items must be the same dataclass
    if len(all_class := {item.__class__.__name__ for item in items}) != 1:
        raise ValueError(f"All items must be of the same dataclass. Found classes: {all_class}")

    # Ff hashable, use set to remove duplicates
    if any(item.__hash__ is not None for item in items):
        return list(set(items))

    # Otherwise, initialize an empty list to store the squeezed mutant elements
    reduced_items: List[T] = []
    # Iterate through the list of mutants
    for item in items:
        # Check if the current mutant already exists in the squeezed list
        if item in reduced_items:
            # If it exists, skip the current mutant and continue to the next iteration
            continue
        # If it does not exist, add the current mutant to the squeezed list
        reduced_items.append(item)
    # Return the squeezed list of mutants
    return reduced_items


@contextlib.contextmanager
def convert_crlf_to_lf(input_file: str, base_dir: Optional[str] = None):
    """
    Context manager to convert a text file with CRLF line endings to LF
    and yield the path to the temporary file.

    If the input file does not contain any CRLF line endings, it yields None.

    Parameters:
    - input_file: str, path to the input text file with CRLF line endings.
    - base_dir: Optional[str], the base directory for the temporary file.

    Yields:
    - str, path to the newly created temporary file with LF line endings,
      or the original input file path if no CRLF line endings were found.

    """
    # Read the entire file content once
    try:
        with open(input_file, newline="", encoding="utf-8") as infile:
            content = infile.read()
    except OSError as e:
        raise OSError(f"Failed to read input file {input_file}: {e}") from e

    # Check if the file contains CRLF line endings
    if "\r\n" not in content:
        # If no CRLF line endings are found, yield the input file and exit early
        yield input_file
        return

    # Proceed to create a temporary file and convert if CRLF exists
    with tmpdir_manager(base_dir) as tmpdir:
        output_file_basename = os.path.basename(input_file)
        output_file = os.path.join(tmpdir, f"converted_file.{output_file_basename}")
        warnings.warn(UserWarning(f"Converting CRLF line endings to LF: {input_file} -> {output_file}"), stacklevel=2)

        # Write converted content to the temporary file
        with open(output_file, "w", newline="\n", encoding="utf-8") as outfile:
            outfile.write(content.replace("\r\n", "\n"))

        # Yield the path to the temporary file
        yield output_file
