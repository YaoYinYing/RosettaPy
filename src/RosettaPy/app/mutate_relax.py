"""
Example Application of Mutate and Relax Protocol against Clustered Sequences.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from Bio.Data import IUPACData
from Bio.SeqIO import parse

from RosettaPy import Rosetta, RosettaEnergyUnitAnalyser, RosettaScriptsVariableGroup
from RosettaPy.node import NodeClassType, NodeHintT, node_picker
from RosettaPy.node.native import Native
from RosettaPy.utils import timing

script_dir = os.path.dirname(os.path.abspath(__file__))


@dataclass
class ScoreClusters:
    """
    A class used to score clusters of protein structures.

    Attributes:
    pdb (str): Path to the protein structure file (PDB format).
    chain_id (str): Identifier of the protein chain.
    save_dir (str): Directory to save the scoring results, default is "tests/outputs".
    job_id (str): Identifier for the job, default is "score_clusters".
    node (NodeClassType): The node configuration for running the relaxation. Defaults to Native(nproc=4).
    """

    pdb: str
    chain_id: str

    save_dir: str = "tests/outputs"
    job_id: str = "score_clusters"

    node: NodeClassType = field(default_factory=Native)

    def __post_init__(self):
        """
        Performs checks and setups after object initialization.
        """
        # Check if the PDB file exists
        if not os.path.isfile(self.pdb):
            raise FileNotFoundError(f"PDB is given yet not found - {self.pdb}")
        # Set instance name and absolute path of the PDB file
        self.instance = os.path.basename(self.pdb)[:-4]
        self.pdb = os.path.abspath(self.pdb)

        # Create directory to save results
        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

    def score(self, branch: str, variants: List[str]) -> RosettaEnergyUnitAnalyser:
        """
        Scores the provided variants within a specific branch.

        Parameters:
        branch (str): Identifier of the branch.
        variants (List[str]): List of variants to be scored.

        Returns:
        RosettaEnergyUnitAnalyser: An object containing the analysis of the scoring results.
        """
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
            run_node=self.node,
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
        """
        Runs the scoring process on clusters within the specified directory.

        Parameters:
        cluster_dir (str): Directory containing clusters to be scored.

        Returns:
        List[RosettaEnergyUnitAnalyser]: A list of objects containing the analysis of the scoring
        results for each cluster.
        """
        cluster_fastas = [c for c in os.listdir(cluster_dir) if c.startswith("c.") and c.endswith(".fasta")]

        clusters = {c.replace(".fasta", ""): self.fasta2mutlabels(os.path.join(cluster_dir, c)) for c in cluster_fastas}

        res: List[RosettaEnergyUnitAnalyser] = []

        for c, v in clusters.items():
            res.append(self.score(branch=c, variants=v))

        return res

    @staticmethod
    def fasta2mutlabels(f: str) -> List[str]:
        """
        Converts a FASTA file into a list of mutation labels.

        Parameters:
        f (str): Path to the FASTA file.

        Returns:
        List[str]: List of mutation labels.
        """
        return [record.id.lstrip(">") for record in parse(f, "fasta")]

    @staticmethod
    def muttask(mut_info: str, chain_id: str):
        """
        Generates a mutation task string from mutation information.

        Parameters:
        mut_info (str): Mutation information.
        chain_id (str): Identifier of the protein chain.

        Returns:
        str: Mutation task string.
        """
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
        """
        Generates an XML-formatted mutation instruction string.

        Parameters:
        mut_info (str): Mutation information.
        chain_id (str): Identifier of the protein chain.

        Returns:
        str: XML-formatted mutation instruction string.
        """
        mut_mover = ""

        mut_array = mut_info.split("_")
        for i, mut in enumerate(mut_array):
            resid = int(mut[1:-1])
            res_mut = mut[-1]
            new_res = IUPACData.protein_letters_1to3[res_mut].upper()

            new_mut_mover = f'<MutateResidue name="mr{i}" target="{resid}{chain_id}" new_res="{new_res}" />'

            if mut_mover == "":
                mut_mover = new_mut_mover
            else:
                mut_mover += new_mut_mover

        return mut_mover

    @staticmethod
    def mutprotocol(mut_info: str):
        """
        Generates a protocol string for mutations.

        Parameters:
        mut_info (str): Mutation information.

        Returns:
        str: Protocol string for mutations.
        """
        mut_array = mut_info.split("_")
        mut_protocol = ""

        for i, _ in enumerate(mut_array):
            new_mut_protocol = f'<Add mover_name="mr{i}"/>'
            mut_protocol += new_mut_protocol

        return mut_protocol


def main(
    num_mut: int = 1,
    node_hint: Optional[NodeHintT] = None,
):
    """
    Test
    """
    if node_hint == "docker":
        node_hint = "docker_mpi"

    docker_label = f"_{node_hint}" if node_hint else ""
    scorer = ScoreClusters(
        pdb="tests/data/1SUO.pdb",
        chain_id="A",
        node=node_picker(node_type=node_hint),
        job_id=f"score_cluster_{docker_label}_{str(num_mut)}",
    )

    ret = scorer.run(f"tests/data/cluster/1SUO_A_1SUO.ent.mut_designs_{num_mut}")

    for i, r in enumerate(ret):
        top = r.best_decoy

        print("-" * 79)
        print(f"Cluster {i} - {top['decoy']} : {top['score']}")
        print(r.top(3))
        print("-" * 79)


if __name__ == "__main__":
    main()
