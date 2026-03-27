Getting Started
===============

Installation
------------

.. code-block:: bash

   pip install RosettaPy -U

Prerequisites
-------------

- Rosetta must be compiled and installed with a valid license.
- Ensure the `rosetta_scripts` binary is available locally or in a supported container.

Minimal Example
---------------

.. code-block:: python

   import os
   from RosettaPy import Rosetta, RosettaScriptsVariableGroup
   from RosettaPy.node import node_picker

   rosetta = Rosetta(
       bin="rosetta_scripts",
       flags=["/path/to/flags.txt"],
       opts=["-in:file:s", "/path/to/input.pdb", "-parser:protocol", "/path/to/protocol.xml"],
       output_dir="./outputs",
       job_id="demo",
       run_node=node_picker("native"),
       verbose=False,
   )

   # Optional: supply RosettaScripts variables
   rsv = RosettaScriptsVariableGroup.from_dict({
       "TASKOPERATIONS": ["OperateOnCertainResidues"],
   })

   rosetta.opts.append(rsv)
   tasks = rosetta.run(nstruct=2)

   # Each task contains the composed command; running returns execution results
   for t in tasks:
       print(t.cmd)

Where to go next
----------------

- See the guides for specific workflows like PROSS, FastRelax, RosettaLigand, Supercharge, MutateRelax, and Cartesian ddG.
- Explore the full API reference for classes and functions.