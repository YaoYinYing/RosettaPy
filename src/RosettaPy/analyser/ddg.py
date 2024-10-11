from dataclasses import dataclass
import os
from typing import Any, Dict, List, Literal
import warnings

import json
import numpy as np
import pandas as pd

from Bio.Data import IUPACData


def get_stats(group: pd.DataFrame) -> Dict[str, Any]:
    return {"std": np.std(group), "mean": group.mean(), "nr": len(group)}


@dataclass
class RosettaCartesianddGAnalyser:
    runtime_dir: str
    recursive: bool = True

    prefer_json: bool = True

    @staticmethod
    def plot_ddg_summary(df_tot: pd.DataFrame, save_dir: str = "tests/outputs/ddg_results"):
        import matplotlib.pyplot as plt

        os.makedirs(save_dir, exist_ok=True)

        plt.figure()
        df_tot["ddG_cart"].plot.hist(bins=30)
        plt.title("ddG")
        plt.xlabel("ddG (kcal/mol)")
        plt.savefig(f"{save_dir}/ddG_dist.png")

        plt.figure()

    def __post_init__(self):
        self.files = self.gather_files()
        if not self.files and self.prefer_json:
            warnings.warn(
                "No .json files found in the directory. Falling back to .ddg files. "
                "This is not recommended as the .ddg files are not fully supported and may not be accurate."
            )
            self.prefer_json = False
            self.files = self.gather_files()

    def gather_files(self) -> List[str]:
        if self.recursive:
            return [
                os.path.join(root, file_name)
                for root, _, files in os.walk(self.runtime_dir)
                for file_name in files
                if file_name.endswith(".json" if self.prefer_json else ".ddg")
            ]

        return [
            os.path.join(self.runtime_dir, file_name)
            for file_name in os.listdir(self.runtime_dir)
            if file_name.endswith(".json" if self.prefer_json else ".ddg")
        ]

    @staticmethod
    def read_ddg(path_and_file_name: str) -> pd.DataFrame:
        header_text = [
            "COMPLEX",
            "Round",
            "Baseline",
            "total",
            "fa_atr_label",
            "fa_atr",
            "fa_rep_label",
            "fa_rep",
            "fa_sol_label",
            "fa_sol",
            "fa_intra_rep_label",
            "fa_intra_rep",
            "fa_intra_sol_xover4_label",
            "fa_intra_sol_xover4",
            "lk_ball_wtd_label",
            "lk_ball_wtd",
            "fa_elec_label",
            "fa_elec",
            "hbond_sr_bb_label",
            "hbond_sr_bb",
            "hbond_lr_bb_label",
            "hbond_lr_bb",
            "hbond_bb_sc_label",
            "hbond_bb_sc",
            "hbond_sc_label",
            "hbond_sc",
            "dslf_fa13_label",
            "dslf_fa13",
            "omega_label",
            "omega",
            "fa_dun_label",
            "fa_dun",
            "p_aa_pp_label",
            "p_aa_pp",
            "yhh_planarity_label",
            "yhh_planarity",
            "ref_label",
            "ref",
            "rama_prepro_label",
            "rama_prepro",
            "cart_bonded_label",
            "cart_bonded",
        ]
        df = pd.read_csv(path_and_file_name, skiprows=0, sep="\s+", names=header_text)

        labels = [label for label in df.columns if label.endswith("label")]
        df.drop(["COMPLEX"] + labels, axis=1, inplace=True)

        # rename wt
        wt_labels = ["WT_:", "WT:"]
        mask = df["Baseline"].isin(wt_labels)
        df.loc[mask, "Baseline"] = "WT"

        # Drop ending `:`
        df["Baseline"] = df["Baseline"].str.rstrip(":")

        return df

    @staticmethod
    def read_json(path_and_file_name: str) -> pd.DataFrame:
        ddg_json: List[Dict[Literal["mutations", "scores"], Any]] = json.load(open(path_and_file_name))

        mutant_ddg_records = []
        # round counts
        id_cache: str = ""
        id_count: int = 0
        for _j in ddg_json:
            mutations: List[Dict[Literal["mut", "pos", "wt"], str]] = _j["mutations"]
            scores: Dict[str, Any] = _j["scores"]

            if RosettaCartesianddGAnalyser.is_wild_type(mutations):
                mutant_id = "WT"
            else:
                mutant_id = RosettaCartesianddGAnalyser.mutinfo2id(mutations)

            # round counts
            if id_cache != mutant_id:
                id_cache = mutant_id
                id_count = 0
            else:
                id_count += 1

            md = {"Round": f"Round{id_count}", "Baseline": id_cache}

            md.update(scores)
            mutant_ddg_records.append(md)

        df = pd.DataFrame(mutant_ddg_records)
        return df

    @staticmethod
    def is_wild_type(mutations: List[Dict[Literal["mut", "pos", "wt"], str]]) -> bool:
        return all([m["mut"] == m["wt"] for m in mutations])

    @staticmethod
    def mutinfo2id(mutations: List[Dict[Literal["mut", "pos", "wt"], str]]) -> str:
        return "MUT_" + "_".join(f'{m["pos"]}{IUPACData.protein_letters_1to3[m["mut"]].upper()}' for m in mutations)

    def parse_ddg_files(self) -> pd.DataFrame:
        if self.prefer_json:
            self.dg_df_raws = [self.read_json(f) for f in self.files]
        else:
            self.dg_df_raws = [self.read_ddg(f) for f in self.files]

        self.dg_df_raws = list(filter(lambda df: not df.empty, self.dg_df_raws))

        ddg_summary = pd.concat([self.raw_to_ddg(df) for df in self.dg_df_raws])
        ddg_summary.loc[(ddg_summary["ddG_cart"] < ddg_summary["cutoff"]), "Accepted"] = 1
        ddg_summary.loc[(ddg_summary["ddG_cart"] >= ddg_summary["cutoff"]), "Accepted"] = 0
        ddg_summary = ddg_summary.loc[ddg_summary["Baseline"].str.startswith("MUT_"), :]

        self.ddg_summary = ddg_summary
        return ddg_summary

    @staticmethod
    def raw_to_ddg(df_raw: pd.DataFrame) -> pd.DataFrame:

        df_tot_ = df_raw.groupby(["Baseline"])["total"].apply(get_stats).unstack().reset_index()
        df_tot_["ddG_cart"] = df_tot_["mean"] - df_tot_["mean"].loc[(df_tot_["Baseline"] == "WT")].values[0]

        cutoff = (
            df_tot_[df_tot_["Baseline"] == "WT"]["ddG_cart"].values[0]
            + 2 * df_tot_[df_tot_["Baseline"] == "WT"]["std"].values[0]
        )

        df_tot_["WT_mean"] = df_tot_["mean"].loc[(df_tot_["Baseline"] == "WT")].values[0]
        df_tot_["WT_mean_std"] = df_tot_["std"].loc[(df_tot_["Baseline"] == "WT")].values[0]
        df_tot_["cutoff"] = cutoff

        df_tot_.drop(df_tot_[df_tot_["Baseline"] == "WT"].index, inplace=True)
        return df_tot_


def main():
    ddg_analyser = RosettaCartesianddGAnalyser("tests/data/ddg_runtimes", recursive=True)
    df = ddg_analyser.parse_ddg_files()

    print(df)

    ddg_analyser.plot_ddg_summary(df)


if __name__ == "__main__":
    main()
