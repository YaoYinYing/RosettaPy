import os
from dataclasses import dataclass
import warnings


from RosettaPy import Rosetta, RosettaEnergyUnitAnalyser
from RosettaPy.utils import timing


script_dir = os.path.dirname(os.path.abspath(__file__))


class RelaxScriptInputWarning(UserWarning): ...


@dataclass
class FastRelax:
    pdb: str

    save_dir: str = "tests/outputs"
    job_id: str = "fastrelax"

    relax_script: str = "MonomerRelax2019"
    default_repeats: int = 15

    dualspace: bool = False

    @staticmethod
    def get_relax_scripts_from_db(script_name: str) -> str:
        """
        ref:
        ERROR: [ERROR] relaxscript argument /usr/local/database/MonomerRelax2019.txt should not have extensions.
        Additionally, /usr/local/database/MonomerRelax2019 does not appear to be a valid script name.
        Please look at main/database/sampling/relax_scripts/ or the wiki for valid names.
        """

        if os.path.exists(script_name):
            return os.path.basename(script_name).replace(".txt", "")

        if script_name.endswith(".txt"):
            script_name = script_name[:-4]

        ROSETTA3_DB = os.environ.get("ROSETTA3_DB")
        if not ROSETTA3_DB:
            raise RuntimeError("ROSETTA3_DB environment variable is not set")

        all_scripts = [
            os.path.join(ROSETTA3_DB, f[:-4])
            for f in os.listdir(f"{ROSETTA3_DB}/sampling/relax_scripts/")
            if f.endswith(".txt") and f != "README.txt" and "dualspace" not in f
        ]

        for script in all_scripts:
            if os.path.basename(script) == script_name:
                return script_name

        raise RuntimeError(
            f"No such relax script - {script_name}, All available scripts: {[os.path.basename(f).replace('.txt','') for f in all_scripts]}"
        )

    def __post_init__(self):
        if not os.path.isfile(self.pdb):
            raise FileNotFoundError(f"PDB is given yet not found - {self.pdb}")
        self.instance = os.path.basename(self.pdb)[:-4]
        self.pdb = os.path.abspath(self.pdb)

        os.makedirs(os.path.join(self.save_dir, self.job_id), exist_ok=True)
        self.save_dir = os.path.abspath(self.save_dir)

        if self.relax_script.endswith(".txt"):
            warnings.warn(RelaxScriptInputWarning(f"Relaxscript argument should not have extensions."))

        self.relax_script = self.get_relax_scripts_from_db(self.relax_script)

    def run(self, nstruct: int = 8) -> RosettaEnergyUnitAnalyser:

        rosetta = Rosetta(
            bin="relax",
            opts=[
                "-in:file:s",
                os.path.abspath(self.pdb),
                "-relax:script",
                self.relax_script,
                "-relax:default_repeats",
                str(self.default_repeats),
                "-out:prefix",
                f"{self.instance}_fastrelax_",
                "-out:file:scorefile",
                f"{self.instance}_fastrelax.sc",
                "-score:weights",
                "ref2015_cart" if self.dualspace else "ref2015",
                "-relax:dualspace",
                "true" if self.dualspace else "false",
            ],
            save_all_together=True,
            output_dir=os.path.join(self.save_dir, self.job_id),
            job_id=f"fastrelax_{self.instance}_{os.path.basename(self.relax_script)}",
            # run_node=RosettaContainer(image="dockerhub.yaoyy.moe/rosettacommons/rosetta:latest"),
        )

        with timing("FastRelax"):
            rosetta.run(nstruct=nstruct)

        return RosettaEnergyUnitAnalyser(rosetta.output_scorefile_dir)


def main(dualspace: bool = False):
    if dualspace:
        scorer = FastRelax(
            pdb="tests/data/3fap_hf3_A.pdb", dualspace=True, job_id="fastrelax_dualspace", default_repeats=3
        )
    else:
        scorer = FastRelax(pdb="tests/data/3fap_hf3_A.pdb", default_repeats=3)

    analyser = scorer.run(4)
    best_hit = analyser.best_decoy

    print("Analysis of the best decoy:")
    print("-" * 79)
    print(analyser.df.sort_values(by=analyser.score_term))

    print("-" * 79)

    print(f'Best Hit on this FastRelax run: {best_hit["decoy"]} - {best_hit["score"]}')


if __name__ == "__main__":
    main()
