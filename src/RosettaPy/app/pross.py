"""
Example Application of PROSS Reimplemented with RosettaPy
"""

# pylint: disable=too-many-instance-attributes

import os
from typing import Any, List, Mapping, Optional, Sequence, Tuple, Union

from RosettaPy import Rosetta, RosettaEnergyUnitAnalyser, RosettaScriptsVariableGroup
from RosettaPy.app.abc import RosettaAppBase
from RosettaPy.app.utils import PDBProcessor
from RosettaPy.node import NodeHintT
from RosettaPy.utils import timing

script_dir = os.path.dirname(os.path.abspath(__file__))


class PROSS(RosettaAppBase):
    """
    PROSS Application
    """

    def __init__(
        self,
        pdb: str = "",
        pssm: str = "",
        res_to_fix: str = "1A",
        res_to_restrict: str = "1A",
        job_id: str = "pross",
        save_dir: str = "pross",
        user_opts: Optional[List] = None,
        node_hint: NodeHintT = "native",
        node_config: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(job_id, save_dir, user_opts, node_hint, node_config, **kwargs)

        self.pdb = pdb
        self.pssm = pssm
        self.res_to_fix = res_to_fix
        self.res_to_restrict = res_to_restrict

        # Check if the PDB file exists; if not, raise an exception
        if not os.path.isfile(self.pdb):
            raise FileNotFoundError(f"PDB is given yet not found - {self.pdb}")

        # Extract the instance name from the PDB file path, removing the file extension
        self._instance = os.path.basename(self.pdb)[:-4]
        # Get the absolute path of the PDB file
        self.pdb = os.path.abspath(self.pdb)

        # Generate the path for the CA constraints file
        self._c_alpha_constraints = os.path.join(self.save_dir, self.job_id, f"{self._instance}_bbCA.cst")
        # Convert the PDB file to constraints and determine the sequence length
        self._seq_len = PDBProcessor.convert_pdb_to_constraints(self.pdb, self._c_alpha_constraints)

    def refine(self, nstruct=1, opts: Optional[Sequence[Union[str, RosettaScriptsVariableGroup]]] = None) -> str:
        """
        Refine the protein structure using PROSS.

        Args:
            nstruct (int): The number of different structures to generate during refinement.

        Returns:
            str: The absolute path of the best refined structure file (PDB format).

        This method sets up and runs a refinement job for the protein structure using Rosetta,
        leveraging the PROSS workflow. It specifies the refinement protocol, constraints,
        and other necessary options, conducts the refinement in a designated output directory,
        and identifies the best refined structure based on energy scores.
        """
        if not opts:
            opts = []
        # Construct the directory path for storing refinement results
        refinement_dir = os.path.join(self.save_dir, self.job_id, "refinement")

        # Initialize the Rosetta object for the refinement job
        rosetta = Rosetta(
            bin="rosetta_scripts",
            flags=[os.path.join(script_dir, "deps/pross/flags/flags_nodelay")],
            opts=[
                "-parser:protocol",
                f"{script_dir}/deps/pross/xmls/refine.xml",
                RosettaScriptsVariableGroup.from_dict(
                    {
                        "cst_value": "0.4",
                        "cst_full_path": self._c_alpha_constraints,
                        "pdb_reference": self.pdb,
                        "res_to_fix": self.res_to_fix,
                    }
                ),
            ]
            + list(opts)
            + list(self.user_opts),
            output_dir=refinement_dir,
            save_all_together=False,
            job_id="pross_refinement",
            run_node=self.node,
        )

        # Execute the refinement job within a timing context
        with timing("PROSS: Refinement"):
            rosetta.run(inputs=[{"-in:file:s": self.pdb}], nstruct=nstruct)

        # Analyze the refinement results to identify the best decoy (refined structure)
        best_decoy = RosettaEnergyUnitAnalyser(rosetta.output_scorefile_dir).best_decoy
        best_refined_pdb = os.path.join(rosetta.output_pdb_dir, f'{best_decoy["decoy"]}.pdb')

        # Output information about the best refined decoy
        print(f'Best Decoy on refinement: {best_decoy["decoy"]} - {best_decoy["score"]}: {best_refined_pdb}')

        # Ensure the best refined PDB file exists
        if not os.path.isfile(best_refined_pdb):
            raise RuntimeError(f"Refinement against {self._instance} failed.")

        # Return the absolute path of the best refined PDB file
        return os.path.abspath(best_refined_pdb)

    def filterscan(
        self, refined_pdb: str, opts: Optional[Sequence[Union[str, RosettaScriptsVariableGroup]]] = None
    ) -> Tuple[List[str], str]:
        """
        Perform filterscan on the refined PDB file to generate residue designability filters.

        Parameters:
            refined_pdb (str): The path of the refined PDB file.

        Returns:
            Tuple[List[str], str]: A tuple containing a list of merged filter files and the directory path
            of the filterscan results.
        """
        if not opts:
            opts = []

        # Define the threshold for each filter
        filter_thresholds = [0.5, -0.45, -0.75, -1, -1.25, -1.5, -1.8, -2]

        # Construct the directory path for filterscan results
        filterscan_dir = os.path.join(self.save_dir, self.job_id, "filterscan")

        # Define the paths for score files and residue design files
        score_path = os.path.join(filterscan_dir, "scores")
        resfiles_path = os.path.join(filterscan_dir, "resfiles", "tmp/")
        os.makedirs(score_path, exist_ok=True)
        os.makedirs(resfiles_path, exist_ok=True)

        # Generate the file paths for all filters
        existed_filters = [
            os.path.join(filterscan_dir, "resfiles", f"designable_aa_resfile.{str(i)}") for i in filter_thresholds
        ]

        # If all filter files exist, skip filterscan and return the file names and directory path
        if all(os.path.isfile(f) for f in existed_filters):
            print("Skip filterscan because all filters are found.")
            return [os.path.basename(f) for f in existed_filters], filterscan_dir

        # Initialize Rosetta object for running filterscan protocol
        rosetta = Rosetta(
            bin="rosetta_scripts",
            flags=[os.path.join(script_dir, "deps/pross/flags/flags_nodelay")],
            opts=[
                "-in:file:s",
                refined_pdb,
                "-no_nstruct_label",
                "-overwrite",
                "-out:path:all",
                filterscan_dir,
                "-parser:protocol",
                f"{script_dir}/deps/pross/xmls/filterscan_parallel.xml",
                RosettaScriptsVariableGroup.from_dict(
                    {
                        "cst_value": "0.4",
                        "cst_full_path": self._c_alpha_constraints,
                        "pdb_reference": self.pdb,
                        "res_to_fix": self.res_to_fix,
                        "resfiles_path": resfiles_path,
                        "scores_path": score_path,
                        "pssm_full_path": self.pssm,
                        "res_to_restrict": self.res_to_restrict,
                    }
                ),
            ]
            + list(opts)
            + list(self.user_opts),
            output_dir=filterscan_dir,
            save_all_together=True,
            job_id=f"{self._instance}.filterscan",
            run_node=self.node,
        )

        # Run filterscan protocol
        with timing("PROSS: Filterscan"):
            rosetta.run(inputs=[{"-parser:script_vars": f"current_res={i}"} for i in range(1, self._seq_len + 1)])

        # Merge resfiles
        merged_filters = merge_resfiles(filterscan_dir, self._seq_len)

        # Return the list of merged filter files and the directory path of the filterscan results
        return [os.path.basename(f) for f in merged_filters], filterscan_dir

    def design(
        self,
        filters: List[str],
        refined_pdb: str,
        filterscan_dir,
        opts: Optional[Sequence[Union[str, RosettaScriptsVariableGroup]]] = None,
    ):
        """
        Performs protein design process.

        This function uses the Rosetta software package to perform protein design, including design scans
        with different filter conditions and analysis of the design results to find the optimal decoy.

        Parameters:
        - filters (List[str]): A list of filter names used for design scans.
        - refined_pdb (str): The path to the refined PDB file.
        - filterscan_dir (str): The directory containing filter scan files.

        Returns:
        - pdb_path (str): The path to the PDB file of the best decoy.
        """
        if not opts:
            opts = []
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
                        "cst_full_path": self._c_alpha_constraints,
                        "pdb_reference": self.pdb,
                        "res_to_fix": self.res_to_fix,
                        "pssm_full_path": self.pssm,
                    }
                ),
            ]
            + list(opts)
            + list(self.user_opts),
            output_dir=design_dir,
            save_all_together=False,
            job_id=f"{self._instance}_design",
            run_node=self.node,
        )

        with timing("PROSS: Design"):
            rosetta.run(
                inputs=[
                    {
                        "-parser:script_vars": f"in_resfile={filterscan_dir}/resfiles/{rf}",
                        "-out:suffix": f'_{rf.replace("designable_aa_resfile.", "")}',
                        "-out:file:scorefile": f'{self._instance}_design_{rf.replace("designable_aa_resfile.", "")}.sc',
                    }
                    for rf in filters
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


def merge_resfiles(filterscan_res_dir: str, seq_length: int) -> List[str]:
    """
    Merges temporary resfiles by their levels and writes the merged resfile to the target directory.

    Args:
        filterscan_res_dir (str): Directory path where resfiles are stored.
        seq_length (int): The sequence length indicating how many resfiles are expected.

    Returns:
        List[str]: Paths to the merged resfiles.
    """

    # Print a banner and indicate the start of the merging process
    print("Step 4: merge resfiles.")

    # Initialize a list to store the paths of all merged resfiles
    resfiles = []

    # Iterate over the different levels
    for level in [0.5, -0.45, -0.75, -1, -1.25, -1.5, -1.8, -2]:
        # Construct the filename for the current level resfile
        resfile_fn = f"designable_aa_resfile.{level}"
        # Mark whether this is the first resfile
        first_resfile = True

        # Construct the full path for the target resfile
        target_resfile_path = os.path.join(filterscan_res_dir, "resfiles", resfile_fn)

        # Iterate over each resfile ID from 1 to seq_length
        for res_id in range(1, seq_length + 1):
            # Construct the filename for the temporary resfile
            tmp_resfile_fn = f"designable_aa_resfile-{res_id}.{level}"
            # Construct the full path for the temporary resfile
            tmp_resfile_path = os.path.join(filterscan_res_dir, "resfiles", "tmp", tmp_resfile_fn)

            # Check if the temporary resfile exists
            if not os.path.isfile(tmp_resfile_path):
                # If it does not exist, skip it
                continue

            # If this is the first resfile, initialize the target resfile with the first temporary file's content
            if first_resfile:
                with open(tmp_resfile_path, encoding="utf-8") as tmp_file:
                    content = tmp_file.read()
                with open(target_resfile_path, "w", encoding="utf-8") as resfile:
                    resfile.write(content)
                first_resfile = False
            else:
                # Otherwise, append relevant lines (those starting with digits) from subsequent temporary files
                with open(tmp_resfile_path, encoding="utf-8") as tmp_file:
                    lines = tmp_file.readlines()
                with open(target_resfile_path, "a", encoding="utf-8") as resfile:
                    resfile.writelines(line for line in lines if line.strip() and line[0].isdigit())

        # Add the path of the merged resfile to the list
        resfiles.append(target_resfile_path)

    # Return the list containing the paths of all merged resfiles
    return resfiles


def main(
    node_hint: NodeHintT = "native",
):
    """
    Test
    """
    if node_hint == "docker":
        node_hint = "docker_mpi"

    docker_label = f"_{node_hint}" if node_hint else ""
    pross = PROSS(
        pdb="tests/data/3fap_hf3_A_short.pdb",
        pssm="tests/data/3fap_hf3_A_ascii_mtx_file_short",
        job_id="pross_reduce" + docker_label,
        node_hint=node_hint,
    )
    best_refined = pross.refine(1)

    filters, filterscan_dir = pross.filterscan(best_refined)
    pross.design(filters=filters, refined_pdb=best_refined, filterscan_dir=filterscan_dir)


if __name__ == "__main__":
    main()
