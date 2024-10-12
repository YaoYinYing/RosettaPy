# RosettaPy

A Python utility for wrapping Rosetta command line tools.

![GitHub License](https://img.shields.io/github/license/YaoYinYing/RosettaPy)

## CI Status

[![Python CI](https://github.com/YaoYinYing/RosettaPy/actions/workflows/CI.yml/badge.svg)](https://github.com/YaoYinYing/RosettaPy/actions/workflows/CI.yml)
[![Test with Rosetta](https://github.com/YaoYinYing/RosettaPy/actions/workflows/RosettaCI.yml/badge.svg)](https://github.com/YaoYinYing/RosettaPy/actions/workflows/RosettaCI.yml)
[![Dependabot Updates](https://github.com/YaoYinYing/RosettaPy/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/YaoYinYing/RosettaPy/actions/workflows/dependabot/dependabot-updates)

## Quality

[![codecov](https://codecov.io/gh/YaoYinYing/RosettaPy/branch/main/graph/badge.svg?token=epCTnx8SXj)](https://codecov.io/gh/YaoYinYing/RosettaPy)
[![CodeFactor](https://www.codefactor.io/repository/github/yaoyinying/rosettapy/badge)](https://www.codefactor.io/repository/github/yaoyinying/rosettapy)
[![Maintainability](https://api.codeclimate.com/v1/badges/56830e8844e9ef6075c2/maintainability)](https://codeclimate.com/github/YaoYinYing/RosettaPy/maintainability)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/4d6b6f78e59b4c38a0362d2d83fc9815)](https://app.codacy.com/gh/YaoYinYing/RosettaPy/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
![Pylint](https://github-image-cache.yaoyy.moe/badge_dir_with_uniq_name/RosettaPy/pylint/pylint_scan.svg)
![GitHub repo size](https://img.shields.io/github/repo-size/YaoYinYing/RosettaPy)

## Release

![GitHub Release](https://img.shields.io/github/v/release/YaoYinYing/RosettaPy)
![GitHub Release Date](https://img.shields.io/github/release-date/YaoYinYing/RosettaPy)

![PyPI - Format](https://img.shields.io/pypi/format/RosettaPy)
![PyPI - Version](https://img.shields.io/pypi/v/RosettaPy)
![PyPI - Status](https://img.shields.io/pypi/status/RosettaPy)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/RosettaPy)

## Python version supported

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/RosettaPy)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/RosettaPy)

## Overview

`RosettaPy` is a Python module designed to locate Rosetta biomolecular modeling suite binaries that follow a specific naming pattern and execute Rosetta in command line. The module includes:

### Building Blocks

- An object-oriented `RosettaFinder` class to search for binaries.
- A `RosettaBinary` dataclass to represent the binary and its attributes.
- A `RosettaCmdTask` dataclass to represent a single Rosetta run task.
- A `RosettaContainer` dataclass to wrap runs into Rosetta Containers.
- A `MPI_node` dataclass to manage MPI resourses. _Not Seriously Tested_
- A command-line wrapper dataclass `Rosetta` for handling Rosetta runs.
- A `RosettaScriptsVariableGroup` dataclass to represent Rosetta scripts variables.
- A general and simplified result analyzer `RosettaEnergyUnitAnalyser` to read and interpret Rosetta output score files.
- A series of example applications that follow the design elements and patterns described above.
  - PROSS
  - FastRelax
  - RosettaLigand
  - Supercharge
  - MutateRelax
  - Cartesian ddG (Analyser: `RosettaCartesianddGAnalyser`)
- Unit tests to ensure reliability and correctness.

## Features

- **Flexible Binary Search**: Finds Rosetta binaries based on their naming convention.
- **Platform Support**: Supports Linux and macOS operating systems.
- **Container Support**: Works with Docker containers running upon the official Rosetta Docker image.
- **Customizable Search Paths**: Allows specification of custom directories to search.
- **Structured Binary Representation**: Uses a dataclass to encapsulate binary attributes.
- **Command-Line Shortcut**: Provides a quick way to find binaries via the command line.
- **Available on PyPI**: Installable via `pip` without the need to clone the repository.
- **Unit Tested**: Includes tests for both classes to ensure functionality.

## Naming Convention

The binaries are expected to follow this naming pattern:

```text
rosetta_scripts[[.mode].oscompilerrelease]
```

- **Binary Name**: `rosetta_scripts` (default) or specified.
- **Mode** (optional): `default`, `mpi`, or `static`.
- **OS** (optional): `linux` or `macos`.
- **Compiler** (optional): `gcc` or `clang`.
- **Release** (optional): `release` or `debug`.

Examples of valid binary filenames:

- `rosetta_scripts` (dockerized Rosetta)
- `rosetta_scripts.linuxgccrelease`
- `rosetta_scripts.mpi.macosclangdebug`
- `rosetta_scripts.static.linuxgccrelease`

## Installation

Ensure you have Python 3.8 or higher installed.

### Install via PyPI

You can install `RosettaPy` directly from PyPI:

```bash
pip install RosettaPy -U
```

## Usage

### Building Your Own Rosetta Workflow

```python
# Imports
from RosettaPy import Rosetta, RosettaScriptsVariableGroup, RosettaEnergyUnitAnalyser
from RosettaPy.node import RosettaContainer

# Create a Rosetta object with the desired parameters
rosetta = Rosetta(
    bin="rosetta_scripts",
    flags=[...],
    opts=[
        "-in:file:s", os.path.abspath(pdb),
        "-parser:protocol", "/path/to/my_rosetta_scripts.xml",
    ],
    output_dir=...,
    save_all_together=True,
    job_id=...,

    # Some Rosetta Apps (Superchange, Cartesian ddG, etc.) may produce files in the working directory,
    # and this may not threadsafe if one runs multiple jobs in parallel in the same directory.
    # In this case, the `isolation` flag can be used to create a temporary directory for each run.
    # isolation=True,

    # Optionally, if one wishes to use the Rosetta container.
    # The image name can be found at https://hub.docker.com/r/rosettacommons/rosetta
    # run_node=RosettaContainer(image="rosettacommons/rosetta:latest")
)

# Compose your Rosetta tasks matrix
tasks = [ # Create tasks for each variant
    {
        "rsv": RosettaScriptsVariableGroup.from_dict(
            {
                "var1": ...,
                "var2": ...,
                "var3": ...,
            }
        ),
        "-out:file:scorefile": f"{variant}.sc",
        "-out:prefix": f"{variant}.",
    }
    for variant in variants
]

# Run Rosetta against these tasks
rosetta.run(inputs=tasks)

# Or create a distributed runs with structure labels (-nstruct)
options=[...] # Passing an optional list of options that will be used to all structure models
rosetta.run(nstruct=nstruct, inputs=options) # input options will be passed to all runs equally

# Use Analyzer to check the results
analyser = RosettaEnergyUnitAnalyser(score_file=rosetta.output_scorefile_dir)
best_hit = analyser.best_decoy
pdb_path = os.path.join(rosetta.output_pdb_dir, f'{best_hit["decoy"]}.pdb')

# Ta-da !!!
print("Analysis of the best decoy:")
print("-" * 79)
print(analyser.df.sort_values(by=analyser.score_term))

print("-" * 79)

print(f'Best Hit on this run: {best_hit["decoy"]} - {best_hit["score"]}: {pdb_path}')
#
```

## Environment Variables

The `RosettaFinder` searches the following directories by default:

0. `PATH`, which is commonly used in dockerized Rosetta image.
1. The path specified in the `ROSETTA_BIN` environment variable.
2. `ROSETTA3/bin`
3. `ROSETTA/main/source/bin/`
4. A custom search path provided during initialization.

## Running Tests

The project includes unit tests using Python's `pytest` framework.

1. Clone the repository (if not already done):

   ```bash
   git clone https://github.com/YaoYinYing/RosettaPy.git
   cd RosettaPy
   ```

2. Navigate to the project directory:

   ```bash
   cd RosettaPy
   ```

3. Run the tests:

   ```bash
   python -m pytest ./tests
   ```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for bug reports and feature requests.

## License

This project is licensed under the MIT License.

## Acknowledgements

- **Rosetta Commons**: The Rosetta software suite for the computational modeling and analysis of protein structures.

## Contact

For questions or support, please contact:

- **Name**: Yinying Yao
- **Email**:yaoyy.hi(a)gmail.com
