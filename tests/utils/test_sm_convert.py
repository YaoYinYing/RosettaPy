import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from rdkit import Chem

from RosettaPy.app.utils.smiles2param import (
    deprotonate_acids,
    generate_molecule,
    get_conformers,
    protonate_tertiary_amine,
    SmallMoleculeParamsGenerator,
)


# Test case for deprotonate_acids
def test_deprotonate_acids():
    smiles = "CC(=O)O"  # Acetic acid
    expected = "CC(=O)[O-]"
    result = deprotonate_acids(smiles)
    assert result == expected, f"Expected {expected}, but got {result}"


def test_protonate_tertiary_amine():
    from rdkit import Chem

    smiles = "CCN(CC)CC"  # Tertiary amine
    mol = Chem.MolFromSmiles(smiles)  # type: ignore
    result_mol = protonate_tertiary_amine(mol)
    nitrogen_idx = [atom.GetIdx() for atom in result_mol.GetAtoms() if atom.GetAtomicNum() == 7][0]  # type: ignore
    charge = result_mol.GetAtomWithIdx(nitrogen_idx).GetFormalCharge()  # type: ignore # Check nitrogen atom charge
    assert charge == 1, f"Expected charge of 1, but got {charge}"


# Test case for generate_molecule
def test_generate_molecule():
    name = "test_molecule"
    smiles = "CCO"  # Ethanol
    mol = generate_molecule(name, smiles)
    expected_num_atoms = 9  # 3 atoms (C, C, O) + 6 H atoms
    assert mol.GetNumAtoms() == expected_num_atoms, f"Expected {expected_num_atoms} atoms, but got {mol.GetNumAtoms()}"
    assert mol.GetProp("_Name") == name, f"Expected name {name}, but got {mol.GetProp('_Name')}"


# Test case for get_conformers
def test_get_conformers():
    smiles = "CCO"  # Ethanol
    mol = generate_molecule("ethanol", smiles)
    num_conformers = 5
    conf_ids = get_conformers(mol, nr=num_conformers, rmsthreshold=0.001)  # Lower the threshold to avoid pruning
    assert len(conf_ids) == num_conformers, f"Expected {num_conformers} conformers, but got {len(conf_ids)}"


@pytest.fixture
def generator():
    for k in (
        "ROSETTA_PYTHON_SCRIPTS",
        "ROSETTA",
        "ROSETTA3",
    ):
        if k in os.environ:
            os.environ.pop(k)
    return SmallMoleculeParamsGenerator(num_conformer=50, save_dir="./test_ligands/")


@pytest.mark.parametrize(
    "ROSETTA_PYTHON_SCRIPTS,ROSETTA,ROSETTA3,PYTHON_SCRIPTS_PATH",
    [
        ("", "", "", "rosetta_subdir_clone/source/scripts/python/public"),
        ("/mock/rosetta_scripts", "", "", "/mock/rosetta_scripts"),
        ("", "/mock/rosetta/", "", "/mock/rosetta/main/source/scripts/python/public/"),
        ("", "", "/mock/rosetta/main/source", "/mock/rosetta/main/source/scripts/python/public/"),
    ],
)
def test_post_init(ROSETTA_PYTHON_SCRIPTS, ROSETTA, ROSETTA3, PYTHON_SCRIPTS_PATH):

    os.environ["ROSETTA_PYTHON_SCRIPTS"] = ROSETTA_PYTHON_SCRIPTS
    os.environ["ROSETTA"] = ROSETTA
    os.environ["ROSETTA3"] = ROSETTA3

    generator = SmallMoleculeParamsGenerator(num_conformer=50, save_dir="./test_ligands/")
    assert os.path.abspath(generator._rosetta_python_script_dir) == os.path.abspath(PYTHON_SCRIPTS_PATH)


# Test smile2canon method
def test_smile2canon_valid():
    smile = "C1=CC=CC=C1"  # Benzene
    canonical_smile = SmallMoleculeParamsGenerator.smile2canon("benzene", smile)
    assert canonical_smile == "c1ccccc1"


def test_smile2canon_invalid():
    invalid_smile = "InvalidSMILES"
    with patch("builtins.print") as mock_print:
        canonical_smile = SmallMoleculeParamsGenerator.smile2canon("invalid", invalid_smile)
        assert canonical_smile is None


# Test compare_fingerprints method
def test_compare_fingerprints():
    ligands = {"LI1": "C1=CC=CC=C1", "LI2": "C1=CC(=CC=C1)O"}  # Benzene  # Phenol

    with patch("pandas.DataFrame") as mock_df:
        SmallMoleculeParamsGenerator.compare_fingerprints(ligands)

        assert mock_df.call_count == 1


# Test generate_rosetta_input method
@patch("os.makedirs")
@patch("os.chdir")
@patch("rdkit.Chem.SDWriter.write")
@patch("subprocess.Popen")
def test_generate_rosetta_input(mock_popen, mock_writer, mock_chdir, mock_makedirs, generator):
    mol_mock = MagicMock()
    mol_mock.GetConformers.return_value = [MagicMock()]
    generator._rosetta_python_script_dir = "/mock/scripts"

    generator.generate_rosetta_input(mol_mock, "test_ligand", charge=0)

    mock_makedirs.assert_called_once_with("./test_ligands//test_ligand", exist_ok=True)
    mock_chdir.assert_any_call("./test_ligands//test_ligand")
    mock_writer.assert_called_once_with(mol_mock, confId=mol_mock.GetConformers()[0].GetId())
    mock_popen.assert_called_once_with(
        [
            sys.executable,
            "/mock/scripts/molfile_to_params.py",
            "test_ligand.sdf",
            "-n",
            "test_ligand",
            "--conformers-in-one-file",
            "--recharge=0",
            "-c",
            "--clobber",
        ]
    )


# Test convert method
@patch("RosettaPy.app.utils.smiles2param.SmallMoleculeParamsGenerator.compare_fingerprints")
@patch.object(SmallMoleculeParamsGenerator, "convert_single")
def test_convert(mock_convert_single, mock_compare_fingerprints, generator):
    ligands = {"LIG1": "C1=CC=CC=C1", "LIG2": "C1=CC(=CC=C1)O"}  # Benzene  # Phenol

    generator.convert(ligands)

    mock_compare_fingerprints.assert_called_once_with(ligands)
    assert mock_convert_single.call_count == 2
