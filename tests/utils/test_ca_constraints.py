import pytest

from RosettaPy.app.utils import PDBProcessor


@pytest.fixture
def sample_pdb_lines():
    # Sample lines from a PDB file (both valid and invalid)
    return [
        "ATOM    406  CA  ALA A  53      12.345  67.890  23.456  1.00 20.00           C\n",  # valid CA atom
        "ATOM    407  N   ALA A  53      12.345  67.890  23.456  1.00 20.00           N\n",  # non-CA atom
        # valid CA atom from HETATM
        "HETATM  408  CA  LIG A  54      34.567  78.901  45.678  1.00 40.00           C\n",
        "ATOM    409  CB  ALA A  53      12.345  67.890  23.456  1.00 20.00           C\n",  # non-CA atom
        "ATOM    410  CA  GLY A  54      13.345  68.890  24.456  1.00 21.00           C\n",  # valid CA atom
        "ATOM    411  O   ALA A  53      12.345  67.890  23.456  1.00 20.00           O\n",  # non-CA atom
    ]


def test_get_calpha_constraint_line_valid(sample_pdb_lines):
    # Test valid CA lines
    line = sample_pdb_lines[0]
    result = PDBProcessor.get_calpha_constraint_line(line)
    assert result == "CoordinateConstraint CA 53A CA 53A 12.345 67.890 23.456 HARMONIC 0 1\n"


def test_get_calpha_constraint_line_invalid(sample_pdb_lines):
    # Test invalid lines (non-CA atoms)
    line = sample_pdb_lines[1]
    result = PDBProcessor.get_calpha_constraint_line(line)
    assert result == ""  # Should return an empty string for non-CA atoms


def test_get_calpha_constraint_line_hetatm(sample_pdb_lines):
    # Test valid CA line from a HETATM record
    line = sample_pdb_lines[2]
    result = PDBProcessor.get_calpha_constraint_line(line)
    assert result == "CoordinateConstraint CA 54A CA 54A 34.567 78.901 45.678 HARMONIC 0 1\n"


def test_convert_pdb_to_constraints(tmpdir, sample_pdb_lines):
    # Test the conversion of a mock PDB to constraint file
    pdb_file_path = tmpdir.join("test.pdb")
    output_file_path = tmpdir.join("constraints.txt")

    # Write sample PDB content to the temporary PDB file
    with open(pdb_file_path, "w") as f:
        f.writelines(sample_pdb_lines)

    # Run the conversion function
    count = PDBProcessor.convert_pdb_to_constraints(str(pdb_file_path), str(output_file_path))

    # Check that the correct number of constraints were written (3 valid CA atoms)
    assert count == 3

    # Check the contents of the output file
    with open(output_file_path) as f:
        contents = f.read()

    expected_output = (
        "CoordinateConstraint CA 53A CA 53A 12.345 67.890 23.456 HARMONIC 0 1\n"
        "CoordinateConstraint CA 54A CA 54A 34.567 78.901 45.678 HARMONIC 0 1\n"
        "CoordinateConstraint CA 54A CA 54A 13.345 68.890 24.456 HARMONIC 0 1\n"
    )

    assert contents == expected_output


def test_no_ca_atoms_in_pdb(tmpdir):
    # Test when no CA atoms are present in the PDB
    pdb_file_path = tmpdir.join("no_ca.pdb")
    output_file_path = tmpdir.join("no_ca_constraints.txt")

    # Write a PDB with no CA atoms
    no_ca_atoms = [
        "ATOM    406  N   ALA A  53      12.345  67.890  23.456  1.00 20.00           N\n",
        "ATOM    407  CB  ALA A  53      12.345  67.890  23.456  1.00 20.00           C\n",
    ]

    with open(pdb_file_path, "w") as f:
        f.writelines(no_ca_atoms)

    # Run the conversion function
    count = PDBProcessor.convert_pdb_to_constraints(str(pdb_file_path), str(output_file_path))

    # Check that no constraints were written
    assert count == 0

    with open(output_file_path) as f:
        contents = f.read()

    assert contents == ""  # No constraints should be written
