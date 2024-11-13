"""
Module for processing protein chain, sequence, mutant and mutation.
"""

import os
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Union, ValuesView

import Bio
from Bio.PDB import PDBParser, PPBuilder  # type: ignore
from Bio.PDB.PDBExceptions import PDBConstructionWarning

from RosettaPy.utils.tools import squeeze

warnings.filterwarnings("ignore", category=PDBConstructionWarning)


@dataclass(frozen=True)
class Mutation:
    """
    Class representing a protein mutation.
    """

    chain_id: str  # Chain ID of the mutation
    position: int  # Position within the chain (1-based index)
    wt_res: str  # Wild-type residue (original amino acid)
    mut_res: str  # Mutated residue (new amino acid)

    def __str__(self) -> str:
        """
        String representation of the mutation in the format 'A123B',
        where A is the wild-type residue, 123 is the position, and B is the mutated residue.
        """
        return f"{self.wt_res}{self.position}{self.mut_res}"

    def to_rosetta_format(self, jump_index: int) -> str:
        """
        Converts the mutation to Rosetta mutfile format with the jump index ('A 123 B').
        The jump index is the global residue index across all chains.
        """
        return f"{self.wt_res} {jump_index} {self.mut_res}"


@dataclass(frozen=True)
class Chain:
    """
    Class representing a protein chain.
    """

    chain_id: str  # Chain ID (e.g., 'A', 'B', etc.)
    sequence: str  # Amino acid sequence of the chain

    @property
    def length(self) -> int:
        """
        Returns the length of the chain sequence.
        """
        return len(self.sequence)


def parse_pdb_sequences(pdb_filename: str) -> Union[List[Chain], None]:
    """
    Parse sequences from a PDB file using Biopython.

    Parameters:
    pdb_filename (str): Path to the PDB file.

    Returns:
    dict: A dictionary mapping chain IDs to their sequences.
    """
    if not os.path.exists(pdb_filename):
        raise FileNotFoundError(f"PDB file {pdb_filename} not found.")

    parser = PDBParser()
    try:
        structure = parser.get_structure(os.path.basename(pdb_filename)[:-4], pdb_filename)
    except AttributeError as e:
        warnings.warn(UserWarning("Failed to parse PDB file. A deprecated version of Biopython is installed"))

        raise AttributeError(f"Biopython version ({Bio.__version__}) not supported.") from e

    ppb = PPBuilder()

    if structure is None or len(structure) == 0:
        raise ValueError("Invalid PDB file.")

    chains: List[Chain] = []

    for model in structure:

        for chain in model:
            chain_id = chain.get_id()
            polypeptides = ppb.build_peptides(chain)

            seq = "".join([str(pp.get_sequence()) for pp in polypeptides])

            chains.append(Chain(chain_id=str(chain_id), sequence=seq))

        # only the first model is considered
        return chains


@dataclass
class RosettaPyProteinSequence:
    """
    Class representing a protein sequence.
    """

    chains: List[Chain] = field(default_factory=list)

    # internal variables
    _jump_index_cache: Dict = field(default_factory=dict)

    @property
    def all_chain_ids(self) -> List[str]:
        """
        Get all chain IDs.

        This property collects the ID of each chain in the current instance.
        It iterates over `self.chains`, a list of chain objects, and extracts
        the `chain_id` attribute of each chain using a list comprehension.

        :return: A list containing all chain IDs
        """
        return [chain.chain_id for chain in self.chains]

    def add_chain(self, chain_id: str, sequence: str):
        """
        Adds a new chain to the protein sequence.

        Args:
            chain_id (str): Chain ID (e.g., 'A', 'B', etc.)
            sequence (str): Amino acid sequence for the chain.
        """
        if chain_id in self.all_chain_ids:
            raise ValueError(f"Chain ID {chain_id} already exists in the protein sequence.")
        self.chains.append(Chain(chain_id=chain_id, sequence=sequence))

    def get_sequence_by_chain(self, chain_id: str) -> str:
        """
        Retrieves the sequence for a given chain ID.

        Args:
            chain_id (str): Chain ID (e.g., 'A', 'B').

        Returns:
            str: The amino acid sequence of the specified chain.

        Raises:
            ValueError: If the chain ID is not found.
        """
        if chain_id not in self.all_chain_ids:
            raise ValueError(f"Chain {chain_id} not found in the protein sequence.")

        try:
            return next(filter(lambda x: x.chain_id == chain_id, self.chains)).sequence
        except StopIteration as e:
            raise ValueError(f"Chain {chain_id} is not found in the Protein Sequence.") from e

    @classmethod
    def from_dict(cls, chains: Dict[str, str]) -> "RosettaPyProteinSequence":
        """
        Create a ProteinSequence instance from a dictionary of chain IDs and sequences.

        This class method initializes a new instance of the RosettaPyProteinSequence class
        by creating a list of Chain objects from the provided dictionary. Each Chain object
        is created with a chain ID and sequence extracted from the dictionary.

        Parameters:
        - chains (Dict[str, str]): A dictionary mapping chain IDs to their sequences.

        Returns:
        - RosettaPyProteinSequence: A new instance of the RosettaPyProteinSequence class,
          populated with Chain objects created from the provided dictionary.
        """
        return cls(chains=[Chain(chain_id=chain_id, sequence=sequence) for chain_id, sequence in chains.items()])

    @property
    def as_dict(self) -> Dict[str, str]:
        """
        Returns a dictionary representation of the RosettaPyProteinSequence object.

        This method iterates over each chain in the `self.chains` list and extracts the `chain_id`
        and `sequence` attributes of each chain. It then creates a dictionary where the keys are
        the chain IDs and the values are the corresponding chain sequences.

        :return: A dictionary containing the chain IDs as keys and their corresponding sequences as values.
        """
        return {chain.chain_id: chain.sequence for chain in self.chains}

    @classmethod
    def from_pdb(cls, pdb_file: str) -> "RosettaPyProteinSequence":
        """
        Parse a PDB file and extract the amino acid sequence for each chain.

        Args:
            pdb_file (str): Path to the PDB file.

        Returns:
            ProteinSequence: An instance of ProteinSequence populated with chains
                             from the PDB structure.
        """

        chains = parse_pdb_sequences(pdb_file)
        if chains is None:
            raise RuntimeError(f"Failed to parse PDB file {pdb_file}.")

        return cls(chains=chains)

    def calculate_jump_index(self, chain_id: str, position: int) -> int:
        """
        Calculate the jump residue index across all chains for the given chain_id and position.
        The jump index is a 1-based index across all chains in the protein sequence.

        Args:
            chain_id (str): The chain ID where the mutation occurs.
            position (int): The position within the chain (1-based index).

        Returns:
            int: The jump index across all chains.
        """

        if (chain_id, position) in self._jump_index_cache:
            return self._jump_index_cache[(chain_id, position)]
        jump_index = 0
        for chain in self.chains:
            if chain.chain_id == chain_id:
                jump_index += position
                break

            jump_index += chain.length  # Add the length of the previous chains
        return jump_index

    def mutation_to_rosetta_format(self, mutation: Mutation) -> str:
        """
        Converts a Mutation object to the Rosetta mutfile format including jump index.

        Args:
            mutation (Mutation): The mutation object to convert.

        Returns:
            str: The Rosetta format string with the calculated jump index.
        """
        jump_index = self.calculate_jump_index(mutation.chain_id, mutation.position)
        return mutation.to_rosetta_format(jump_index)


@dataclass
class Mutant:
    """
    A dataclass representing Protein Mutant
    """

    # List of Mutation objects representing mutations
    mutations: List[Mutation]
    # ProteinSequence object to handle chain sequences
    wt_protein_sequence: RosettaPyProteinSequence
    _mutant_score: float = field(default_factory=float)
    _mutant_description: str = ""
    _pdb_fp: str = ""
    _mutant_id: str = ""
    _wt_score: float = 0.0

    def get_mutated_chain(self, chain_id) -> str:
        """
        Returns the mutated chain with the given chain_id.

        Parameters:
        - chain_id: str, the identifier of the chain to be mutated.

        Returns:
        - str, the amino acid sequence of the mutated chain.
        """
        sequence = list(self.wt_protein_sequence.get_sequence_by_chain(chain_id))
        for mutation in filter(lambda m: m.chain_id == chain_id, self.mutations):
            pos = mutation.position
            assert isinstance(mutation, Mutation)
            if sequence[pos - 1] != mutation.wt_res:
                raise ValueError(
                    f"Mutation {mutation} does not match the wild-type sequence on "
                    f"position <{pos}>:<{sequence[pos - 1]}>:<{mutation.wt_res}>."
                )
            sequence[pos - 1] = mutation.mut_res

        return "".join(sequence)

    @property
    def mutated_sequence(self) -> RosettaPyProteinSequence:
        """
        Returns the mutated protein sequence.

        This property iterates through all chains in the wild-type protein sequence,
        calls the get_mutated_chain method for each chain to obtain the mutated sequence,
        and assembles a new RosettaPyProteinSequence object with the mutated chains.

        :return: A RosettaPyProteinSequence object containing the mutated chains.
        """
        return RosettaPyProteinSequence(
            chains=[
                Chain(chain_id=chain_id, sequence=self.get_mutated_chain(chain_id=chain_id))
                for chain_id in self.wt_protein_sequence.all_chain_ids
            ]
        )

    def __post_init__(self):
        """
        This method is automatically called after the initialization of the instance.
        It ensures the list of mutations is valid and the protein sequence is set.
        """
        self.mutations = squeeze(self.mutations)
        self.validate_mutations()

    def validate_mutations(self):
        """
        Validates the structure of the mutation list to ensure it's not empty and
        each element is a `Mutation` instance.
        """
        if not self.mutations:
            raise ValueError("Mutation list cannot be empty.")
        if not all(isinstance(mutation, Mutation) for mutation in self.mutations):
            raise TypeError("All elements in mutations must be instances of the Mutation class.")

    @property
    def as_mutfile(self) -> str:
        """
        Converts mutation information into the Rosetta required mutfile format.

        This method first calculates the number of mutations and uses this as the first line of the mutfile.
        Then, for each mutation, it converts the mutation into the Rosetta format.
        """
        return f"{len(self.mutations)}\n" + "\n".join(
            [self.wt_protein_sequence.mutation_to_rosetta_format(mutation=mutation) for mutation in self.mutations]
        )

    def generate_rosetta_mutfile(self, file_path: str):
        """
        Saves all mutations to a file in Rosetta's mutfile format with calculated jump indices.

        Args:
            file_path (str): The file path to save the mutation file.
        """
        # skipcq: PTC-W6004
        with open(file_path, "w", encoding="utf-8") as file:
            for mutation in self.mutations:
                rosetta_format = self.wt_protein_sequence.mutation_to_rosetta_format(mutation)
                file.write(f"{rosetta_format}\n")

    @property
    def raw_mutant_id(self) -> str:
        """
        Generates and returns a raw mutant identifier string by concatenating
        chain ID, wild-type residue, position, and mutated residue for each
        mutation in the `mutations` list.
        """
        return "_".join([str(mutation) for mutation in self.mutations])

    @property
    def mutant_score(self) -> float:
        """
        The mutant score property.
        """
        return self._mutant_score

    @mutant_score.setter
    def mutant_score(self, value: float):
        """
        Set the mutant score to a new value.
        """
        self._mutant_score = float(value)

    @classmethod
    def from_pdb(cls, wt_pdb: str, mutant_pdb: List[str]) -> List["Mutant"]:
        """
        Creates a list of `Mutant` instances by comparing the wild-type structure (wt_pdb)
        with the mutant structures (mutant_pdb). Each mutant structure generates one `Mutant` instance.

        Args:
            wt_pdb (str): Path to the wild-type PDB file.
            mutant_pdb (List[str]): List of paths to mutant PDB files.

        Returns:
            List[Mutant]: List of Mutant instances created by comparing the wild-type structure with mutants.
        """
        wt_protein = RosettaPyProteinSequence.from_pdb(wt_pdb)

        mutants = []
        for pdb_file in mutant_pdb:
            if not os.path.exists(pdb_file):
                raise FileNotFoundError(f"Could not find PDB file: {pdb_file}")
            mutant_protein = RosettaPyProteinSequence.from_pdb(pdb_file)

            mutations = []
            # Compare the sequences of wild-type and mutant
            for wt_chain in wt_protein.chains:
                mutant_chain = mutant_protein.get_sequence_by_chain(wt_chain.chain_id)

                # Iterate through residues to find differences
                for i, (wt_res, mut_res) in enumerate(zip(wt_chain.sequence, mutant_chain)):
                    if wt_res != mut_res:
                        mutation = Mutation(
                            chain_id=wt_chain.chain_id,
                            position=i + 1,  # Convert to 1-based index
                            wt_res=wt_res,
                            mut_res=mut_res,
                        )
                        mutations.append(mutation)

            # Create Mutant instance for this pdb
            mutant_instance = cls(mutations=mutations, wt_protein_sequence=wt_protein)
            mutants.append(mutant_instance)

        return mutants

    @property
    def non_xtal(self) -> "Mutant":
        """
        Returns a new Mutant instance with 'X's removed from sequences and mutation positions adjusted accordingly.
        """
        new_chains = []
        position_mappings = {}  # Maps chain_id to position mapping dict

        for chain in self.wt_protein_sequence.chains:
            seq_with_xtal = chain.sequence
            seq_without_xtal = "".join(residue for residue in seq_with_xtal if residue != "X")
            old_to_new_pos = {}
            new_position = 1

            # Build position mapping
            for old_position, residue in enumerate(seq_with_xtal, start=1):
                if residue != "X":
                    old_to_new_pos[old_position] = new_position
                    new_position += 1

            # Store the chain with the non-xtal sequence
            new_chains.append(Chain(chain.chain_id, seq_without_xtal))
            position_mappings[chain.chain_id] = old_to_new_pos

        # Adjust mutations
        new_mutations = []
        for mutation in self.mutations:
            chain_id = mutation.chain_id
            old_position = mutation.position
            position_map = position_mappings.get(chain_id, {})
            new_position = position_map.get(old_position)

            if new_position is not None:
                new_mutations.append(
                    Mutation(
                        chain_id=mutation.chain_id,
                        position=new_position,
                        wt_res=mutation.wt_res,
                        mut_res=mutation.mut_res,
                    )
                )
            else:
                # Mutation at an 'X' position, so it's ignored
                pass

        # Create new RosettaPyProteinSequence
        new_protein_sequence = RosettaPyProteinSequence(chains=new_chains)

        return Mutant(mutations=new_mutations, wt_protein_sequence=new_protein_sequence)


def mutants2mutfile(mutants: Union[List[Mutant], ValuesView[Mutant]], file_path: str) -> str:
    """
    Converts mutant information into a MutFile and writes it to the specified file.

    Parameters:
    - mutants (Union[List[Mutant], ValuesView[Mutant]]): A list or view of Mutant objects.
    - file_path (str): The path to the file where the MutFile will be written.

    Returns:
    - str: The content of the MutFile that was written to the file.
    """

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Create a dictionary mapping raw mutant IDs to their corresponding Mutant objects for easy access.
    mutants_dict = {m.raw_mutant_id: m for m in mutants}

    # Join the MutFile representation of each mutant into a single string.
    as_mutfile = "\n".join(mutant.as_mutfile for _, mutant in mutants_dict.items())

    # Generate the MutFile content including the total number of mutations.
    mutfile_content = f"total {len([_m for m in mutants_dict.values() for _m in m.mutations])}\n{as_mutfile}"

    # Write the MutFile content to the specified file.
    # skipcq: PTC-W6004
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(mutfile_content)

    return mutfile_content


def mutpdb2mutfile(wt_pdb: str, mutant_pdb_dir: str, mutfile_save_dir: str) -> Tuple[List[str], List[Mutant]]:
    """
    Method to generate mutation files for Cartesian ddG calculation based on the specified mutant PDB files.

    Parameters:
        wt_pdb (str): Path to the wild-type PDB file.
        mutant_pdb_dir (str): Directory path containing the mutant PDB files.
        mutfile_save_dir (str): Directory path where the mutation files will be saved.

    Returns:
        Tuple[List[str], List[Mutant]]: A tuple containing a list of mutation files and a list of Mutant objects.
    """
    # Collect paths to all PDB files in the mutant PDB directory
    pdbs = [os.path.join(mutant_pdb_dir, f) for f in os.listdir(mutant_pdb_dir)]

    # Generate Mutant objects from the wild-type PDB and mutant PDB files
    mutants = Mutant.from_pdb(wt_pdb, pdbs)

    # Ensure the directory for saving mutation files exists
    os.makedirs(mutfile_save_dir, exist_ok=True)

    # Create a dictionary mapping mutant IDs to Mutant objects
    mutants_dict = {m.raw_mutant_id: m for m in mutants}

    mutfiles = []

    # Generate mutation files for each mutant
    for _, m in enumerate(mutants_dict.values()):
        m_id = m.raw_mutant_id
        mutfile = os.path.join(mutfile_save_dir, f"{m_id}.mutfile")
        mutants2mutfile([m], mutfile)
        mutfiles.append(mutfile)

    # Return the list of mutation files and the list of Mutant objects
    return mutfiles, list(mutants_dict.values())


def main():
    """
    Test
    """
    for pdb in os.listdir("tests/data/designed/pross"):
        seq = RosettaPyProteinSequence.from_pdb(f"tests/data/designed/pross/{pdb}")
        print(f"{pdb}: {str(seq.chains[0].sequence)}")


if __name__ == "__main__":
    wt = RosettaPyProteinSequence.from_pdb("tests/data/3fap_hf3_A_short.pdb")
    print(f"3fap_hf3_A_short.pdb: {str(wt.chains[0].sequence)}")
    main()
