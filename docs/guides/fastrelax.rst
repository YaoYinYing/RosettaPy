FastRelax Workflow
==================

Example
-------

.. code-block:: python

   from RosettaPy.app.fastrelax import FastRelax
   from RosettaPy.node import node_picker

   fr = FastRelax(
       pdb="/path/to/input.pdb",
       output_dir="./outputs",
       node=node_picker("native"),
   )
   scores = fr.run(nstruct=10)
   print(scores.describe())