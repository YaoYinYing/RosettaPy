Supercharge Workflow
====================

Example
-------

.. code-block:: python

   from RosettaPy.app.supercharge import supercharge
   from RosettaPy.node import node_picker

   scores = supercharge(
       pdb="/path/to/input.pdb",
       target_pI=9.0,
       output_dir="./outputs",
       node=node_picker("native"),
   )
   print(scores.head())