"""
Utility functions of Small Molecule Comformer Sampling
"""

# pylint: disable=no-member


# # Design of small molecule binders
#

# Data were obtained from pubchem
#
# (https://pubchem.ncbi.nlm.nih.gov/compound/3345#section=Top)

# The python script for the generating the parameter file has to be set:
# python2.7 /Users/pgreisen/Programs/Rosetta/Rosetta/main/source/scripts/python/public/molfile_to_params.py
#


import os
import sys
import warnings
from dataclasses import dataclass
from typing import Dict

import pandas as pd
from joblib import Parallel, delayed
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from rdkit.Chem.Fingerprints import FingerprintMols  # type: ignore

from RosettaPy import Rosetta
from RosettaPy.utils import (RosettaCmdTask, partial_clone, print_diff, render,
                             zip_render)


# Functions
def deprotonate_acids(smiles):
    """
    Deprotonate carboxylic acids function.

    This function uses a SMARTS reaction to deprotonate the carboxylic acid group in a given molecule,
    effectively converting it into its corresponding carboxylate ion.

    Parameters:
    - smiles: A string representing the SMILES format of the molecule.

    Returns:
    - A string representing the SMILES format of the deprotonated molecule.
    """
    # Define the reaction to deprotonate carboxylic acids
    deprotonate_cooh = AllChem.ReactionFromSmarts("[C:1](=[O:2])-[OH1:3]>>[C:1](=[O:2])-[O-H0:3]")  # type: ignore
    # Convert SMILES to Mol object
    mol = Chem.MolFromSmiles(smiles)  # type: ignore
    # Execute the deprotonation reaction
    m_deprot = deprotonate_cooh.RunReactants((mol,))
    # Check if the reaction product exists
    if len(m_deprot) != 0:
        # Convert the deprotonated molecule back to SMILES format
        smiles = Chem.MolToSmiles(m_deprot[0][0])  # type: ignore
    return smiles


def protonate_tertiary_amine(mol):
    """
    Protonates a tertiary amine in the given molecule.

    A tertiary amine is identified by the presence of a nitrogen atom bonded to three carbon atoms.
    This function searches for such a structure and protonates the nitrogen atom, increasing its formal charge by 1.

    Parameters:
    mol: The molecule object representing the chemical structure to be modified.

    Returns:
    The modified molecule object with the protonated tertiary amine, if applicable.
    """
    # Define a pattern to match non-tertiary amine atoms
    patt_1 = Chem.MolFromSmarts("[^3]")  # type: ignore
    print(patt_1)  # Debug output to show the pattern
    # Find all matches of the pattern in the molecule
    matches_1 = mol.GetSubstructMatches(patt_1)

    # Define a pattern to match nitrogen atoms
    patt_2 = Chem.MolFromSmarts("[#7]")  # type: ignore
    # Find all matches of the pattern in the molecule
    matches_2 = mol.GetSubstructMatches(patt_2)

    # If both patterns match at least once, proceed to find common matches
    if len(matches_1) > 0 and len(matches_2) > 0:
        # Convert lists of matches to sets for efficient intersection operation
        a = set(matches_1)
        b = set(matches_2)
        # Find the intersection, which represents the tertiary amines
        ntert = a.intersection(b)
        # Iterate over the identified tertiary amine sites to modify the molecule
        print(f'{render(len(ntert), "purple-bold-negative")} tertiary amines found:')
        if len(ntert) <= 0:
            return mol

        for n in ntert:
            # Convert the molecule to a canonical SMILES string representation
            mol_strings = Chem.MolToSmiles(mol, isomericSmiles=True)  # type: ignore
            # Get the symbol and formal charge of the nitrogen atom
            atom_symbol = mol.GetAtomWithIdx(n[0]).GetSymbol()
            formal_charge = mol.GetAtomWithIdx(n[0]).GetFormalCharge()
            # Calculate the molecular formula for verification
            mol_formula = Chem.AllChem.CalcMolFormula(mol)  # type: ignore
            zip_render(
                labels={
                    "Molecular Strings": mol_strings,
                    "Atom Symbol": atom_symbol,
                    "Formal Charge": formal_charge,
                    "Molecular Formula": mol_formula,
                },
                label_colors=["yellow", "blue", "green", "red"],
            )

            # Set the formal charge of the nitrogen atom to +1 to protonate it
            mol.GetAtomWithIdx(n[0]).SetFormalCharge(1)
            # Update the property cache of the molecule to reflect the changes
            mol.UpdatePropertyCache()
            # Return the modified molecule
            return mol
    else:
        print(f'{render("No", "purple-bold-negative")} tertiary amines found:')
        # If no matches are found, return the original molecule without modification
        return mol


def generate_molecule(name, smiles):
    """
    Generate the 3D molecular structure based on input SMILES
    ----------
    name : name of molecule
    smiles: SMILES of molecule
    Returns
    ----------
    Mol

    """
    m = Chem.MolFromSmiles(smiles)  # type: ignore

    try:
        m = protonate_tertiary_amine(m)
    except Exception:
        warnings.warn("Could not protonate tertiary amine")

    m_h = Chem.AddHs(m)  # type: ignore
    # Embeed the geometry
    AllChem.EmbedMolecule(m_h, AllChem.ETKDG())  # type: ignore
    # Setting name of molecule
    m_h.SetProp("_Name", name)
    return m_h


def get_conformers(mol, nr=500, rmsthreshold=0.1):
    """
    Generate 3D conformers of molecule using CSD-method
    ----------
    mol : RKdit molecule
    nr : integer, number of conformers to be generate
    rmsthreshold : float, prune conformers that are less rms away from another conf
    Returns
    ----------
    List of new conformation IDs
    """
    # Generate conformers on the CSD-method
    return AllChem.EmbedMultipleConfs(  # type: ignore
        mol,
        numConfs=nr,
        useBasicKnowledge=True,
        pruneRmsThresh=rmsthreshold,  # type: ignore
        useExpTorsionAnglePrefs=True,
    )


@dataclass
class SmallMoleculeParamsGenerator:
    """
    A class for generating small molecule parameters.

    This class is responsible for converting ligands into a format usable by Rosetta, including preprocessing
    ligands and generating molecular parameters.

    Attributes:
        num_conformer (int): The number of conformers to generate.
        save_dir (str): The directory where the generated files will be saved.
    """

    num_conformer: int = 100
    save_dir: str = "./ligands/"

    # Internal use
    _rosetta_python_script_dir: str = ""

    def __post_init__(self):
        """
        Post-initialization method to set up the save directory and determine the Rosetta Python scripts directory.
        """
        os.makedirs(self.save_dir, exist_ok=True)

        if os.environ.get("ROSETTA_PYTHON_SCRIPTS"):

            self._rosetta_python_script_dir = os.environ["ROSETTA_PYTHON_SCRIPTS"]
            print(f"Find $ROSETTA_PYTHON_SCRIPTS = {self._rosetta_python_script_dir}")
            return

        if os.environ.get("ROSETTA"):
            self._rosetta_python_script_dir = os.path.join(os.environ["ROSETTA"], "main/source/scripts/python/public/")
            print(f"Find $ROSETTA_PYTHON_SCRIPTS (ROSETTA) = {self._rosetta_python_script_dir}")
            return
        if os.environ.get("ROSETTA3"):
            self._rosetta_python_script_dir = os.path.join(os.environ["ROSETTA3"], "scripts/python/public/")
            print(f"Find $ROSETTA_PYTHON_SCRIPTS (ROSETTA3) = {self._rosetta_python_script_dir}")
            return

        warnings.warn(
            RuntimeWarning(
                "Could not find or setup a proper directory like ROSETTA_PYTHON_SCRIPTS, ROSETTA, or ROSETTA3. "
                "Maybe in Dockerized? Try setup from repository..."
            )
        )

        try:
            self._rosetta_python_script_dir = partial_clone(
                target_dir="rosetta_python_script_dir",
                subdirectory_to_clone="source/scripts/python/public",
                subdirectory_as_env="source/scripts/python/public",
                env_variable="ROSETTA_PYTHON_SCRIPTS",
            )
            print(f"Setup $ROSETTA_PYTHON_SCRIPTS from Rosetta Repository = {self._rosetta_python_script_dir}")
            return
        except RuntimeError as e:
            raise RuntimeError("Could not find or setup a proper directory for ROSETTA_PYTHON_SCRIPTS.") from e

    @staticmethod
    def smile2canon(name, ds):
        """
        Converts a SMILES string to its canonical form.

        This method attempts to convert the provided SMILES string (ds) into its Canonical SMILES format.
        If successful, it returns the canonical SMILES string; otherwise, if the conversion fails
        (e.g., ds is not a valid SMILES string),
        it prints an error message and returns None.

        Parameters:
        name (str): The name of the compound, used for identifying the compound in error messages.
        ds (str): The SMILES string to be converted to canonical form.

        Returns:
        str | None: The canonical SMILES string if successful, or None if the conversion fails.
        """
        try:
            return Chem.CanonSmiles(ds)

        except Exception as e:
            print(f"Drop Invalid SMILES:{name} {ds}: {e}")
            return None

    @staticmethod
    def compare_fingerprints(ligands: Dict[str, str]):
        """
        Compare the similarity of molecular fingerprints of a given set of ligands.

        Parameters:
        ligands: Dict[str, str] A dictionary containing the ligand identifiers as keys and their
        corresponding molecular structures (SMILES format) as values.

        Returns:
        None
        """
        # Convert each ligand's SMILES format to its canonical SMILES format
        canon_smiles = {}
        for i, smiles_string in ligands.items():
            canon_smiles_string = SmallMoleculeParamsGenerator.smile2canon(i, smiles_string)
            if canon_smiles_string is not None:
                canon_smiles.update({i: canon_smiles_string})

        print(canon_smiles)

        # Create a list of molecules
        mols = {k: Chem.MolFromSmiles(v) for k, v in canon_smiles.items()}

        # Generate fingerprints for each molecule
        fingerprints = {k: FingerprintMols.FingerprintMol(v) for k, v in mols.items()}

        # Prepare lists for the DataFrame
        qu, ta, sim = [], [], []

        # Compare all fingerprints pairwise without duplicates
        c_smiles_v = list(canon_smiles.values())
        fpsv = list(fingerprints.values())

        for i, (lig_name, fingerprint) in enumerate(fingerprints.items()):
            try:
                s = DataStructs.BulkTanimotoSimilarity(fingerprint, fpsv[i + 1:])
            except ValueError as e:
                print(f"Ignore molecule `{lig_name}` for fingerprints pairwise due to: {e}")
                continue
            print(canon_smiles[lig_name], c_smiles_v[i + 1:])
            for j, _s in enumerate(s):
                qu.append(canon_smiles[lig_name])
                ta.append(c_smiles_v[i + 1:][j])
                sim.append(_s)

        # Build the DataFrame and sort it
        df_final = pd.DataFrame(data={"query": qu, "target": ta, "Similarity": sim})
        df_final = df_final.sort_values("Similarity", ascending=False)
        print(df_final)

    def convert_single(self, ligand_name: str, smiles: str):
        """
        Process a single ligand, including deprotonation, generation of molecular structures, energy
        minimization, and generation of Rosetta input files.

        Parameters:
        - ligand_name: str, the name of the ligand.
        - smiles: str, the SMILES representation of the ligand's structure.

        Returns:
        None
        """

        # Deprotonate the ligand based on its SMILES representation and update the ligand structure.
        updated = deprotonate_acids(smiles)
        # Generate a molecular structure object for the updated ligand.
        mol = generate_molecule(ligand_name, updated)

        # Print the deprotonation result and the before and after SMILES representations.
        print_diff(
            f"Deprotonation - {ligand_name}", {"Before:": smiles, "After:": updated}, ["red", "green"], "light_purple"
        )

        # Generate conformers for the ligand molecule and perform energy minimization.
        cids = get_conformers(mol, self.num_conformer, 0.1)
        # Perform a short minimization and compute the RMSD
        for cid in cids:
            _ = AllChem.MMFFOptimizeMolecule(mol, confId=cid)  # type: ignore
        rmslist = []
        AllChem.AlignMolConformers(mol, RMSlist=rmslist)  # type: ignore

        # Generate the Rosetta input file for the processed ligand.
        self.generate_rosetta_input(mol=mol, name=ligand_name, charge=Chem.GetFormalCharge(mol))  # type: ignore

    def convert(self, ligands: Dict[str, str], n_jobs: int = 1):
        """
        Converts ligands from SMILES strings to molecules and generates similarity metrics.

        Args:
            ligands (Dict[str, str]): A dictionary mapping names to SMILES strings.
        """

        SmallMoleculeParamsGenerator.compare_fingerprints(ligands)

        Parallel(n_jobs=n_jobs, verbose=101)(
            delayed(self.convert_single)(ligand_name=i, smiles=v) for i, v in ligands.items()
        )

    def generate_rosetta_input(self, mol, name, charge=0):
        """
        Generates Rosetta input files for a given molecule.

        Args:
            mol: The molecule object.
            name (str): The name of the molecule.
            charge (int): The formal charge of the molecule.
        """
        task_dir = os.path.abspath(self.save_dir)
        sdf_path = os.path.join(task_dir, f"{name}.sdf")

        w = Chem.SDWriter(sdf_path)  # type: ignore
        for i in mol.GetConformers():
            w.write(mol, confId=i.GetId())
        w.close()

        return Rosetta.execute(
            RosettaCmdTask(
                cmd=[
                    sys.executable,
                    os.path.join(self._rosetta_python_script_dir, "molfile_to_params.py"),
                    f"{sdf_path}",
                    "-n",
                    name,
                    "--conformers-in-one-file",
                    f"--recharge={str(charge)}",
                    "-c",
                    "--clobber",
                ],
                base_dir=task_dir,
                task_label=name,
            )
        )


def main(
    n_jobs: int = 3,
):
    """
    Main function to remove specific keys from the environment variables and convert small molecule parameters.

    This function first removes three keys related to Rosetta from the environment variables to prevent potential
    configuration conflicts.
    It then uses an instance of SmallMoleculeParamsGenerator to generate and save parameter files for small molecules.
    These parameter files are typically used in molecular modeling and simulations.
    """

    # Remove Rosetta-related keys from the environment variables to avoid potential configuration conflicts
    for k in (
        "ROSETTA_PYTHON_SCRIPTS",
        "ROSETTA",
        "ROSETTA3",
    ):
        if k in os.environ:
            os.environ.pop(k)

    # Initialize the SmallMoleculeParamsGenerator and convert the specified molecules
    converter = SmallMoleculeParamsGenerator(save_dir="tests/outputs/ligands")
    converter.convert(
        {
            # O-Phospho-L-tyrosine
            "OPY": "C1=CC(=CC=C1C[C@@H](C(=O)O)N)OP(=O)(O)O",
            "ASA": "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
            "CAF": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
        },
        n_jobs=n_jobs,
    )


if __name__ == "__main__":
    main()
