Cartesian ddG Workflow
======================

Example
-------

.. code-block:: python

   from RosettaPy.app.cart_ddg import CartesianddG
   from RosettaPy.common.mutation import Mutant, Mutation, RosettaPyProteinSequence, Chain
   from RosettaPy.node import node_picker

   wt = RosettaPyProteinSequence(chains=[Chain(chain_id="A", sequence="IRGWEEGVAQM")])
   mutant = Mutant(mutations=[Mutation(chain_id="A", position=10, wt_res="Q", mut_res="V")], wt_protein_sequence=wt)

   app = CartesianddG(
       pdb="/path/to/wt.pdb",
       mutant=mutant,
       output_dir="./outputs",
       node=node_picker("native"),
   )
   ddg = app.run(nstruct=25)
   print(ddg)