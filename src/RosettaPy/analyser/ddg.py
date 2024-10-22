"""
Cartesian ddG Analysis Utilities.
"""

import json
import os
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from Bio.Data import IUPACData


def get_stats(group: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate and return the statistics for the given data group.

    Parameters:
    group (pd.DataFrame): A pandas DataFrame containing the data to be analyzed.

    Returns:
    Dict[str, Any]: A dictionary containing the following keys and their corresponding values:
        - 'std': The standard deviation of the data group
        - 'mean': The mean value of the data group
        - 'nr': The number of elements in the data group

    This function provides basic statistical characteristics of the data group, including
    the dispersion (through standard deviation), central tendency (through mean value),
    and the scale of the data group (through the count of elements).
    """
    return {"std": np.std(group), "mean": group.mean(), "nr": len(group)}


@dataclass
class RosettaCartesianddGAnalyser:
    """
    Class that performs the analysis of Rosetta Cartesian ddG results.
    """

    runtime_dir: str
    recursive: bool = True

    prefer_json: bool = True

    # internal attributes
    dg_df_raws: Optional[List[pd.DataFrame]] = None
    ddg_summary: Optional[pd.DataFrame] = None

    @staticmethod
    def plot_ddg_summary(df_tot: pd.DataFrame, save_dir: str = "tests/outputs/ddg_results"):
        """
        Plot ddG summary charts.

        This method visualizes the distribution of ddG (delta delta G) values and saves the plots to a
        specified directory.

        It performs the following actions:
        1. Ensures the save directory exists, creating it if necessary.
        2. Plots the histogram of ddG values and saves the chart.

        :param df_tot: DataFrame containing ddG data.
        :param save_dir: Directory where the plots will be saved. Defaults to "tests/outputs/ddg_results".
        """

        os.makedirs(save_dir, exist_ok=True)

        plt.figure()
        df_tot["ddG_cart"].plot.hist(bins=30)
        plt.title("ddG")
        plt.xlabel("ddG (kcal/mol)")
        plt.savefig(f"{save_dir}/ddG_dist.png")

        plt.figure()

    def __post_init__(self):
        """
        Post-initialization method.

        This method is called after object initialization to gather specific files and issue warnings
        based on file types.
        It first attempts to collect all .json files if preferred.
        If no .json files are found, it warns the user and falls back to collecting .ddg files instead.
        """

        self.files = self.gather_files()
        if not self.files and self.prefer_json:
            warnings.warn(
                "No .json files found in the directory. Falling back to .ddg files. "
                "This is not recommended as the .ddg files are not fully supported and may not be accurate."
            )
            self.prefer_json = False
            self.files = self.gather_files()

    def gather_files(self) -> List[str]:
        """
        Collects files based on whether the search is recursive.

        This method collects files from the runtime directory either recursively or non-recursively based
        on the `recursive` attribute.
        - If `recursive` is True, it walks through the directory tree and collects all JSON or DDG files.
        - If `recursive` is False, it only looks at the top-level directory for JSON or DDG files.

        :return: A list of file paths (str) to the collected JSON or DDG files.
        """
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
        """
        Reads a DDG file and returns a pandas DataFrame.

        Parameters:
        path_and_file_name (str): The path and filename of the file to read.

        Returns:
        pd.DataFrame: A DataFrame containing the data from the file.
        """
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
        df = pd.read_csv(path_and_file_name, skiprows=0, sep=r"\s+", names=header_text)

        labels = [label for label in df.columns if label.endswith("label")]
        df.drop(["COMPLEX"] + labels, axis=1, inplace=True)

        # Standardize wild type labels
        wt_labels = ["WT_:", "WT:"]
        mask = df["Baseline"].isin(wt_labels)
        df.loc[mask, "Baseline"] = "WT"

        # Remove trailing colon
        df["Baseline"] = df["Baseline"].str.rstrip(":")

        return df

    @staticmethod
    def read_json(path_and_file_name: str) -> pd.DataFrame:
        """
        Reads a JSON file and converts it into a pandas DataFrame.

        :param path_and_file_name: The path and filename of the JSON file.
        :return: A pandas DataFrame containing the data from the JSON file.
        """
        with open(path_and_file_name, encoding="utf-8") as jr:
            ddg_json: List[Dict[Literal["mutations", "scores"], Any]] = json.load(jr)

        mutant_ddg_records = []
        # Track unique mutant IDs and rounds

        id_cache: str = ""
        id_count: int = 0
        for _j in ddg_json:
            mutations: List[Dict[Literal["mut", "pos", "wt"], str]] = _j["mutations"]
            scores: Dict[str, Any] = _j["scores"]

            if RosettaCartesianddGAnalyser.is_wild_type(mutations):
                mutant_id = "WT"
            else:
                mutant_id = RosettaCartesianddGAnalyser.mutinfo2id(mutations)

            # Update round count for each unique mutant ID
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
        """
        Determine if all mutations in the given list represent wild-type conditions.

        This function checks if the mutation state (`mut`) matches the wild-type state (`wt`) for each entry.
        It returns True if all mutations are wild-type, otherwise False.

        Parameters:
        mutations (List[Dict[Literal["mut", "pos", "wt"], str]]):
            A list of dictionaries containing mutation information, including the mutation state (`mut`),
            position (`pos`), and wild-type state (`wt`).
            - "mut": The mutated state.
            - "pos": The position of the mutation.
            - "wt": The wild-type state.

        Returns:
        bool:
            True if all mutations are wild-type, otherwise False.
        """
        # Check if all "mut" values match the corresponding "wt" values in the mutations list
        return all(m["mut"] == m["wt"] for m in mutations)

    @staticmethod
    def mutinfo2id(mutations: List[Dict[Literal["mut", "pos", "wt"], str]]) -> str:
        """
        Convert a list of mutation information to a specific mutation ID string.

        Parameters:
        mutations: A list of dictionaries containing mutation details, including the mutated amino acid, position,
        and wild-type amino acid.

        Returns:
        A string representing the generated mutation ID in a specific format.

        Summary:
        This function converts a set of mutation information into a standardized string ID, facilitating subsequent
        identification and processing. For each mutation, it concatenates the position and the mutated amino acid
        (converted using IUPACData.protein_letters_1to3) and separates all mutations with underscores. The final
        string is prefixed with "MUT_" to form the complete mutation ID.
        """
        return "MUT_" + "_".join(f'{m["pos"]}{IUPACData.protein_letters_1to3[m["mut"]].upper()}' for m in mutations)

    def parse_ddg_files(self) -> pd.DataFrame:
        """
        Parses DDG files. This method first determines whether to read JSON or DDG files based on the `prefer_json`
        attribute, then filters out empty dataframes, converts the remaining data to DDG format and merges them.
        Finally, it marks which mutations are accepted based on the `ddG_cart` value and the `cutoff` threshold,
        and returns only the summary data of baseline mutations that start with "MUT_".

        :return: A pandas DataFrame containing the summary information of mutations, including which ones were
        accepted.
        """
        # Depending on the prefer_json attribute, choose between using read_json or read_ddg method
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
        """
        Converts raw data to ddG (Delta-Delta G) representation.

        This function groups the raw data by baseline and calculates
        statistics for each group. It then computes the ddG values and
        applies a cutoff based on the wild-type (WT) mean and standard deviation.

        Parameters:
            df_raw (pd.DataFrame): The input DataFrame containing raw data.

        Returns:
            pd.DataFrame: A DataFrame with processed ddG values and cutoff.
        """
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
    """
    Test
    """
    ddg_analyser = RosettaCartesianddGAnalyser("tests/data/ddg_runtimes", recursive=True)
    df = ddg_analyser.parse_ddg_files()

    print(df)

    ddg_analyser.plot_ddg_summary(df)


if __name__ == "__main__":
    main()
