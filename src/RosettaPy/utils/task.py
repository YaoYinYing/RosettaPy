"""
Task module for Rosetta
"""

# Disable pylint for with-context manager for subprocss.Popen for unit test mocks.
# pylint: disable=consider-using-with

import copy
import os
import subprocess
import warnings
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Union

import tree

from RosettaPy.utils.tools import isolate


class RosettaScriptVariableWarning(RuntimeWarning):
    """
    Warning for RosettaScriptsVariable.
    """


class RosettaScriptVariableNotExistWarning(RosettaScriptVariableWarning):
    """
    Warning for RosettaScriptsVariable when the variable does not exist in Rosetta Script content.
    """


class IgnoreMissingFileWarning(UserWarning):
    """
    Warning for IgnoreMissingFile.
    """


@dataclass(frozen=True)
class RosettaScriptsVariable:
    """
    Represents a single RosettaScripts variable, consisting of a key and a value.
    """

    k: str
    v: str

    @property
    def aslist(self) -> List[str]:
        """
        Converts the configuration into a list format suitable for command-line arguments.

        Returns:
            List[str]: A list containing the configuration in command-line argument format.
        """
        return [
            "-parser:script_vars",
            f"{self.k}={self.v}",
        ]


@dataclass(frozen=True)
class RosettaScriptsVariableGroup:
    """
    Represents a group of RosettaScripts variables, providing functionalities to manage these variables collectively.
    """

    variables: List[RosettaScriptsVariable]

    @property
    def empty(self):
        """
        Checks if the list of variables in the group is empty.

        Returns:
            bool: True if the list of variables is empty; otherwise, False.
        """
        return len(self.variables) == 0

    @property
    def aslonglist(self) -> List[str]:
        """
        Flattens the list of variables into a single list of strings.

        Returns:
            List[str]: A flattened list containing all elements from the variables.
        """
        return [i for v in self.variables for i in v.aslist]

    @property
    def asdict(self) -> Dict[str, str]:
        """
        Converts the list of variables into a dictionary.

        Returns:
            Dict[str, str]: A dictionary with variable keys and their corresponding values.
        """
        return {rsv.k: rsv.v for rsv in self.variables}

    @classmethod
    def from_dict(cls, var_pair: Dict[str, str]) -> "RosettaScriptsVariableGroup":
        """
        Creates an instance of RosettaScriptsVariableGroup from a dictionary of variable pairs.

        Args:
            var_pair (Dict[str, str]): A dictionary representing variable pairs.

        Returns:
            RosettaScriptsVariableGroup: An instance of RosettaScriptsVariableGroup.

        Raises:
            ValueError: If the created instance has no variables.
        """
        variables = [RosettaScriptsVariable(k=k, v=str(v)) for k, v in var_pair.items()]
        instance = cls(variables)
        if instance.empty:
            raise ValueError()
        return instance

    def apply_to_xml_content(self, xml_content: str):
        """
        Replaces placeholders in the XML content with actual variable values.

        Args:
            xml_content (str): The original XML content with placeholders.

        Returns:
            str: The XML content with placeholders replaced by variable values.

        Raises:
            RosettaScriptVariableNotExistWarning: If a placeholder for a variable does not exist in the XML content.
        """
        xml_content_copy = copy.deepcopy(xml_content)
        for k, v in self.asdict.items():
            if f"%%{k}%%" not in xml_content_copy:
                warnings.warn(RosettaScriptVariableNotExistWarning(f"Variable {k} not in Rosetta Script content."))
                continue
            xml_content_copy = xml_content_copy.replace(f"%%{k}%%", v)

        return xml_content_copy


def expand_input_dict(d: Dict[str, Union[str, RosettaScriptsVariableGroup]]) -> List[str]:
    """
    Expands a dictionary containing strings and variable groups into a flat list.

    :param d: Dictionary with keys and values that can be either strings or variable groups.
    :return: A list of expanded key-value pairs.
    """

    opt_list = [[k, v] if not isinstance(v, RosettaScriptsVariableGroup) else v.aslonglist for k, v in d.items()]

    return tree.flatten(opt_list)


@dataclass
class RosettaCmdTask:
    """
    RosettaCmdTask represents a command-line task for running Rosetta commands.
    """

    cmd: List[str]  # The command list for the task
    task_label: Optional[str] = None  # The label of the task, optional
    base_dir: Optional[str] = None  # a base directory for run local task

    @property
    def runtime_dir(self) -> str:  # The directory for storing runtime output
        """
        Determine the runtime directory for the task.

        If the task_label is not provided, it returns the current working directory or the base directory as specified.
        If the task_label is provided, it joins the base directory (or the current working directory
        if base_dir is not set) with the task_label to form the runtime directory.

        Returns:
            str: The runtime directory path.
        """
        if not self.task_label:
            # Return the current working directory or the base directory based on the configuration
            return os.getcwd() if not self.base_dir else self.base_dir

        if self.base_dir is None:
            # Warn the user if base_dir is not set and fix it to the current working directory
            warnings.warn("Fixing base_dir to curdir")
            self.base_dir = os.getcwd()

        # Return the runtime directory composed of base_dir and task_label
        return os.path.join(self.base_dir, self.task_label)


def _isolated_execute(task: RosettaCmdTask, func: Callable[[RosettaCmdTask], RosettaCmdTask]) -> RosettaCmdTask:
    """
    Executes a given task in an isolated environment.

    This method is used to run a specific function within an isolated context,
    ensuring that the execution of the task is separated from the global environment.
    It is typically used for scenarios requiring a clean or restricted execution context.

    Parameters:
    - task (RosettaCmdTask): A task object containing necessary information.
    - func (Callable[[RosettaCmdTask], RosettaCmdTask]): A function that takes and returns a RosettaCmdTask object,
    which will be executed within the isolated environment.

    Returns:
    - RosettaCmdTask: The task object after execution.

    Raises:
    - ValueError: If the task label (task_label) or base directory (base_dir) is missing.
    """
    # Check if the task label exists; raise an exception if it does not
    if not task.task_label:
        raise ValueError("Task label is required when executing the command in isolated mode.")

    # Check if the base directory exists; raise an exception if it does not
    if not task.base_dir:
        raise ValueError("Base directory is required when executing the command in isolated mode.")

    with isolate(save_to=task.runtime_dir):
        return func(task)


def execute(task: RosettaCmdTask, func: Optional[Callable[[RosettaCmdTask], RosettaCmdTask]] = None) -> RosettaCmdTask:
    """
    Executes the given task with support for both non-isolated and isolated execution modes,
    which can be customized via the provided function argument.

    :param task: The task object to be executed, encapsulating the specific content to run.
    :param func: An optional parameter specifying the function to execute the task. If not provided,
                    defaults to a non-isolated execution mode.
    :return: The task object after execution.

    Notes:
    - If no task label (task_label) is specified, the task is executed directly using the specified function.
    - Otherwise, the task is executed in an isolated mode.
    - If the function argument func is not provided, a default non-isolated execution mode is used.
    """
    # Use the default non-isolated execution mode if no function is provided
    if func is None:
        func = _non_isolated_execute
    if not task.task_label:
        return func(task)
    return _isolated_execute(task, func)


def _non_isolated_execute(task: RosettaCmdTask) -> RosettaCmdTask:
    """
    Executes a command and handles its output and errors.

    :param task: The command task to execute, containing the command and its configuration.
    :return: Returns the command task object after execution, including the command execution results.
    """
    # Use subprocess.Popen to execute the command, redirecting output and setting encoding to UTF-8.
    process = subprocess.Popen(
        task.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf-8"
    )

    # Print command execution information.
    print(f'Launching command: `{" ".join(task.cmd)}`')
    # Communicate to get the command's output and error.
    stdout, stderr = process.communicate()
    # Wait for the command to complete and get the return code.
    retcode = process.wait()

    if retcode:
        # If the command fails, print the failure message and raise an exception.
        print(f"Command failed with return code {retcode}")
        print(stdout)
        warnings.warn(RuntimeWarning(stderr))
        raise RuntimeError(
            f"Command failed with return code {retcode}.\n"
            f"Command: `{' '.join(task.cmd)}`\n"
            f"PWD: {os.getcwd()}\n"
            f"Stdout: {stdout}"
            f"Stderr: {stderr}"
        )

    return task
