import os
from typing import List
from dataclasses import dataclass

from Bio.Data import IUPACData
from Bio.SeqIO import parse

from RosettaPy import Rosetta, RosettaScriptsVariableGroup, RosettaEnergyUnitAnalyser
from RosettaPy.node import RosettaContainer
from RosettaPy.utils import timing


script_dir = os.path.dirname(os.path.abspath(__file__))


@dataclass
class ScoreClusters:
    pdb: str
    chain_id: str

    save_dir: str = "tests/outputs"
    job_id: str = "score_clusters"

    def __post_init__(self):
        if not os.path.isfile(self.pdb):
            raise FileNotFoundError(f"PDB is given yet not found - {self.pdb}")
        self.instance = os.path.basename(self.pdb)[:-4]
        self.pdb = os.path.abspath(self.pdb)

        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

    def score(self, branch: str, variants: List[str]) -> RosettaEnergyUnitAnalyser:

        score_dir = os.path.join(self.save_dir, self.job_id, f"branch_{branch}")
        os.makedirs(score_dir, exist_ok=True)

        rosetta = Rosetta(
            bin="rosetta_scripts",
            flags=[os.path.join(script_dir, "deps/mutate_relax/flags/cluster_scoring.flags")],
            opts=[
                "-in:file:s",
                os.path.abspath(self.pdb),
                "-parser:protocol",
                f"{script_dir}/deps/mutate_relax/xml/mutant_validation_temp.xml",
            ],
            output_dir=score_dir,
            save_all_together=True,
            job_id=f"branch_{branch}",
            # run_node=RosettaContainer(image="dockerhub.yaoyy.moe/rosettacommons/rosetta:latest"),
        )

        branch_tasks = [
            {
                "rsv": RosettaScriptsVariableGroup.from_dict(
                    {
                        "muttask": self.muttask(variant, self.chain_id),
                        "mutmover": self.mutmover(variant, self.chain_id),
                        "mutprotocol": self.mutprotocol(variant),
                    }
                ),
                "-out:file:scorefile": f"{variant}.sc",
                "-out:prefix": f"{variant}.",
            }
            for variant in variants
        ]
        with timing("Score clusters"):
            rosetta.run(inputs=branch_tasks)

        return RosettaEnergyUnitAnalyser(rosetta.output_scorefile_dir)

    def run(self, cluster_dir: str):
        cluster_fastas = [c for c in os.listdir(cluster_dir) if c.startswith("c.") and c.endswith(".fasta")]

        clusters = {c.replace(".fasta", ""): self.fasta2mutlabels(os.path.join(cluster_dir, c)) for c in cluster_fastas}

        res: List[RosettaEnergyUnitAnalyser] = []

        for c, v in clusters.items():
            res.append(self.score(branch=c, variants=v))

        return res

    @staticmethod
    def fasta2mutlabels(f: str) -> List[str]:
        return [record.id.lstrip(">") for record in parse(f, "fasta")]

    @staticmethod
    def muttask(mut_info: str, chain_id: str):
        mut_array = mut_info.split("_")
        mut_task = ""
        for mut_id in mut_array:
            resid = mut_id[1:-1]
            new_mut_task = resid + chain_id
            if mut_task == "":
                mut_task = new_mut_task
            else:
                mut_task += "," + new_mut_task
        return mut_task

    @staticmethod
    def mutmover(mut_info: str, chain_id: str) -> str:

        # Initialize the mutation instruction string
        mut_mover = ""

        # Parse the mutation information
        mut_array = mut_info.split("_")
        for mut_id, mut in enumerate(mut_array):
            resid = int(mut[1:-1])  # Extract the residue position
            res_mut = mut[-1]  # Extract the new amino acid type

            # Generate the XML-formatted mutation instruction string
            new_mut_mover = f'<MutateResidue name="mr{mut_id}" target="{resid}{chain_id}" new_res="{IUPACData.protein_letters_1to3[res_mut].upper()}" />'

            # Concatenate the instructions
            if mut_mover == "":
                mut_mover = new_mut_mover
            else:
                mut_mover += new_mut_mover

        return mut_mover

    @staticmethod
    def mutprotocol(mut_info: str):
        mut_array = mut_info.split("_")
        mut_protocol = ""

        for i, mut_id in enumerate(mut_array):
            new_mut_protocol = f'<Add mover_name="mr{i}"/>'
            mut_protocol += new_mut_protocol

        return mut_protocol


def main(num_mut: int = 1):
    scorer = ScoreClusters(pdb="tests/data/1SUO.pdb", chain_id="A")

    ret = scorer.run(f"tests/data/cluster/1SUO_A_1SUO.ent.mut_designs_{num_mut}")

    for i, r in enumerate(ret):
        top = r.best_decoy

        print("-" * 79)
        print(f"Cluster {i} - {top['decoy']} : {top['score']}")
        print(r.top(3))
        print("-" * 79)


if __name__ == "__main__":
    main()
