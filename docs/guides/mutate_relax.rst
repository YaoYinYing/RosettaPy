MutateRelax Workflow
====================

Example
-------

.. code-block:: python

   from RosettaPy.app.mutate_relax import MutateRelax
   from RosettaPy.common.mutation import Mutant, Mutation, RosettaPyProteinSequence, Chain
   from RosettaPy.node import node_picker

   wt = RosettaPyProteinSequence(chains=[Chain(chain_id="A", sequence="IRGWEEGVAQM")])
   mutant = Mutant(mutations=[Mutation(chain_id="A", position=10, wt_res="Q", mut_res="V")], wt_protein_sequence=wt)

   mr = MutateRelax(
       pdb="/path/to/wt.pdb",
       mutant=mutant,
       output_dir="./outputs",
       node=node_picker("native"),
   )
   df = mr.run(nstruct=10)
   print(df.head())