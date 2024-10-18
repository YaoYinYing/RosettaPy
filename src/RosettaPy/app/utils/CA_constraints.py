"""
Utility functions of PDB processing
"""


class PDBProcessor:
    """
    A PDBProcessor
    """

    @staticmethod
    def get_calpha_constraint_line(line: str) -> str:
        """
        Static method to process a single line of a PDB file and output a CoordinateConstraint
        for CA atoms only.

        Args:
            line (str): A single line from a PDB file.

        Returns:
            str: A formatted CoordinateConstraint string if the line contains a CA atom,
                 otherwise an empty string.
        """
        if (line.startswith("ATOM") or line.startswith("HETATM")) and line[12:16].strip() == "CA":
            # Extract necessary information based on column positions in the line
            root_aa = line[22:26].strip()  # Residue number
            root_aa_chain = line[21].strip()  # Chain identifier
            x = line[30:38].strip()  # X coordinate
            y = line[38:46].strip()  # Y coordinate
            z = line[46:54].strip()  # Z coordinate
            atom = line[12:16].strip()  # Atom type (CA in this case)
            res_num = root_aa
            chain = root_aa_chain

            # Return formatted output similar to AWK's printf
            return (
                f"CoordinateConstraint {atom} {res_num}{chain} CA {root_aa}{root_aa_chain} {x} {y} {z} HARMONIC 0 1\n"
            )
        return ""

    @staticmethod
    def convert_pdb_to_constraints(pdb_file_path: str, output_file_path: str) -> int:
        """
        Static method to convert a PDB file into a list of CoordinateConstraints for CA atoms
        and write them to an output file.

        Args:
            pdb_file_path (str): The file path to the PDB file.
            output_file_path (str): The file path to write the CA constraints.

        Returns:
            count: Sequence Length
        """
        # Open the PDB file for reading and the output file for writing
        with open(pdb_file_path, encoding="utf-8") as pdb_file, open(
            output_file_path, "w", encoding="utf-8"
        ) as output_file:
            c = 0
            for line in pdb_file:
                constraint = PDBProcessor.get_calpha_constraint_line(line)
                if constraint:  # Only write non-empty constraints
                    output_file.write(constraint)
                    c += 1
            return c
