"""
Example Application of RosettaLigand
"""

# pylint: disable=invalid-name
# pylint: disable=too-many-instance-attributes

import os
import warnings
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from RosettaPy import Rosetta, RosettaEnergyUnitAnalyser, RosettaScriptsVariableGroup
from RosettaPy.node import NodeClassType, NodeHintT, node_picker
from RosettaPy.node.native import Native
from RosettaPy.rosetta import IgnoreMissingFileWarning
from RosettaPy.utils import timing

script_dir = os.path.dirname(os.path.abspath(__file__))


@dataclass
class RosettaLigand:
    """
    Class for performing ligand docking using Rosetta.

    Attributes:
        pdb (str): Path to the Protein Data Bank (PDB) file. Default is an empty string.
        ligands (List[str]): List of ligand parameter files. Default is an empty list.
        save_dir (str): Directory to save outputs. Default is "tests/outputs".
        job_id (str): Identifier for the job. Default is "rosettaligand".
        cst (Optional[str]): Path to the constraint file. Default is None.
        nstruct (int): Number of structures to generate. Default is 1,000.
        box_size (int): Size of the docking box. Default is 30.
        move_distance (float): Distance to move during docking. Default is 0.5.
        gridwidth (int): Width of the grid. Default is 45.
        chain_id_for_dock (str): Chain identifier for docking. Default is "B".
        start_from_xyz (Optional[Tuple[float, float, float]]): Starting coordinates for docking. Default is None.
        node (NodeClassType): The node configuration for running the relaxation. Defaults to Native(nproc=4).
    """

    pdb: str = ""
    ligands: List[str] = field(default_factory=list)
    save_dir: str = "tests/outputs"
    job_id: str = "rosettaligand"
    cst: Optional[str] = None
    box_size: int = 30
    move_distance: float = 0.5
    gridwidth: int = 45
    chain_id_for_dock = "B"
    start_from_xyz: Optional[Tuple[float, float, float]] = None

    node: NodeClassType = field(default_factory=Native)

    @property
    def has_startfrom(self) -> bool:
        """
        Checks if the start_from_xyz attribute is valid.

        Returns:
            bool: True if start_from_xyz is a tuple of three floats, False otherwise.
        """
        return isinstance(self.start_from_xyz, tuple) and all(
            isinstance(c, float) for c in [self.start_from_xyz[0], self.start_from_xyz[1], self.start_from_xyz[2]]
        )

    @property
    def startfrom_mover(self) -> str:
        """
        Generates XML for the StartFrom mover if start_from_xyz is set.

        Returns:
            str: XML for the StartFrom mover or an empty string.
        """
        if self.has_startfrom:
            assert isinstance(self.start_from_xyz, tuple), "Start from xyz requires a tuple of 3 floats"
            return f"""<StartFrom name="startfrom" chain="{self.chain_id_for_dock}">
<Coordinates x="{self.start_from_xyz[0]}" y="{self.start_from_xyz[1]}" z="{self.start_from_xyz[2]}"/>
</StartFrom>"""
        return ""

    @property
    def startfrom_protocol(self) -> str:
        """
        Generates XML for the StartFrom protocol if start_from_xyz is set.

        Returns:
            str: XML for the StartFrom protocol or an empty string.
        """
        if self.has_startfrom:
            return '<Add mover_name="startfrom"/>'
        return ""

    @property
    def cst_mover(self) -> str:
        """
        Generates XML for the CST mover if a constraint file is provided.

        Returns:
            str: XML for the CST mover or an empty string.
        """
        if self.cst and os.path.isfile(self.cst):
            return f'<AddOrRemoveMatchCsts name="cstadd" cstfile="{self.cst}" cst_instruction="add_new"/>'
        return ""

    @property
    def cst_protocol(self) -> str:
        """
        Generates XML for the CST protocol if a constraint file is provided.

        Returns:
            str: XML for the CST protocol or an empty string.
        """
        if self.cst and os.path.isfile(self.cst):
            return '<Add mover_name="cstadd"/>'
        return ""

    def __post_init__(self):
        """
        Post-initialization actions including validation of PDB file path and setting absolute paths.
        """
        if not os.path.isfile(self.pdb):
            raise FileNotFoundError(f"PDB is given yet not found - {self.pdb}")
        self.instance = os.path.basename(self.pdb)[:-4]
        self.pdb = os.path.abspath(self.pdb)

        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

    @property
    def opts_ligand(self) -> List[str]:
        """
        Generates options for ligand parameters.

        Returns:
            List[str]: List of command-line options for ligand parameters.
        """
        ligands = []
        for _, l in enumerate(self.ligands):
            if not (isinstance(l, str) and l.endswith(".params")):
                warnings.warn(IgnoreMissingFileWarning(f"Invalid Parameter input for ligand - {l}"))
                continue

            if not os.path.isfile(l):
                warnings.warn(IgnoreMissingFileWarning(f"Ignore nofound ligand - {l}"))
                continue

            ligands.extend(["-extra_res_fa", os.path.abspath(l)])
        return ligands

    def dock(self, nstruct: int = 1_000) -> str:
        """
        Performs docking using Rosetta and returns the path to the best hit PDB file.

        Returns:
            str: Path to the best hit PDB file.
        """
        docking_dir = os.path.join(self.save_dir, self.job_id, "docking")

        opts = [
            "-parser:protocol",
            f"{script_dir}/deps/rosettaligand/xmls/rosetta_ligand.xml",
            "-out:prefix",
            f"{self.instance}_{self.job_id}",
            "-in:file:s",
            self.pdb,
            RosettaScriptsVariableGroup.from_dict(
                {
                    "box_size": str(self.box_size),
                    "move_distance": str(self.move_distance),
                    "gridwidth": str(self.gridwidth),
                    "chain_id_for_dock": self.chain_id_for_dock,
                    "startfrom_mover": self.startfrom_mover,
                    "startfrom_protocol": self.startfrom_protocol,
                    "cst_mover": self.cst_mover,
                    "cst_protocol": self.cst_protocol,
                }
            ),
        ] + self.opts_ligand

        rosetta = Rosetta(
            bin="rosetta_scripts",
            flags=[os.path.join(script_dir, "deps/rosettaligand/flags/rosetta_ligand.flags")],
            opts=opts,
            output_dir=docking_dir,
            save_all_together=False,
            job_id=f"{self.instance}_{self.job_id}",
            run_node=self.node,
        )

        with timing("RosettaLigand: Docking"):
            rosetta.run(nstruct=nstruct)

        analyser = RosettaEnergyUnitAnalyser(score_file=rosetta.output_scorefile_dir)
        best_hit = analyser.best_decoy
        pdb_path = os.path.join(rosetta.output_pdb_dir, f'{best_hit["decoy"]}.pdb')

        print("Analysis of the best decoy:")
        print("-" * 79)
        print(analyser.df.sort_values(by=analyser.score_term))

        print("-" * 79)

        print(f'Best Hit on this RosettaLigand run: {best_hit["decoy"]} - {best_hit["score"]}: {pdb_path}')

        return pdb_path


def main(
    startfrom=None,
    node_hint: Optional[NodeHintT] = None,
):
    """
    Test
    """
    if node_hint == "docker":
        node_hint = "docker_mpi"

    docker_label = f"_{node_hint}" if node_hint else ""
    runner = RosettaLigand(
        pdb="tests/data/6zcy_lig.pdb",
        ligands=["tests/data/lig/lig.fa.params"],
        start_from_xyz=startfrom,
        job_id="rosettaligand" + docker_label if startfrom is None else "rosettaligand_startfrom" + docker_label,
        node=node_picker(node_type=node_hint),
    )

    runner.dock(
        nstruct=4,
    )


if __name__ == "__main__":
    main()
