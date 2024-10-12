import copy
from dataclasses import dataclass
import os
from typing import Dict, List, Optional
import warnings


class RosettaScriptVariableWarning(RuntimeWarning): ...


class RosettaScriptVariableNotExistWarning(RosettaScriptVariableWarning): ...


class IgnoreMissingFileWarning(UserWarning): ...


@dataclass(frozen=True)
class RosettaScriptsVariable:
    k: str
    v: str

    @property
    def aslist(self) -> List[str]:
        return [
            "-parser:script_vars",
            f"{self.k}={self.v}",
        ]


@dataclass(frozen=True)
class RosettaScriptsVariableGroup:
    variables: List[RosettaScriptsVariable]

    @property
    def empty(self):
        return len(self.variables) == 0

    @property
    def aslonglist(self) -> List[str]:
        return [i for v in self.variables for i in v.aslist]

    @property
    def asdict(self) -> Dict[str, str]:
        return {rsv.k: rsv.v for rsv in self.variables}

    @classmethod
    def from_dict(cls, var_pair: Dict[str, str]) -> "RosettaScriptsVariableGroup":
        variables = [RosettaScriptsVariable(k=k, v=str(v)) for k, v in var_pair.items()]
        instance = cls(variables)
        if instance.empty:
            raise ValueError()
        return instance

    def apply_to_xml_content(self, xml_content: str):
        xml_content_copy = copy.deepcopy(xml_content)
        for k, v in self.asdict.items():
            if f"%%{k}%%" not in xml_content_copy:
                warnings.warn(RosettaScriptVariableNotExistWarning(f"Variable {k} not in Rosetta Script content."))
                continue
            xml_content_copy = xml_content_copy.replace(f"%%{k}%%", v)

        return xml_content_copy


@dataclass
class RosettaCmdTask:
    cmd: List[str]  # The command list for the task
    task_label: Optional[str] = None  # The label of the task, optional
    base_dir: Optional[str] = None  # a base directory for run local task

    @property
    def runtime_dir(self) -> str:  # The directory for storing runtime output
        """
        Determine the runtime directory for the task.

        If the task_label is not provided, it returns the current working directory or the base directory as specified.
        If the task_label is provided, it joins the base directory (or the current working directory if base_dir is not set)
        with the task_label to form the runtime directory.

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
