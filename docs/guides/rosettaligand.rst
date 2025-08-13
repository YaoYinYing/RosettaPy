RosettaLigand Workflow
======================

Example
-------

.. code-block:: python

   from RosettaPy.app.rosettaligand import RosettaLigand
   from RosettaPy.node import node_picker

   rl = RosettaLigand(
       receptor_pdb="/path/to/receptor.pdb",
       ligand_params="/path/to/ligand.params",
       output_dir="./outputs",
       node=node_picker("native"),
   )
   scores = rl.run(nstruct=20)
   print(scores.sort_values("total_score").head())