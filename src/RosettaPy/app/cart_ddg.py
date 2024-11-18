"""
Example Application of Cartesian ddG
"""

# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments


import os
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from RosettaPy import Rosetta, RosettaCartesianddGAnalyser, RosettaEnergyUnitAnalyser
from RosettaPy.common.mutation import Mutant, mutpdb2mutfile
from RosettaPy.node import NodeClassType, NodeHintT, node_picker
from RosettaPy.node.native import Native
from RosettaPy.utils import timing

script_dir = os.path.dirname(os.path.abspath(__file__))


@dataclass
class CartesianDDG:
    """
    A class for performing Cartesian ddG (delta delta G) calculations on protein structures.

    Attributes:
        pdb (str): The path to the input PDB file.
        save_dir (str, optional): The directory to save the output results. Defaults to "tests/outputs".
        job_id (str, optional): The job identifier. Defaults to "cart_ddg".

        node (NodeClassType): The node configuration for running the relaxation. Defaults to Native(nproc=4).
    """

    pdb: str
    save_dir: str = "tests/outputs"
    job_id: str = "cart_ddg"

    node: NodeClassType = field(default_factory=Native)

    def __post_init__(self):
        """
        Post-initialization method to perform checks and set up the working directory.

        Raises:
            FileNotFoundError: If the specified PDB file does not exist.
        """
        if not os.path.isfile(self.pdb):
            raise FileNotFoundError(f"PDB is given yet not found - {self.pdb}")
        self.instance = os.path.basename(self.pdb)[:-4]
        self.pdb = os.path.abspath(self.pdb)

        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

    def relax(self, nstruct_relax: int = 30):
        """
        Method to perform structure relaxation using Rosetta.
        Args:
            nstruct_relax (int, optional): The number of relaxed structures to generate. Defaults to 30.

        Returns:
            str: The path to the best relaxed PDB file.
        """
        rosetta = Rosetta(
            bin="relax",
            flags=[f"{script_dir}/deps/cart_ddg/flags/ddG_relax.flag"],
            opts=[
                "-in:file:s",
                os.path.abspath(self.pdb),
                "-relax:script",
                f"{script_dir}/deps/cart_ddg/flags/cart2.script",
                "-out:prefix",
                f"{self.instance}_relax_",
                "-out:file:scorefile",
                f"{self.instance}_relax.sc",
            ],
            save_all_together=True,
            output_dir=os.path.join(self.save_dir, f"{self.job_id}_relax"),
            job_id=f"cart_ddg_relax_{self.instance}",
            run_node=self.node,
        )

        with timing("Cartesian ddG: Relax"):
            rosetta.run(nstruct=nstruct_relax)

        analyser = RosettaEnergyUnitAnalyser(rosetta.output_scorefile_dir)
        analyser.top(10)
        top_pdb = analyser.best_decoy

        print(f"best_decoy: {top_pdb['decoy']} - {top_pdb['score']}")
        pdb_path = os.path.join(rosetta.output_pdb_dir, f"{top_pdb['decoy']}.pdb")

        return pdb_path

    def cartesian_ddg(
        self, input_pdb, mutfiles: List[str], mutants: List[Mutant], use_legacy: bool = False, ddg_iteration: int = 3
    ):
        """
        Method to perform Cartesian ddG calculation using Rosetta.

        Args:
            input_pdb (str): The path to the input PDB file for ddG calculation.
            mutfiles (List[str]): A list of paths to files containing mutant information.
            mutants (List[Mutant]): A list of Mutant objects representing the mutants to be analyzed.
            use_legacy (bool, optional): Whether to use the legacy method for ddG calculation. Defaults to False.
            ddg_iteration (int, optional): The number of iterations for the ddG calculation. Defaults to 3.

        Returns:
            pd.DataFrame: A dataframe containing the ddG calculation results for each mutant.
        """
        # Initialize Rosetta for Cartesian ddG calculation with specified options and settings
        rosetta = Rosetta(
            bin="cartesian_ddg",
            flags=[f"{script_dir}/deps/cart_ddg/flags/ddG.options"],
            opts=[
                "-in:file:s",
                os.path.abspath(input_pdb),
                "-out:prefix",
                f"{self.instance}_cart_ddg_",
                "-out:file:scorefile",
                f"{self.instance}_cart_ddg.sc",
                "-ddg:json",
                "true",
                "-ddg::legacy",
                "true" if use_legacy else "false",
                "-ddg:iterations",
                str(ddg_iteration),
                "-ddg:output_dir",
                os.path.join(self.save_dir, self.job_id),
            ],
            isolation=True,
            save_all_together=True,
            output_dir=os.path.join(self.save_dir, f"{self.job_id}_cart_ddg"),
            job_id=f"cart_ddg_run_{self.instance}",
            run_node=self.node,
        )

        # Generate a list of tasks, each containing the path to a mutfile and the corresponding output file name
        tasks = [{"-ddg:mut_file": mf, "-ddg:out": f"{m.raw_mutant_id}.out"} for mf, m in zip(mutfiles, mutants)]

        # Execute the Cartesian ddG calculation tasks and measure the execution time
        with timing("Cartesian ddG: Evaluation"):
            task_list = rosetta.run(inputs=tasks)  # type: ignore

        # Parse the ddG calculation results for each task and combine them into a single DataFrame
        return pd.concat(
            [
                RosettaCartesianddGAnalyser(runtime_dir=task.runtime_dir, recursive=True).parse_ddg_files()
                for task in task_list
            ]
        )


def main(
    legacy: bool = False,
    node_hint: Optional[NodeHintT] = None,
):
    """
    Test
    """

    docker_label = f"_{node_hint}" if node_hint else ""

    mutant_pdb_dir = "tests/data/designed/pross/"

    cart_ddg = CartesianDDG(
        pdb="tests/data/3fap_hf3_A_short.pdb",
        job_id="cart_ddg" + docker_label if not legacy else "cart_ddg_legacy" + docker_label,
        node=node_picker(node_type=node_hint),
    )

    mutfiles, mutants = mutpdb2mutfile(
        wt_pdb=cart_ddg.pdb,
        mutant_pdb_dir=mutant_pdb_dir,
        mutfile_save_dir=os.path.join(cart_ddg.save_dir, cart_ddg.job_id, "mutfiles"),
    )

    pdb_path = cart_ddg.relax(
        nstruct_relax=4,
    )
    df = cart_ddg.cartesian_ddg(
        input_pdb=pdb_path,
        mutfiles=mutfiles,
        mutants=mutants,
        use_legacy=legacy,
    )

    print(df)


if __name__ == "__main__":
    main(False)
