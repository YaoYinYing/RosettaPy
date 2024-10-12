import os
from typing import List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
from RosettaPy import Rosetta, RosettaEnergyUnitAnalyser, RosettaCartesianddGAnalyser
from RosettaPy.common.mutation import Mutant, mutants2mutfile
from RosettaPy.node import RosettaContainer
from RosettaPy.utils import timing

script_dir = os.path.dirname(os.path.abspath(__file__))


@dataclass
class CartesianDDG:
    pdb: str
    save_dir: str = "tests/outputs"
    job_id: str = "cart_ddg"

    nstruct_relax: int = 30
    use_legacy: bool = False
    ddg_iteration: int = 3

    mutant_pdb_dir = "tests/data/designed/pross/"

    def __post_init__(self):
        if not os.path.isfile(self.pdb):
            raise FileNotFoundError(f"PDB is given yet not found - {self.pdb}")
        self.instance = os.path.basename(self.pdb)[:-4]
        self.pdb = os.path.abspath(self.pdb)

        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

    def relax(self):
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
            # run_node=RosettaContainer(image="dockerhub.yaoyy.moe/rosettacommons/rosetta:mpi"),
        )

        with timing("Cartesian ddG: Relax"):
            rosetta.run(nstruct=self.nstruct_relax)

        analyser = RosettaEnergyUnitAnalyser(rosetta.output_scorefile_dir)
        analyser.top(10)
        top_pdb = analyser.best_decoy

        print(f"best_decoy: {top_pdb['decoy']} - {top_pdb['score']}")
        pdb_path = os.path.join(rosetta.output_pdb_dir, f"{top_pdb['decoy']}.pdb")

        return pdb_path

    def cartesian_ddg(self, input_pdb):
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
                "true" if self.use_legacy else "false",
                "-ddg:iterations",
                str(self.ddg_iteration),
                "-ddg:output_dir",
                os.path.join(self.save_dir, self.job_id),
            ],
            isolation=True,
            save_all_together=True,
            output_dir=os.path.join(self.save_dir, f"{self.job_id}_cart_ddg"),
            job_id=f"cart_ddg_run_{self.instance}",
            # run_node=RosettaContainer(image="dockerhub.yaoyy.moe/rosettacommons/rosetta:mpi", prohibit_mpi=True),
        )

        mutfiles, mutants = self.mut2mutfile()
        tasks = [{"-ddg:mut_file": mf, "-ddg:out": f"{m.raw_mutant_id}.out"} for mf, m in zip(mutfiles, mutants)]

        with timing("Cartesian ddG: Evaluation"):
            task_list = rosetta.run(inputs=tasks)  # type: ignore

        return pd.concat(
            [
                RosettaCartesianddGAnalyser(runtime_dir=task.runtime_dir, recursive=True).parse_ddg_files()
                for task in task_list
            ]
        )

    def mut2mutfile(self) -> Tuple[List[str], List[Mutant]]:
        pdbs = [os.path.join(self.mutant_pdb_dir, f) for f in os.listdir(self.mutant_pdb_dir)]
        mutants = Mutant.from_pdb(self.pdb, pdbs)

        mutants_dict = {m.raw_mutant_id: m for m in mutants}

        mutfiles = []

        for i, m in enumerate(mutants_dict.values()):
            m_id = m.raw_mutant_id
            mutfile = os.path.join(self.save_dir, self.job_id, "mutfiles", f"{m_id}.mutfile")
            mutants2mutfile([m], mutfile)
            mutfiles.append(mutfile)
        return mutfiles, list(mutants_dict.values())


def main(legacy: bool = False):
    cart_ddg = CartesianDDG(
        pdb="tests/data/3fap_hf3_A_short.pdb",
        nstruct_relax=4,
        use_legacy=legacy,
        job_id="cart_ddg" if not legacy else "cart_ddg_legacy",
    )

    pdb_path = cart_ddg.relax()
    df = cart_ddg.cartesian_ddg(input_pdb=pdb_path)

    print(df)


if __name__ == "__main__":
    main(True)
