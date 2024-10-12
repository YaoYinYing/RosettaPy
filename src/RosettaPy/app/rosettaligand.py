import os
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
import warnings
from RosettaPy import Rosetta, RosettaScriptsVariableGroup, RosettaEnergyUnitAnalyser
from RosettaPy.rosetta import IgnoreMissingFileWarning
from RosettaPy.utils import timing
from RosettaPy.node import RosettaContainer


script_dir = os.path.dirname(os.path.abspath(__file__))


@dataclass
class RosettaLigand:
    pdb: str = ""
    ligands: List[str] = field(default_factory=list)

    save_dir: str = "tests/outputs"
    job_id: str = "rosettaligand"

    cst: Optional[str] = None
    nstruct: int = 1_000

    box_size: int = 30
    move_distance: float = 0.5
    gridwidth: int = 45
    chain_id_for_dock = "B"

    start_from_xyz: Optional[Tuple[float, float, float]] = None

    # internal
    startfrom_mover = ""
    startfrom_protocol = ""

    cst_mover = ""
    cst_protocol = ""

    def __post_init__(self):
        if not os.path.isfile(self.pdb):
            raise FileNotFoundError(f"PDB is given yet not found - {self.pdb}")
        self.instance = os.path.basename(self.pdb)[:-4]
        self.pdb = os.path.abspath(self.pdb)

        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

        if isinstance(self.start_from_xyz, tuple) and all(
            isinstance(c, float) for c in [self.start_from_xyz[0], self.start_from_xyz[1], self.start_from_xyz[2]]
        ):
            self.startfrom_mover = f'<StartFrom name="startfrom" chain="{self.chain_id_for_dock}"><Coordinates x="{self.start_from_xyz[0]}" y="{self.start_from_xyz[1]}" z="{self.start_from_xyz[2]}"/></StartFrom>'
            self.startfrom_protocol = '<Add mover_name="startfrom"/>'

        if self.cst and os.path.isfile(self.cst):
            self.cst_mover = f'<AddOrRemoveMatchCsts name="cstadd" cstfile="{self.cst}" cst_instruction="add_new"/>'
            self.cst_protocol = '<Add mover_name="cstadd"/>'

    @property
    def opts_ligand(self) -> List[str]:
        ligands = []
        for i, l in enumerate(self.ligands):
            if isinstance(l, str) and l.endswith(".params"):
                if not os.path.isfile(l):
                    warnings.warn(IgnoreMissingFileWarning(f"Ignore Ligand - {l}"))
                ligands.extend(["-extra_res_fa", os.path.abspath(l)])
        return ligands

    def dock(self) -> str:
        docking_dir = os.path.join(self.save_dir, self.job_id, "docking")

        rosetta = Rosetta(
            bin="rosetta_scripts",
            flags=[os.path.join(script_dir, "deps/rosettaligand/flags/rosetta_ligand.flags")],
            opts=[
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
            ]
            + self.opts_ligand,
            output_dir=docking_dir,
            save_all_together=False,
            job_id=f"{self.instance}_{self.job_id}",
            # mpi_node=MPI_node(nproc=os.cpu_count()),
            # run_node=RosettaContainer(image="dockerhub.yaoyy.moe/rosettacommons/rosetta:mpi"),
        )

        with timing("RosettaLigand: Docking"):
            rosetta.run(nstruct=self.nstruct)

        analyser = RosettaEnergyUnitAnalyser(score_file=rosetta.output_scorefile_dir)
        best_hit = analyser.best_decoy
        pdb_path = os.path.join(rosetta.output_pdb_dir, f'{best_hit["decoy"]}.pdb')

        print("Analysis of the best decoy:")
        print("-" * 79)
        print(analyser.df.sort_values(by=analyser.score_term))

        print("-" * 79)

        print(f'Best Hit on this RosettaLigand run: {best_hit["decoy"]} - {best_hit["score"]}: {pdb_path}')

        return pdb_path


def main(startfrom=None):
    runner = RosettaLigand(
        pdb="tests/data/6zcy_lig.pdb",
        ligands=["tests/data/lig/lig.fa.params"],
        nstruct=4,
        start_from_xyz=startfrom,
        job_id="rosettaligand" if startfrom is None else "rosettaligand_startfrom",
    )

    runner.dock()


if __name__ == "__main__":
    main()
