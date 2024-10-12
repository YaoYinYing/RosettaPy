import os
from typing import List, Optional
from RosettaPy import Rosetta
from RosettaPy.node import RosettaContainer
from RosettaPy.rosetta import RosettaCmdTask


def supercharge(
    pdb: str,
    abs_target_charge=20,
    nproc: Optional[int] = 4,
) -> List[RosettaCmdTask]:

    rosetta = Rosetta(
        "supercharge",
        job_id="test_supercharge",
        output_dir=os.path.abspath("tests/outputs/"),
        nproc=nproc,
        opts=[
            "-in:file:s",
            os.path.abspath(pdb),
            "-dont_mutate_glyprocys",
            "true",
            "-dont_mutate_correct_charge",
            "true",
            "-dont_mutate_hbonded_sidechains",
            "true",
            "-include_asp",
            "-include_glu",
            "-refweight_asp",
            "-0.6",
            "-refweight_glu",
            "-0.8",
            "-include_arg",
            "-include_lys",
            "-refweight_arg",
            "-1.98",
            "-refweight_lys",
            "-1.65",
            "-ignore_unrecognized_res",
            "-surface_residue_cutoff",
            "16",
            "-target_net_charge_active",
            "-mute",
            "all",
            "-unmute",
            "protocols.design_opt.Supercharge",
            "-overwrite",
            "-run:score_only",
        ],
        save_all_together=True,
        isolation=True,
        # run_node=RosettaContainer(image="dockerhub.yaoyy.moe/rosettacommons/rosetta:mpi", prohibit_mpi=True),
    )
    instance = os.path.basename(pdb)[:-4]

    return rosetta.run(
        inputs=[
            {"-out:file:scorefile": f"{instance}_charge_{c}.sc", "-target_net_charge": str(c)}
            for c in range(-abs_target_charge, abs_target_charge, 2)
        ]
    )


def main():
    pdb = "tests/data/3fap_hf3_A.pdb"
    supercharge(pdb, nproc=os.cpu_count())


if __name__ == "__main__":
    main()
