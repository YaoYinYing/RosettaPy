"""
Utility functions for creating mounts via filesystems
"""

# pylint: disable=too-few-public-methods

import os
import warnings
from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Type, Union

from docker import types

from RosettaPy.utils.escape import print_diff, render
from RosettaPy.utils.task import RosettaCmdTask


class Mounter(ABC):
    """
    A basic class for defining a class that can mount files and directories.

    This class provides a template for subclasses that specifically implement how to mount a source to a target.

    Attributes:
        source (str): The path of the source to mount.
        target (str): The path where the source will be mounted.

    Attributes for implementation by subclasses:
        mount (Any): To be defined by subclasses, representing the mount operation or its result.
        mounted (Any): To be defined by subclasses, representing the state or result after mounting.
    """

    source: str
    target: str

    mount: Any
    mounted: Any

    @classmethod
    @abstractmethod
    def from_path(cls, path_to_mount: str) -> "Mounter":
        """
        Abstract class method, intended for subclasses to implement, creating and returning an instance of the
        subclass based on the given path.

        This method indicates that subclasses should support creating instances by passing the path of the item
        to mount, but the specific implementation details are left to the subclass to define.

        Parameters:
            path_to_mount (str): The path of the item to mount.

        Returns:
            Mounter: An instance of a subclass of Mounter, capable of mounting the specified path.
        """


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


def _process_xml_fragment(script_vars_v: str, mounter: Type[Mounter]) -> Tuple[str, List[Mounter]]:
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
            mount_obj = mounter.from_path(vf)
            mounts.append(mount_obj)
            # Add the mounted path representation to vf_list
            vf_list.append(mount_obj.mounted)
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


def _mount_from_xml_variable(_cmd: str, mounter: Type[Mounter]) -> Tuple[str, List[Mounter]]:
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
        mount_obj = mounter.from_path(script_vars_v)
        # Return the variable assignment with the mounted path and a list containing the mount object
        return f"{script_vars[0]}={mount_obj.mounted}", [mount_obj]

    # Handling of XML file blocks with file inputs
    # Example: '<AddOrRemoveMatchCsts name="cstadd" cstfile="/my/example.cst" cst_instruction="add_new"/>'
    if " " in script_vars_v and "<" in script_vars_v:  # Indicates an XML fragment
        # If the value appears to be an XML fragment, process it using the _process_xml_fragment method
        joined_vf, mounts = _process_xml_fragment(script_vars_v, mounter=mounter)
        # Return the variable assignment with the processed XML fragment and the list of mount objects
        return f"{script_vars[0]}={joined_vf}", mounts

    # If the value does not match any of the above conditions, return the original command and an empty list
    return _cmd, []


def mount(input_task: RosettaCmdTask, mounter: Type[Mounter]) -> Tuple[RosettaCmdTask, Union[List[types.Mount], None]]:
    """
    Prepares the mounting environment for a single task.

    This function is responsible for mounting files and directories required by the given task.

    Parameters:
        input_task (RosettaCmdTask): The task object containing the command and runtime directory information.

    Returns:
        Tuple[RosettaCmdTask, List[types.Mount]]: A tuple containing the updated task object
        with mounted paths and a list of mounts.
    """

    all_mounts: List[Mounter] = []
    updated_cmd_with_mounts = []

    for i, cmd_segment in enumerate(input_task.cmd):
        try:
            # Handle general options
            if cmd_segment.startswith("-"):
                updated_cmd_with_mounts.append(cmd_segment)
                continue

            # Handle option input
            if os.path.isfile(cmd_segment) or os.path.isdir(cmd_segment):
                mount_obj = mounter.from_path(cmd_segment)
                all_mounts.append(mount_obj)
                updated_cmd_with_mounts.append(mount_obj.mounted)
                continue

            # Handle Rosetta flag files
            if cmd_segment.startswith("@"):
                mount_obj = mounter.from_path(cmd_segment[1:])
                all_mounts.append(mount_obj)
                updated_cmd_with_mounts.append(f"@{mount_obj.mounted}")
                continue

            # Handle Rosetta Scripts variables
            if "=" in cmd_segment and input_task.cmd[i - 1] == "-parser:script_vars":
                updated_cmd_segment, partial_mounts = _mount_from_xml_variable(cmd_segment, mounter=mounter)
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

    mounted_runtime_dir = mounter.from_path(input_task.runtime_dir)
    all_mounts.append(mounted_runtime_dir)

    mounted_task = RosettaCmdTask(
        cmd=updated_cmd_with_mounts,
        base_dir=mounted_runtime_dir.mounted,
    )

    if hasattr(mounter, "squeeze"):
        return mounted_task, (mounter.squeeze([mount.mount for mount in all_mounts]))  # type: ignore

    return mounted_task, None
