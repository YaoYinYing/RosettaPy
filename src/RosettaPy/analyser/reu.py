"""
Analysis tool of Rosetta Energy Unit
"""

import os
import warnings
from dataclasses import dataclass
from typing import Dict, Literal, Optional, Tuple, Union

import pandas as pd


@dataclass
class RosettaEnergyUnitAnalyser:
    """
    A tool class for analyzing Rosetta energy calculation results.

    Parameters:
    - score_file (str): The path to the score file or directory containing score files.
    - score_term (str, optional): The column name in the score file to use as the score. Defaults to "total_score".
    - job_id (Optional[str], optional): An identifier for the job. Defaults to None.
    """

    score_file: str
    score_term: str = "total_score"

    job_id: Optional[str] = None

    @staticmethod
    def scorefile2df(score_file: str) -> pd.DataFrame:
        """
        Converts a score file into a pandas DataFrame.

        Parameters:
        - score_file (str): Path to the score file.

        Returns:
        - pd.DataFrame: DataFrame containing the data from the score file.
        """
        df = pd.read_fwf(score_file, skiprows=1)

        if "SCORE:" in df.columns:
            df.drop("SCORE:", axis=1, inplace=True)

        return df

    def __post_init__(self):
        """
        Initializes the DataFrame based on the provided score file or directory.
        """
        if os.path.isfile(self.score_file):
            self.df = self.scorefile2df(self.score_file)
        elif os.path.isdir(self.score_file):
            dfs = [
                self.scorefile2df(os.path.join(self.score_file, f))
                for f in os.listdir(self.score_file)
                if f.endswith(".sc")
            ]
            warnings.warn(UserWarning(f"Concatenate {len(dfs)} score files"))
            self.df = pd.concat(dfs, axis=0, ignore_index=True)
        else:
            raise FileNotFoundError(f"Score file {self.score_file} not found.")

        if self.score_term not in self.df.columns:
            raise ValueError(f'Score term "{self.score_term}" not found in score file.')

    @staticmethod
    def df2dict(dfs: pd.DataFrame, k: str = "total_score") -> Tuple[Dict[Literal["score", "decoy"], Union[str, float]]]:
        """
        Converts a DataFrame into a tuple of dictionaries with scores and decoys.

        Parameters:
        - dfs (pd.DataFrame): DataFrame containing the scores.
        - k (str, optional): Column name to use as the score. Defaults to "total_score".

        Returns:
        - Tuple[Dict[Literal["score", "decoy"], Union[str, float]]]: Tuple of dictionaries containing scores
        and decoys.
        """
        t = tuple(
            {
                "score": float(dfs[dfs.index == i][k].iloc[0]),
                "decoy": str(dfs[dfs.index == i]["description"].iloc[0]),
            }
            for i in dfs.index
        )

        return t  # type: ignore

    @property
    def best_decoy(self) -> Dict[Literal["score", "decoy"], Union[str, float]]:
        """
        Returns the best decoy based on the score term.

        Returns:
        - Dict[Literal["score", "decoy"], Union[str, float]]: Dictionary containing the score and decoy of
        the best entry.
        """
        if self.df.empty:
            return {}
        return self.top(1)[0]

    def top(
        self, rank: int = 1, score_term: Optional[str] = None
    ) -> Tuple[Dict[Literal["score", "decoy"], Union[str, float]]]:
        """
        Returns the top `rank` decoys based on the specified score term.

        Parameters:
        - rank (int, optional): The number of top entries to return. Defaults to 1.
        - score_term (Optional[str], optional): The column name to use as the score. Defaults to the class
        attribute `score_term`.

        Returns:
        - Tuple[Dict[Literal["score", "decoy"], Union[str, float]]]: Tuple of dictionaries containing scores and
        decoys of the top entries.
        """
        if rank <= 0:
            raise ValueError("Rank must be greater than 0")

        # Override score_term if provided
        score_term = score_term if score_term is not None and score_term in self.df.columns else self.score_term

        df = self.df.sort_values(
            by=score_term if score_term is not None and score_term in self.df.columns else self.score_term
        ).head(rank)

        return self.df2dict(dfs=df, k=score_term)
