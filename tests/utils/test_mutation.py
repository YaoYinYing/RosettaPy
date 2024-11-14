import copy
import os
from typing import Dict

import pytest

from RosettaPy.common import (
    Chain,
    Mutant,
    Mutation,
    RosettaPyProteinSequence,
    mutants2mutfile,
)

# Test cases for the Mutation class


# Sample PDB content for testing
sample_wt_pdb = "tests/data/3fap_hf3_A_short.pdb"

sample_mutant_pdb_dir = "tests/data/designed/pross/"

sample_mutant_pdbs = [
    f"{sample_mutant_pdb_dir}/3fap_hf3_A_short_0003_-0.45.pdb",
    f"{sample_mutant_pdb_dir}/3fap_hf3_A_short_0003_-1.5.pdb",
]


@pytest.fixture
def sample_wt_sequence():
    return copy.copy("IRGWEEGVAQM")


@pytest.fixture
def sample_mutation():
    return Mutation(chain_id="A", position=10, wt_res="Q", mut_res="V")


@pytest.fixture
def sample_protein_sequence(sample_wt_sequence):
    protein_sequence = RosettaPyProteinSequence(chains=[Chain(chain_id="A", sequence=sample_wt_sequence)])
    return protein_sequence


@pytest.fixture
def sample_protein_sequence_pdb():
    protein_sequence = RosettaPyProteinSequence.from_pdb(sample_wt_pdb)
    return protein_sequence


@pytest.fixture
def sample_mutant(sample_protein_sequence, sample_mutation):
    return Mutant(mutations=[sample_mutation], wt_protein_sequence=sample_protein_sequence)


@pytest.fixture
def sample_mutants() -> Dict[str, Mutant]:

    pdbs = [os.path.join(sample_mutant_pdb_dir, f) for f in os.listdir(sample_mutant_pdb_dir)]
    mutants = Mutant.from_pdb(sample_wt_pdb, pdbs)
    return {f: m for f, m in zip(pdbs, mutants)}


def test_mutation_str(sample_mutation):
    """
    Test the string representation of a Mutation.
    """
    assert str(sample_mutation) == "Q10V"


def test_mutation_rosetta_format(sample_mutation):
    """
    Test the Rosetta format conversion of a Mutation.
    """
    assert sample_mutation.to_rosetta_format(10) == "Q 10 V"


def test_protein_sequence_get_chain(sample_protein_sequence, sample_wt_sequence):
    """
    Test adding a chain to the RosettaPyProteinSequence object.
    """
    assert len(sample_protein_sequence.chains) == 1
    assert isinstance(sample_protein_sequence.get_sequence_by_chain("A"), str)
    assert sample_protein_sequence.get_sequence_by_chain("A") == sample_wt_sequence


def test_protein_sequence_add_chain():
    """
    Test adding a chain to the RosettaPyProteinSequence object.
    """
    sample_protein_sequence = RosettaPyProteinSequence()
    sample_protein_sequence.add_chain("A", "IRGWEEAVAQM")
    assert len(sample_protein_sequence.chains) == 1
    assert isinstance(sample_protein_sequence.get_sequence_by_chain("A"), str)
    assert sample_protein_sequence.get_sequence_by_chain("A") == "IRGWEEAVAQM"


def test_protein_sequence_add_exist_chain(sample_protein_sequence):
    """
    Test adding a chain to the RosettaPyProteinSequence object.
    """
    assert len(sample_protein_sequence.chains) == 1
    with pytest.raises(ValueError):
        sample_protein_sequence.add_chain("A", "IRGWEEGVCQM")


def test_protein_sequence_from_pdb(sample_wt_sequence):
    """
    Test loading a RosettaPyProteinSequence from a PDB file.
    """
    protein_sequence = RosettaPyProteinSequence.from_pdb(sample_wt_pdb)
    assert len(protein_sequence.chains) == 1
    sequence_chain_A = protein_sequence.get_sequence_by_chain("A")
    assert isinstance(sequence_chain_A, str)

    assert not isinstance(sequence_chain_A, RosettaPyProteinSequence)
    assert isinstance(sample_wt_sequence, str)

    assert sequence_chain_A == sample_wt_sequence
    """
    WTF???
    E       assert '[RosettaPyProteinSequence("IRGWEEGVAQM")]' == 'IRGWEEGVAQM'
    E
    E         - IRGWEEGVAQM
    E         + [RosettaPyProteinSequence("IRGWEEGVAQM")]

    """


def test_protein_sequence_get_sequence_by_chain(sample_protein_sequence, sample_wt_sequence):
    """
    Test retrieving a sequence from a RosettaPyProteinSequence by chain ID.
    """
    assert sample_protein_sequence.get_sequence_by_chain("A") == sample_wt_sequence


def test_protein_sequence_get_sequence_by_chain_invalid(sample_protein_sequence):
    """
    Test that retrieving a sequence from a non-existent chain raises an error.
    """
    with pytest.raises(ValueError):
        sample_protein_sequence.get_sequence_by_chain("B")


def test_mutant_creation(sample_mutant, sample_wt_sequence):
    """
    Test creating a Mutant object.
    """
    assert len(sample_mutant.mutations) == 1
    assert sample_mutant.raw_mutant_id == "Q10V"
    assert sample_mutant.wt_protein_sequence.get_sequence_by_chain("A") == sample_wt_sequence


def test_mutant_as_mutfile(sample_mutant):
    """
    Test generating the Rosetta mutfile content from the Mutant object.
    """
    mutfile_content = sample_mutant.as_mutfile
    assert "1" in mutfile_content  # Number of mutations
    assert "Q 10 V" in mutfile_content  # Mutation information


def test_mutant_from_pdb():
    """
    Test creating Mutant objects from PDB files using mock data.
    """

    mutants = Mutant.from_pdb(sample_wt_pdb, sample_mutant_pdbs)

    # Verify that two mutant instances were created
    assert len(mutants) == 2
    for mutant in mutants:
        # Ensure at least one mutation is present
        assert len(mutant.mutations) >= 1


def test_protein_sequence_construct_sources_pdb(sample_protein_sequence, sample_protein_sequence_pdb):
    assert sample_protein_sequence_pdb == sample_protein_sequence


def test_many_mutants_from_pdb(sample_mutants: Dict[str, Mutant]):
    assert len(sample_mutants) != 0


def test_mutated_sequences(sample_mutants: Dict[str, Mutant]):
    for f, m in sample_mutants.items():
        mf = RosettaPyProteinSequence.from_pdb(f)
        assert mf.chains == m.mutated_sequence.chains, f"{f}"


def test_protein_sequence_from_dict():
    chains = {"A": "AAAAAAAAAAAAB", "B": "BBBBBBBBBBBBA"}
    protein_sequence = RosettaPyProteinSequence.from_dict(chains)
    expected_sequence = RosettaPyProteinSequence(
        chains=[Chain(chain_id="A", sequence="AAAAAAAAAAAAB"), Chain(chain_id="B", sequence="BBBBBBBBBBBBA")]
    )

    assert protein_sequence == expected_sequence
    assert len(protein_sequence.chains) == 2
    assert protein_sequence.get_sequence_by_chain("A") == "AAAAAAAAAAAAB"
    with pytest.raises(ValueError):
        protein_sequence.get_sequence_by_chain("C")


def test_protein_sequence_as_dict():
    protein_sequence = RosettaPyProteinSequence(
        chains=[Chain(chain_id="A", sequence="AAAAAAAAAAAAB"), Chain(chain_id="B", sequence="BBBBBBBBBBBBA")]
    )
    assert protein_sequence.as_dict == {"A": "AAAAAAAAAAAAB", "B": "BBBBBBBBBBBBA"}


def test_mutants_to_mutfile(sample_mutants: Dict[str, Mutant]):
    mutfile = "tests/outputs/mutfile.mut"
    mutfile_content = mutants2mutfile(sample_mutants.values(), mutfile)

    assert os.path.exists(mutfile)

    for p, m in sample_mutants.items():
        assert m.as_mutfile in mutfile_content


@pytest.mark.parametrize(
    "chains_with_xtal, mutations, expected_chains_without_xtal, expected_mutations",
    [
        # Test case 1: Single chain with 'X's and a single mutation
        (
            [
                Chain(
                    "A",
                    "XXXAAAAAAAAAAXXAA",
                )
            ],  # chains_with_xtal
            [Mutation("A", 4, "A", "W")],  # mutations
            [
                Chain(
                    "A",
                    "AAAAAAAAAAAA",
                )
            ],  # expected_chains_without_xtal
            [Mutation("A", 1, "A", "W")],  # expected_mutations
        ),
        # Test case 2: Single chain with alternating 'A's and 'X's, multiple mutations
        (
            [
                Chain(
                    "A",
                    "AXAXAXAXAXAXAXAX",
                )
            ],
            [Mutation("A", 3, "A", "Y"), Mutation("A", 5, "A", "G")],
            [
                Chain(
                    "A",
                    "AAAAAAAA",
                )
            ],
            [Mutation("A", 2, "A", "Y"), Mutation("A", 3, "A", "G")],
        ),
        # Test case 3: Single chain with some 'X's, mutations should be adjusted
        (
            [
                Chain(
                    "A",
                    "AAAAXXXXAAAA",
                )
            ],
            [Mutation("A", 4, "A", "V"), Mutation("A", 8, "X", "L"), Mutation("A", 9, "A", "T")],
            [
                Chain(
                    "A",
                    "AAAAAAAA",
                )
            ],
            [Mutation("A", 4, "A", "V"), Mutation("A", 5, "A", "T")],
        ),
        # Test case 4: Multiple chains, mutations on both chains
        (
            [
                Chain(
                    "A",
                    "AXAXAXAX",
                ),
                Chain(
                    "B",
                    "XXXBBBBBB",
                ),
            ],
            [
                Mutation("A", 3, "A", "Y"),
                Mutation("B", 6, "B", "G"),
                Mutation("B", 1, "X", "L"),  # Mutation at 'X', should be ignored
            ],
            [
                Chain(
                    "A",
                    "AAAA",
                ),
                Chain(
                    "B",
                    "BBBBBB",
                ),
            ],
            [
                Mutation("A", 2, "A", "Y"),
                Mutation("B", 3, "B", "G"),
            ],
        ),
        # Test case 5: Multiple chains with 'X's at specific positions
        (
            [
                Chain(
                    "A",
                    "AAAAXXXXAAAA",
                ),
                Chain(
                    "B",
                    "CCCCXXXCCCCC",
                ),
            ],
            [
                Mutation("A", 4, "A", "V"),
                Mutation("B", 5, "X", "L"),  # Mutation at 'X', should be ignored
                Mutation("B", 8, "C", "T"),
            ],
            [
                Chain(
                    "A",
                    "AAAAAAAA",
                ),
                Chain(
                    "B",
                    "CCCCCCCCC",
                ),
            ],
            [
                Mutation("A", 4, "A", "V"),
                Mutation("B", 5, "C", "T"),
            ],
        ),
    ],
)
def test_non_xtal(chains_with_xtal, mutations, expected_chains_without_xtal, expected_mutations):
    """
    Tests the non_xtal property of the Mutant class by comparing the sequences and mutations
    before and after removing 'X's from the sequences.
    """
    # Create the initial Mutant instance
    protein_sequence = RosettaPyProteinSequence(chains_with_xtal)
    mutant = Mutant(mutations, protein_sequence)

    # Get the non_xtal version
    mutant_non_xtal = mutant.non_xtal

    # Check the sequences
    actual_chains_without_xtal = mutant_non_xtal.wt_protein_sequence.chains
    assert (
        actual_chains_without_xtal == expected_chains_without_xtal
    ), f"Expected chains {expected_chains_without_xtal}, got {actual_chains_without_xtal}"

    # Check the mutations
    for m in mutant_non_xtal.mutations:
        assert m in expected_mutations, f"Expected {m} in mutations {expected_mutations}"
