"""
Example Application of Rosetta Supercharge
"""

import os
from typing import List, Optional

from RosettaPy import Rosetta
from RosettaPy.node import NodeClassType, NodeHintT, node_picker
from RosettaPy.rosetta import RosettaCmdTask


def supercharge(
    pdb: str, abs_target_charge=20, node_hint: Optional[NodeHintT] = "native", **node_config
) -> List[RosettaCmdTask]:
    """
    Applies the Rosetta Supercharge protocol to a given PDB file to perform charge mutation scanning.

    The Supercharge protocol aims to optimize the charge distribution of a protein by altering the charge
    states of amino acid residues, exploring stability and other properties under different charge conditions.

    Parameters:
    - pdb: Path to the PDB file containing the protein structure.
    - abs_target_charge: Absolute value of the target net charge range (default is 20, meaning it will scan
    from -20 to 20).
    - nproc: Number of CPU cores for parallel processing (default is 4).

    Returns:
    - A list of RosettaCmdTask objects, each representing a Supercharge run task for a specific charge state.
    """

    # Initialize the Rosetta object with configuration parameters for the Supercharge protocol
    docker_label = f"_{node_hint}" if node_hint else ""
    node: NodeClassType = node_picker(node_type=node_hint, **node_config)
    rosetta = Rosetta(
        "supercharge",
        job_id="test_supercharge" + docker_label,
        output_dir=os.path.abspath("tests/outputs/"),
        opts=[
            "-in:file:s",  # Input PDB file
            os.path.abspath(pdb),
            "-dont_mutate_glyprocys",  # Do not mutate glycosylated or cysteine residues
            "true",
            "-dont_mutate_correct_charge",  # Do not mutate correctly charged residues
            "true",
            # Do not mutate side chains involved in hydrogen bonds
            "-dont_mutate_hbonded_sidechains",
            "true",
            "-include_asp",  # Include aspartic acid
            "-include_glu",  # Include glutamic acid
            "-refweight_asp",  # Reference weight for aspartic acid
            "-0.6",
            "-refweight_glu",  # Reference weight for glutamic acid
            "-0.8",
            "-include_arg",  # Include arginine
            "-include_lys",  # Include lysine
            "-refweight_arg",  # Reference weight for arginine
            "-1.98",
            "-refweight_lys",  # Reference weight for lysine
            "-1.65",
            "-ignore_unrecognized_res",  # Ignore unrecognized residues
            "-surface_residue_cutoff",  # Surface residue cutoff distance
            "16",
            "-target_net_charge_active",  # Activate target net charge option
            "-mute",  # Silent mode, no log information
            "all",
            "-unmute",  # Unmute Supercharge protocol information
            "protocols.design_opt.Supercharge",
            "-overwrite",  # Overwrite existing result files
            "-run:score_only",  # Perform only scoring calculations
        ],
        save_all_together=True,  # Save all results together
        isolation=True,  # Run in isolation to prevent contamination of other tasks
        run_node=node,
    )

    # Generate instance name based on the PDB file name
    instance = os.path.basename(pdb)[:-4]

    # Return the run results of the Rosetta object, each corresponding to a specific charge state
    return rosetta.run(
        inputs=[
            {"-out:file:scorefile": f"{instance}_charge_{c}.sc", "-target_net_charge": str(c)}
            for c in range(-abs_target_charge, abs_target_charge, 2)
        ]
    )


def main(
    node_hint: Optional[NodeHintT] = None,
):
    """
    Test
    """

    pdb = "tests/data/3fap_hf3_A.pdb"
    supercharge(pdb, node_hint=node_hint)


if __name__ == "__main__":
    main()
