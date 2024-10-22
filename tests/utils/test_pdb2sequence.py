import pytest

from RosettaPy.common.mutation import parse_pdb_sequences

# Mock PDB file paths
valid_pdb_path = "tests/data/3fap_hf3_A_short.pdb"
invalid_pdb_path = "invalid.pdb"
non_existent_pdb_path = "non_existent.pdb"


@pytest.fixture
def mock_valid_pdb_file(tmpdir):
    """
    Fixture to create a mock valid PDB file for testing.
    """

    return str(valid_pdb_path)


def test_parse_pdb_sequences_valid(mock_valid_pdb_file):
    """
    Test parsing a valid PDB file.
    """
    chains = parse_pdb_sequences(mock_valid_pdb_file)

    assert chains is not None
    assert len(chains) == 1  # Two chains A and B in the sample PDB
    assert chains[0].chain_id == "A"
    # Simplified expected sequence for chain A
    assert chains[0].sequence == "IRGWEEGVAQM"


def test_parse_pdb_sequences_non_existent_file():
    """
    Test handling of non-existent PDB file.
    """
    with pytest.raises(FileNotFoundError, match=f"PDB file {non_existent_pdb_path} not found."):
        parse_pdb_sequences(non_existent_pdb_path)


def test_parse_pdb_sequences_no_polypeptides(mocker, mock_valid_pdb_file):
    """
    Test a valid PDB file with no polypeptides (empty sequences).
    """
    mock_ppb = mocker.patch("Bio.PDB.PPBuilder.build_peptides", return_value=[])

    chains = parse_pdb_sequences(mock_valid_pdb_file)

    assert chains is not None
    assert len(chains) == 1
    # No polypeptides, so sequence should be empty
    assert chains[0].sequence == ""
