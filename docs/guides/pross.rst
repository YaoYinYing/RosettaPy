PROSS Workflow
==============

The PROSS application designs stabilizing mutations using RosettaScripts.

Example
-------

.. code-block:: python

   import os
   from RosettaPy.app.pross import PROSS
   from RosettaPy.node import node_picker

   workflow = PROSS(
       pdb="/path/to/input.pdb",
       seqres="/path/to/seqres.fasta",  # optional
       output_dir="./outputs",
       node=node_picker("native"),
   )

   # Run design; returns analysis results and artifacts in output_dir
   df = workflow.run(nstruct=5)
   print(df.head())

Notes
-----
- Requires a working `rosetta_scripts` and access to the provided protocol in the package.
- See API docs for configurable parameters.