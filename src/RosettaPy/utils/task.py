"""
Task module for Rosetta
"""

import copy
import os
import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional


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
        variables = [RosettaScriptsVariable(
            k=k, v=str(v)) for k, v in var_pair.items()]
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
                warnings.warn(RosettaScriptVariableNotExistWarning(
                    f"Variable {k} not in Rosetta Script content."))
                continue
            xml_content_copy = xml_content_copy.replace(f"%%{k}%%", v)

        return xml_content_copy


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
