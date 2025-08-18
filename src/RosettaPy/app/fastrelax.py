"""
Example Application of FastRelax.
"""

import os
import warnings
from typing import Any, List, Mapping, Optional, Sequence, Union

from RosettaPy import Rosetta, RosettaEnergyUnitAnalyser, RosettaScriptsVariableGroup
from RosettaPy.app.abc import RosettaAppBase
from RosettaPy.node import NodeHintT
from RosettaPy.utils import timing
from RosettaPy.utils.repository import partial_clone

script_dir = os.path.dirname(os.path.abspath(__file__))


class RelaxScriptInputWarning(UserWarning):
    """Warning of Relax script input format"""


def get_relax_scripts_from_db(script_name: str) -> str:
    """
    Gets the full path of the relaxation script from the database.

    Args:
        script_name (str): The name of the relaxation script.

    Returns:
        str: The full name of the relaxation script without the .txt extension.

    Raises:
        RuntimeError: If the relaxation script is not found or ROSETTA3_DB is not set.

    References:
    ERROR: [ERROR] relaxscript argument /usr/local/database/MonomerRelax2019.txt should not have extensions.
    Additionally, /usr/local/database/MonomerRelax2019 does not appear to be a valid script name.
    Please look at main/database/sampling/relax_scripts/ or the wiki for valid names.
    """
    # Check if the script name already exists in the file system
    if os.path.exists(script_name):
        return os.path.basename(script_name).replace(".txt", "")

    # Remove .txt extension if present
    if script_name.endswith(".txt"):
        script_name = script_name[:-4]

    # Get the ROSETTA3_DB environment variable
    rosetta3_db_path = os.environ.get("ROSETTA3_DB")
    if not rosetta3_db_path:

        rosetta3_db_path = partial_clone(
            repo_url="https://github.com/RosettaCommons/rosetta",
            target_dir="rosetta_db_clone",
            subdirectory_as_env="database",
            subdirectory_to_clone="database/sampling/relax_scripts",
            env_variable="ROSETTA3_DB",
        )
        print(f'ROSETTA3_DB={os.environ.get("ROSETTA3_DB")}')

    # List all available relaxation scripts in the database
    all_scripts = [
        os.path.join(rosetta3_db_path, f[:-4])
        for f in os.listdir(f"{rosetta3_db_path}/sampling/relax_scripts/")
        if f.endswith(".txt") and f != "README.txt" and "dualspace" not in f
    ]

    # Check if the requested script is available
    for script in all_scripts:
        if os.path.basename(script) == script_name:
            return script_name

    # Raise an error if the script is not found
    raise RuntimeError(
        f"No such relax script - {script_name}, "
        f"All available scripts: {[os.path.basename(f).replace('.txt', '') for f in all_scripts]}"
    )


class FastRelax(RosettaAppBase):
    """
    A class for performing fast relaxation on protein structures using Rosetta.

    Attributes:
        pdb (str): The path to the PDB file of the protein structure to be relaxed.
        save_dir (str, optional): The directory to save the results. Defaults to "tests/outputs".
        job_id (str, optional): The job identifier. Defaults to "fastrelax".
        relax_script (str, optional): The relaxation script to use. Defaults to "MonomerRelax2019".
        dualspace (bool, optional): Whether to use dualspace mode. Defaults to False.
        node (NodeClassType): The node configuration for running the relaxation. Defaults to Native(nproc=4).
    """

    def __init__(
        self,
        pdb: str,
        job_id: str = "fastrelax",
        save_dir: str = "tests/outputs",
        relax_script: str = "MonomerRelax2019",
        dualspace: bool = False,
        user_opts: Optional[List] = None,
        node_hint: NodeHintT = "native",
        node_config: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(job_id, save_dir, user_opts, node_hint, node_config, **kwargs)

        self.pdb = pdb
        self.relax_script = relax_script
        self.dualspace = dualspace

        if not os.path.isfile(self.pdb):
            raise FileNotFoundError(f"PDB is given yet not found - {self.pdb}")
        self.instance = os.path.basename(self.pdb)[:-4]
        self.pdb = os.path.abspath(self.pdb)

        if self.relax_script.endswith(".txt"):
            warnings.warn(RelaxScriptInputWarning("Relaxscript argument should not have extensions."))

        self.relax_script = get_relax_scripts_from_db(self.relax_script)

    def run(
        self,
        nstruct: int = 8,
        default_repeats: int = 15,
        opts: Optional[Sequence[Union[str, RosettaScriptsVariableGroup]]] = None,
    ) -> RosettaEnergyUnitAnalyser:
        """
        Runs the fast relaxation process using the specified parameters.

        Args:
            nstruct (int, optional): The number of structures to generate. Defaults to 8.
            default_repeats (int, optional): The default number of repeats for relaxation. Defaults to 15.

        Returns:
            RosettaEnergyUnitAnalyser: An object for analyzing the energy units of the generated structures.
        """
        if not opts:
            opts = []
        # Configure and run Rosetta for fast relaxation
        rosetta = Rosetta(
            bin="relax",
            opts=[
                "-in:file:s",
                os.path.abspath(self.pdb),
                "-relax:script",
                self.relax_script,
                "-relax:default_repeats",
                str(default_repeats),
                "-out:prefix",
                f"{self.instance}_fastrelax_",
                "-out:file:scorefile",
                f"{self.instance}_fastrelax.sc",
                "-score:weights",
                "ref2015_cart" if self.dualspace else "ref2015",
                "-relax:dualspace",
                "true" if self.dualspace else "false",
            ]
            + list(opts)
            + list(self.user_opts),
            save_all_together=True,
            output_dir=os.path.join(self.save_dir, self.job_id),
            job_id=f"fastrelax_{self.instance}_{os.path.basename(self.relax_script)}",
            run_node=self.node,
        )

        with timing("FastRelax"):
            rosetta.run(nstruct=nstruct)

        return RosettaEnergyUnitAnalyser(rosetta.output_scorefile_dir)


def main(
    dualspace: bool = False,
    node_hint: NodeHintT = "native",
):
    """
    Test
    """
    docker_label = f"_{node_hint}" if node_hint else ""
    if dualspace:
        scorer = FastRelax(
            pdb="tests/data/3fap_hf3_A.pdb",
            dualspace=True,
            job_id="fastrelax_dualspace" + docker_label,
            node_hint=node_hint,
        )
    else:
        scorer = FastRelax(
            pdb="tests/data/3fap_hf3_A.pdb",
            node_hint=node_hint,
            job_id="fast_relax" + docker_label,
        )

    analyser = scorer.run(
        nstruct=1,
        default_repeats=1,
    )
    best_hit = analyser.best_decoy

    print("Analysis of the best decoy:")
    print("-" * 79)
    print(analyser.df.sort_values(by=analyser.score_term))

    print("-" * 79)

    print(f'Best Hit on this FastRelax run: {best_hit["decoy"]} - {best_hit["score"]}')


if __name__ == "__main__":
    main()
