"""
Utility functions of Small Molecule Comformer Sampling
"""

# pylint: disable=no-member
# pylint: disable=unused-variable
# pylint: disable=invalid-name


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
import subprocess
from dataclasses import dataclass
from typing import Dict, Optional
import warnings

import pandas as pd

from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import AllChem
from rdkit.Chem.Fingerprints import FingerprintMols
from RosettaPy import RosettaBinary
from RosettaPy.utils.repository import setup_rosetta_python_scripts

from RosettaPy.utils.escape import Colors as C


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
        for n in ntert:
            # Convert the molecule to a canonical SMILES string representation
            molStrings = Chem.MolToSmiles(mol, isomericSmiles=True)  # type: ignore
            # Get the symbol and formal charge of the nitrogen atom
            atomSymbol9 = mol.GetAtomWithIdx(n[0]).GetSymbol()
            formalCharge9 = mol.GetAtomWithIdx(n[0]).GetFormalCharge()
            # Calculate the molecular formula for verification
            test7 = Chem.AllChem.CalcMolFormula(mol)  # type: ignore
            # Set the formal charge of the nitrogen atom to +1 to protonate it
            mol.GetAtomWithIdx(n[0]).SetFormalCharge(1)
            # Update the property cache of the molecule to reflect the changes
            mol.UpdatePropertyCache()
            # Return the modified molecule
            return mol
    else:
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
    LIGAND_NAME = name
    m = Chem.MolFromSmiles(smiles)  # type: ignore
    # print(m)
    # m = protonate_tertiary_amine(m)
    # print(m)
    m_h = Chem.AddHs(m)  # type: ignore
    # Embeed the geometry
    AllChem.EmbedMolecule(m_h, AllChem.ETKDG())  # type: ignore
    # Setting name of molecule
    m_h.SetProp("_Name", LIGAND_NAME)
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
    return AllChem.EmbedMultipleConfs(
        mol,
        numConfs=nr,
        useBasicKnowledge=True,
        pruneRmsThresh=rmsthreshold,  # type: ignore
        useExpTorsionAnglePrefs=True,
    )


#
# def select_molecule(molecule):
# 	new_i = widgets.interactive(print_city, country=countryW, city=geoWs[country['new']])
# 	i.children = new_i.children
#
#
# def on_change(change):
# 	from IPython.display import clear_output
# 	clear_output()
# 	molconf_widget.value = 'Number of conformers: ' + str(mols[change['new']].GetNumConformers())
# 	display(container)
# 	interact(drawit, m=fixed(mols[change['new']]), p=fixed(p), confId=(0, mols[change['new']].GetNumConformers() - 1));


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
            self._rosetta_python_script_dir = setup_rosetta_python_scripts()
            print(f"Setup $ROSETTA_PYTHON_SCRIPTS from Rosetta Repository = {self._rosetta_python_script_dir}")
            return
        except RuntimeError as e:
            raise RuntimeError("Could not find or setup a proper directory for ROSETTA_PYTHON_SCRIPTS.") from e

    @staticmethod
    def smile2canon(name, ds):
        try:
            return Chem.CanonSmiles(ds)

        except Exception as e:
            print(f"Drop Invalid SMILES:{name} {ds}: {e}")
            return None

    @staticmethod
    def compare_fingerprints(ligands: Dict[str, str]):
        c_smiles = {}
        for i, ds in ligands.items():
            c = SmallMoleculeParamsGenerator.smile2canon(i, ds)
            if c is not None:
                c_smiles.update({i: c})

        print(c_smiles)

        # Create a list of molecules
        ms = {i: Chem.MolFromSmiles(v) for i, v in c_smiles.items()}  # type: ignore

        # Generate fingerprints for each molecule
        fps = {i: FingerprintMols.FingerprintMol(x) for i, x in ms.items()}

        # Prepare lists for the DataFrame
        qu, ta, sim = [], [], []

        # Compare all fingerprints pairwise without duplicates
        c_smiles_v = list(c_smiles.values())
        fpsv = list(fps.values())

        for i, (n, fp) in enumerate(fps.items()):
            try:
                s = DataStructs.BulkTanimotoSimilarity(fp, fpsv[i + 1 :])
            except ValueError as e:
                print(f"Ignore molecule `{n}` for fingerprints pairwise due to: {e}")
                continue
            print(c_smiles[n], c_smiles_v[i + 1 :])
            for m in range(len(s)):
                qu.append(c_smiles[n])
                ta.append(c_smiles_v[i + 1 :][m])
                sim.append(s[m])

        # Build the DataFrame and sort it
        d = {"query": qu, "target": ta, "Similarity": sim}
        df_final = pd.DataFrame(data=d)
        df_final = df_final.sort_values("Similarity", ascending=False)
        print(df_final)

    def convert_single(self, ligand_name: str, smiles: str):

        updated_ligands = deprotonate_acids(smiles)
        mol = generate_molecule(ligand_name, updated_ligands)

        print(C.light_purple(C.bold(C.negative(f"Deprotonated --- {ligand_name}"))))
        print(f'{C.red(C.bold(C.italic(f"Before: ")))} {C.red(C.bold(C.negative("-")))} {C.red(C.bold(smiles))}')
        print(
            f'{C.green(C.bold(C.italic(f"After:  ")))} {C.green(C.bold(C.negative("+")))} {C.green(C.bold(updated_ligands))}'
        )

        # Processing ligands

        cids = get_conformers(mol, self.num_conformer, 0.1)
        # Perform a short minimization and compute the RMSD
        for cid in cids:
            _ = AllChem.MMFFOptimizeMolecule(mol, confId=cid)  # type: ignore
        rmslist = []
        AllChem.AlignMolConformers(mol, RMSlist=rmslist)  # type: ignore

        self.generate_rosetta_input(mol=mol, name=ligand_name, charge=Chem.GetFormalCharge(mol))  # type: ignore

    def convert(self, ligands: Dict[str, str]):
        """
        Converts ligands from SMILES strings to molecules and generates similarity metrics.

        Args:
            ligands (Dict[str, str]): A dictionary mapping names to SMILES strings.
        """

        SmallMoleculeParamsGenerator.compare_fingerprints(ligands)

        for i, v in ligands.items():
            self.convert_single(ligand_name=i, smiles=v)

    def generate_rosetta_input(self, mol, name, charge=0):
        """
        Generates Rosetta input files for a given molecule.

        Args:
            mol: The molecule object.
            name (str): The name of the molecule.
            charge (int): The formal charge of the molecule.
        """
        os.makedirs(f"{self.save_dir}/{name}", exist_ok=True)
        wd = os.getcwd()
        os.chdir(f"{self.save_dir}/{name}")
        w = Chem.SDWriter(f"{name}.sdf")  # type: ignore
        for i in mol.GetConformers():
            w.write(mol, confId=i.GetId())
        w.close()

        exe = [
            sys.executable,
            os.path.join(self._rosetta_python_script_dir, "molfile_to_params.py"),
            f"{name}.sdf",
            "-n",
            name,
            "--conformers-in-one-file",
            f"--recharge={str(charge)}",
            "-c",
            "--clobber",
        ]
        print(f'Launching script: {" ".join(exe)}')
        subprocess.Popen(exe)
        print(exe)
        os.chdir(wd)


def main():

    for k in (
        "ROSETTA_PYTHON_SCRIPTS",
        "ROSETTA",
        "ROSETTA3",
    ):
        if k in os.environ:
            os.environ.pop(k)

    converter = SmallMoleculeParamsGenerator(save_dir="tests/outputs/ligands")
    converter.convert(
        {
            "OPY": "C1=CC(=CC=C1C[C@@H](C(=O)O)N)OP(=O)(O)O",  # O-Phospho-L-tyrosine
            "ASA": "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
            "CAF": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
        }
    )


if __name__ == "__main__":
    main()
