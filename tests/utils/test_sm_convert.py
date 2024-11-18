import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from rdkit import Chem

from RosettaPy.app.utils.smiles2param import (
    SmallMoleculeParamsGenerator,
    SmallMoleculeSimilarityChecker,
    deprotonate_acids,
    generate_molecule,
    get_conformers,
    protonate_tertiary_amine,
)
from RosettaPy.utils.task import RosettaCmdTask
from RosettaPy.utils.tools import tmpdir_manager


# Test case for deprotonate_acids
def test_deprotonate_acids():
    smiles = "CC(=O)O"  # Acetic acid
    expected = "CC(=O)[O-]"
    result = deprotonate_acids(smiles)
    assert result == expected, f"Expected {expected}, but got {result}"


def test_protonate_tertiary_amine():

    smiles = "CCN(CC)CC"  # Tertiary amine
    mol = Chem.MolFromSmiles(smiles)  # type: ignore
    result_mol = protonate_tertiary_amine(mol)
    nitrogen_idx = [atom.GetIdx() for atom in result_mol.GetAtoms() if atom.GetAtomicNum() == 7][  # type: ignore
        0
    ]  # type: ignore
    # type: ignore # Check nitrogen atom charge
    charge = result_mol.GetAtomWithIdx(nitrogen_idx).GetFormalCharge()  # type: ignore
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
    # Lower the threshold to avoid pruning
    conf_ids = get_conformers(mol, nr=num_conformers, rmsthreshold=0.001)
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
    with tmpdir_manager() as test_ligands:
        return SmallMoleculeParamsGenerator(num_conformer=50, save_dir=test_ligands)


@pytest.mark.parametrize(
    "ROSETTA_PYTHON_SCRIPTS,ROSETTA,ROSETTA3,PYTHON_SCRIPTS_PATH",
    [
        ("", "", "", "rosetta_python_script_dir/source/scripts/python/public"),
        ("/mock/rosetta_scripts", "", "", "/mock/rosetta_scripts"),
        ("", "/mock/rosetta/", "", "/mock/rosetta/main/source/scripts/python/public/"),
        ("", "", "/mock/rosetta/main/source", "/mock/rosetta/main/source/scripts/python/public/"),
    ],
)
def test_post_init(ROSETTA_PYTHON_SCRIPTS, ROSETTA, ROSETTA3, PYTHON_SCRIPTS_PATH):

    os.environ["ROSETTA_PYTHON_SCRIPTS"] = ROSETTA_PYTHON_SCRIPTS
    os.environ["ROSETTA"] = ROSETTA
    os.environ["ROSETTA3"] = ROSETTA3

    with tmpdir_manager() as test_ligands:
        generator = SmallMoleculeParamsGenerator(num_conformer=50, save_dir=test_ligands)
        assert os.path.abspath(generator._rosetta_python_script_dir) == os.path.abspath(PYTHON_SCRIPTS_PATH)


# Test smile2canon method
def test_smile2canon_valid():
    smile = "C1=CC=CC=C1"  # Benzene
    canonical_smile = SmallMoleculeSimilarityChecker.smile2canon("benzene", smile)
    assert canonical_smile == "c1ccccc1"


def test_smile2canon_invalid():
    invalid_smile = "InvalidSMILES"
    with patch("builtins.print") as mock_print:
        canonical_smile = SmallMoleculeSimilarityChecker.smile2canon("invalid", invalid_smile)
        assert canonical_smile is None


# Test compare_fingerprints method
def test_compare_fingerprints():
    ligands = {"LI1": "C1=CC=CC=C1", "LI2": "C1=CC(=CC=C1)O"}  # Benzene  # Phenol

    with patch("pandas.DataFrame") as mock_df:
        SmallMoleculeSimilarityChecker(ligands=ligands).compare_fingerprints()

        assert mock_df.call_count == 1


@patch("rdkit.Chem.SDWriter.write")
def test_generate_rosetta_input(mock_writer, generator):
    mol_mock = MagicMock()
    mol_mock.GetConformers.return_value = [MagicMock()]
    generator._rosetta_python_script_dir = "/mock/scripts"

    with patch("subprocess.Popen", return_value=("", "")) as mock_popen:
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Output", "")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        actural_task = generator.generate_rosetta_input(mol_mock, "test_ligand", charge=0)
        save_dir = generator.save_dir

        expected_task = RosettaCmdTask(
            cmd=[
                sys.executable,
                "/mock/scripts/molfile_to_params.py",
                os.path.join(save_dir, "test_ligand.sdf"),
                "-n",
                "test_ligand",
                "--conformers-in-one-file",
                "--recharge=0",
                "-c",
                "--clobber",
            ],
            base_dir=save_dir,
            task_label="test_ligand",
        )

        assert actural_task == expected_task

        mock_writer.assert_called_once_with(mol_mock, confId=mol_mock.GetConformers()[0].GetId())


# Test convert method
@patch("RosettaPy.app.utils.smiles2param.SmallMoleculeSimilarityChecker.compare_fingerprints")
@patch.object(SmallMoleculeParamsGenerator, "convert_single")
def test_convert(mock_convert_single, mock_compare_fingerprints, generator):
    ligands = {"LIG1": "C1=CC=CC=C1", "LIG2": "C1=CC(=CC=C1)O"}  # Benzene  # Phenol

    generator.convert(ligands)

    mock_compare_fingerprints.assert_called_once()
    assert mock_convert_single.call_count == 2


@pytest.mark.integration
@pytest.mark.parametrize("n_jobs", [1, 3])
def test_main_test(n_jobs):
    from RosettaPy.app.utils.smiles2param import main

    main(n_jobs)
