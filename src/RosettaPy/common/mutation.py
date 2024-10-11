from dataclasses import dataclass, field
import os
from typing import List, Union, ValuesView
import warnings


from Bio.PDB.PDBExceptions import PDBConstructionWarning

from Bio.PDB import PDBParser, PPBuilder  # type: ignore

warnings.filterwarnings("ignore", category=PDBConstructionWarning)


@dataclass
class Mutation:
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


@dataclass
class Chain:
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
    except AttributeError:
        warnings.warn(
            UserWarning(
                "Failed to parse PDB file. " "This might be due to the use of a deprecated version of Biopython."
            )
        )
        import Bio

        raise NotImplementedError(f"Biopython version ({Bio.__version__}) not supported.")
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
    chains: List[Chain] = field(default_factory=list)

    @property
    def all_chain_ids(self) -> List[str]:
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
        if not chain_id in self.all_chain_ids:
            raise ValueError(f"Chain {chain_id} not found in the protein sequence.")

        return next(filter(lambda x: x.chain_id == chain_id, self.chains)).sequence

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
        # # Load PDB file
        # structure = strucio.load_structure(pdb_file, model=1)

        # chains = []
        # unique_chains = np.unique(structure.chain_id)  # type: ignore # Use numpy.unique() instead of .unique() on the array
        # for chain_id in unique_chains:
        #     # Get atoms from the current chain
        #     chain_atoms = structure[structure.chain_id == chain_id]  # type: ignore

        # # Convert the chain atoms to a sequence of amino acids
        # if hasattr(struc, "to_sequence"):  # Biotite v1.0.1
        #     sequence, chain_starts = struc.to_sequence(chain_atoms)  # type: ignore
        #     sequence = str(sequence[0])
        # else:
        #     import biotite
        #     import biotite.structure.residues as res
        #     from Bio.Data import IUPACData

        #     warnings.warn(DeprecationWarning(f"Detected Biotite v{biotite.__version__}."))

        #     # Get residue codes for the current chain
        #     residue_ids = res.get_residues(chain_atoms)[1]  # Get residue indices

        #     # Convert the ProteinSequence to a string of one-letter codes
        #     sequence = "".join([IUPACData.protein_letters_3to1[str(resn).title()] for resn in residue_ids])

        # # Add the chain to the ProteinSequence
        # chains.append(Chain(chain_id=str(chain_id), sequence=str(sequence)))

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
        if not hasattr(self, "_jump_index_cache"):
            self._jump_index_cache = {}
        if (chain_id, position) in self._jump_index_cache:
            return self._jump_index_cache[(chain_id, position)]
        jump_index = 0
        for chain in self.chains:
            if chain.chain_id == chain_id:
                jump_index += position
                break
            else:
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
    mutations: List[Mutation]  # List of Mutation objects representing mutations
    wt_protein_sequence: RosettaPyProteinSequence  # ProteinSequence object to handle chain sequences
    _mutant_score: float = field(default_factory=float)
    _mutant_description: str = ""
    _pdb_fp: str = ""
    _mutant_id: str = ""
    _wt_score: float = 0.0

    def get_mutated_chain(self, chain_id) -> str:
        """
        Returns the mutated chain with the given chain_id.
        """
        sequence = list(self.wt_protein_sequence.get_sequence_by_chain(chain_id))
        for mutation in filter(lambda m: m.chain_id == chain_id, self.mutations):
            pos = mutation.position
            assert isinstance(mutation, Mutation)
            if sequence[pos - 1] != mutation.wt_res:
                raise ValueError(
                    f"Mutation {mutation} does not match the wild-type sequence on position <{pos}>:<{sequence[pos-1]}>:<{mutation.wt_res}>."
                )
            sequence[pos - 1] = mutation.mut_res

        return "".join(sequence)

    @property
    def mutated_sequence(self) -> RosettaPyProteinSequence:
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
        return f"{len(self.mutations)}\n" + "\n".join(
            [self.wt_protein_sequence.mutation_to_rosetta_format(mutation=mutation) for mutation in self.mutations]
        )

    def generate_rosetta_mutfile(self, file_path: str):
        """
        Saves all mutations to a file in Rosetta's mutfile format with calculated jump indices.

        Args:
            file_path (str): The file path to save the mutation file.
        """
        with open(file_path, "w") as file:
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


def mutants2mutfile(mutants: Union[List[Mutant], ValuesView[Mutant]], file_path: str) -> str:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    mutants_dict = {m.raw_mutant_id: m for m in mutants}
    as_mutfile = "\n".join(mutant.as_mutfile for _, mutant in mutants_dict.items())

    mutfile_content = f"total {len([_m for m in mutants_dict.values() for _m in m.mutations])}\n{as_mutfile}"
    with open(file_path, "w") as file:
        file.write(mutfile_content)
    return mutfile_content


def main():
    for pdb in os.listdir("tests/data/designed/pross"):
        seq = RosettaPyProteinSequence.from_pdb(f"tests/data/designed/pross/{pdb}")
        print(f"{pdb}: {str(seq.chains[0].sequence)}")


if __name__ == "__main__":
    wt = RosettaPyProteinSequence.from_pdb("tests/data/3fap_hf3_A_short.pdb")
    print(f"3fap_hf3_A_short.pdb: {str(wt.chains[0].sequence)}")
    main()
