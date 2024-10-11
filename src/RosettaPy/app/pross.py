import os
from typing import List, Optional
from dataclasses import dataclass
from RosettaPy import Rosetta, RosettaScriptsVariableGroup, RosettaEnergyUnitAnalyser, MPI_node
from RosettaPy.utils import timing, RosettaCmdTask
from RosettaPy.node import RosettaContainer
from RosettaPy.app.utils import PDBProcessor

script_dir = os.path.dirname(os.path.abspath(__file__))


@dataclass
class PROSS:
    pdb: str = ""
    pssm: str = ""

    res_to_fix: str = "1A"
    res_to_restrict: str = "1A"
    blast_bin: Optional[str] = None
    uniref90_db_blast: Optional[str] = None

    save_dir: str = "tests/outputs"
    job_id: str = "pross"

    CA_constraints: str = ""
    seq_len: int = 0
    instance: str = ""

    filter_thresholds = [0.5, -0.45, -0.75, -1, -1.25, -1.5, -1.8, -2]

    def __post_init__(self):
        if not os.path.isfile(self.pdb):
            raise FileNotFoundError(f"PDB is given yet not found - {self.pdb}")

        self.instance = os.path.basename(self.pdb)[:-4]
        self.pdb = os.path.abspath(self.pdb)

        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

        self.CA_constraints = os.path.join(self.save_dir, self.job_id, f"{self.instance}_bbCA.cst")
        self.seq_len = PDBProcessor.convert_pdb_to_constraints(self.pdb, self.CA_constraints)

    def refine(self, nstruct=1) -> str:
        refinement_dir = os.path.join(self.save_dir, self.job_id, "refinement")

        rosetta = Rosetta(
            bin="rosetta_scripts",
            flags=[os.path.join(script_dir, "deps/pross/flags/flags_nodelay")],
            opts=[
                "-parser:protocol",
                f"{script_dir}/deps/pross/xmls/refine.xml",
                RosettaScriptsVariableGroup.from_dict(
                    {
                        "cst_value": "0.4",
                        "cst_full_path": self.CA_constraints,
                        "pdb_reference": self.pdb,
                        "res_to_fix": self.res_to_fix,
                    }
                ),
            ],
            output_dir=refinement_dir,
            save_all_together=False,
            job_id="pross_refinement",
            # run_node=RosettaContainer(image="dockerhub.yaoyy.moe/rosettacommons/rosetta:mpi"),
        )

        with timing("PROSS: Refinement"):
            rosetta.run(inputs=[{"-in:file:s": self.pdb}], nstruct=nstruct)

        best_refined_decoy = RosettaEnergyUnitAnalyser(rosetta.output_scorefile_dir).best_decoy
        best_refined_pdb = os.path.join(rosetta.output_pdb_dir, f'{best_refined_decoy["decoy"]}.pdb')

        print(
            f'Best Decoy on refinement: {best_refined_decoy["decoy"]} - {best_refined_decoy["score"]}: {best_refined_pdb}'
        )

        assert os.path.isfile(best_refined_pdb)
        return os.path.abspath(best_refined_pdb)

    def filterscan(self, refined_pdb: str) -> List[str]:
        self.filterscan_dir = os.path.join(self.save_dir, self.job_id, "filterscan")

        score_path = os.path.join(self.filterscan_dir, "scores")
        resfiles_path = os.path.join(self.filterscan_dir, "resfiles", "tmp/")
        os.makedirs(score_path, exist_ok=True)
        os.makedirs(resfiles_path, exist_ok=True)

        existed_filters = [
            os.path.join(self.filterscan_dir, "resfiles", f"designable_aa_resfile.{str(i)}")
            for i in self.filter_thresholds
        ]

        if all(os.path.isfile(f) for f in existed_filters):
            print("Skip filterscan because all filters are found.")
            return [os.path.basename(f) for f in existed_filters]

        rosetta = Rosetta(
            bin="rosetta_scripts",
            flags=[os.path.join(script_dir, "deps/pross/flags/flags_nodelay")],
            opts=[
                "-in:file:s",
                refined_pdb,
                "-no_nstruct_label",
                "-overwrite",
                "-out:path:all",
                self.filterscan_dir,
                "-parser:protocol",
                f"{script_dir}/deps/pross/xmls/filterscan_parallel.xml",
                RosettaScriptsVariableGroup.from_dict(
                    {
                        "cst_value": "0.4",
                        "cst_full_path": self.CA_constraints,
                        "pdb_reference": self.pdb,
                        "res_to_fix": self.res_to_fix,
                        "resfiles_path": resfiles_path,
                        "scores_path": score_path,
                        "pssm_full_path": self.pssm,
                        "res_to_restrict": self.res_to_restrict,
                    }
                ),
            ],
            output_dir=self.filterscan_dir,
            save_all_together=True,
            job_id=f"{self.instance}.filterscan",
            # run_node=RosettaContainer(image="dockerhub.yaoyy.moe/rosettacommons/rosetta:latest"),
        )

        with timing("PROSS: Filterscan"):
            rosetta.run(inputs=[{"-parser:script_vars": f"current_res={i}"} for i in range(1, self.seq_len + 1)])

        # merge resfiles
        merged_filters = self.merge_resfiles(self.filterscan_dir, self.seq_len)

        return [os.path.basename(f) for f in merged_filters]

    def merge_resfiles(self, filterscan_res_dir: str, seq_length: int) -> List[str]:
        """
        Merges temporary resfiles by their levels and writes the merged resfile to the target directory.

        Args:
            filterscan_res_dir (str): Directory path where resfiles are stored.
            seq_length (int): The sequence length indicating how many resfiles are expected.

        Expected output:
            A merged resfile at: {filterscan_res_dir}/resfiles/designable_aa_resfile.<level>
        """

        # Print banner and indicate the start of the merging process
        print("Step 4: merge resfiles.")

        resfiles = []

        # Iterate over the different levels
        for level in [0.5, -0.45, -0.75, -1, -1.25, -1.5, -1.8, -2]:
            resfile_fn = f"designable_aa_resfile.{level}"
            first_resfile = True

            target_resfile_path = os.path.join(filterscan_res_dir, "resfiles", resfile_fn)

            # Iterate over each resfile id from 1 to seq_length
            for res_id in range(1, seq_length + 1):
                tmp_resfile_fn = f"designable_aa_resfile-{res_id}.{level}"
                tmp_resfile_path = os.path.join(filterscan_res_dir, "resfiles", "tmp", tmp_resfile_fn)

                # Check if the tmp resfile exists
                if not os.path.isfile(tmp_resfile_path):
                    # print(f"TmpResFile not found: {tmp_resfile_fn}")
                    continue

                # If it's the first resfile, we initialize the target resfile by writing the first tmp file
                if first_resfile:
                    # print(f"Head TmpResFile found: {tmp_resfile_fn}")
                    with open(tmp_resfile_path, "r") as tmp_file:
                        content = tmp_file.read()

                    with open(target_resfile_path, "w") as resfile:
                        resfile.write(content)
                    first_resfile = False
                else:
                    # Append the relevant lines (those starting with digits) from subsequent tmp files
                    with open(tmp_resfile_path, "r") as tmp_file:
                        lines = tmp_file.readlines()
                    with open(target_resfile_path, "a") as resfile:
                        resfile.writelines(line for line in lines if line.strip() and line[0].isdigit())

            resfiles.append(target_resfile_path)
        return resfiles

    def design(self, filters: List[str], refined_pdb: str):
        design_dir = os.path.join(self.save_dir, self.job_id, "design")

        rosetta = Rosetta(
            bin="rosetta_scripts",
            flags=[os.path.join(script_dir, "deps/pross/flags/flags_nodelay")],
            opts=[
                "-in:file:s",
                refined_pdb,
                "-no_nstruct_label",
                "-parser:protocol",
                f"{script_dir}/deps/pross/xmls/design_new.xml",
                RosettaScriptsVariableGroup.from_dict(
                    {
                        "cst_value": "0.4",
                        "cst_full_path": self.CA_constraints,
                        "pdb_reference": self.pdb,
                        "res_to_fix": self.res_to_fix,
                        "pssm_full_path": self.pssm,
                    }
                ),
            ],
            output_dir=design_dir,
            save_all_together=False,
            job_id=f"{self.instance}_design",
            # run_node=RosettaContainer(image="dockerhub.yaoyy.moe/rosettacommons/rosetta:latest"),
        )

        with timing("PROSS: Design"):
            rosetta.run(
                inputs=[
                    {
                        "-parser:script_vars": f"in_resfile={self.filterscan_dir}/resfiles/{resfile}",
                        "-out:suffix": f'_{resfile.replace("designable_aa_resfile.", "")}',
                        "-out:file:scorefile": f'{self.instance}_pross_design_{resfile.replace("designable_aa_resfile.", "")}.sc',
                    }
                    for resfile in filters
                ]
            )

        analyser = RosettaEnergyUnitAnalyser(score_file=rosetta.output_scorefile_dir)
        best_hit = analyser.best_decoy
        pdb_path = os.path.join(rosetta.output_pdb_dir, f'{best_hit["decoy"]}.pdb')

        print("Analysis of the best decoy:")
        print("-" * 79)
        print(analyser.df.sort_values(by=analyser.score_term))

        print("-" * 79)

        print(f'Best Hit on this PROSS run: {best_hit["decoy"]} - {best_hit["score"]}: {pdb_path}')

        return pdb_path


def main():
    pross = PROSS(
        pdb="tests/data/3fap_hf3_A_short.pdb", pssm="tests/data/3fap_hf3_A_ascii_mtx_file_short", job_id="pross_reduced"
    )
    best_refined = pross.refine(4)

    filters = pross.filterscan(best_refined)
    pross.design(filters=filters, refined_pdb=best_refined)


if __name__ == "__main__":
    main()
