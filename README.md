# RosettaPy

A Python utility for wrapping Rosetta command line tools.

## License
![GitHub License](https://img.shields.io/github/license/YaoYinYing/RosettaPy)

## CI Status

[![Python CI](https://github.com/YaoYinYing/RosettaPy/actions/workflows/CI.yml/badge.svg)](https://github.com/YaoYinYing/RosettaPy/actions/workflows/CI.yml)
[![Test in Rosetta Container](https://github.com/YaoYinYing/RosettaPy/actions/workflows/RosettaCI.yml/badge.svg)](https://github.com/YaoYinYing/RosettaPy/actions/workflows/RosettaCI.yml)
[![Dependabot Updates](https://github.com/YaoYinYing/RosettaPy/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/YaoYinYing/RosettaPy/actions/workflows/dependabot/dependabot-updates)
[![Pylint](https://github.com/YaoYinYing/RosettaPy/actions/workflows/lint_badge.yml/badge.svg)](https://github.com/YaoYinYing/RosettaPy/actions/workflows/lint_badge.yml)
[![Bare Test with Rosetta Container Node](https://github.com/YaoYinYing/RosettaPy/actions/workflows/CI_Container.yml/badge.svg)](https://github.com/YaoYinYing/RosettaPy/actions/workflows/CI_Container.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/YaoYinYing/RosettaPy/main.svg)](https://results.pre-commit.ci/latest/github/YaoYinYing/RosettaPy/main)


## Quality

[![codecov](https://codecov.io/gh/YaoYinYing/RosettaPy/branch/main/graph/badge.svg?token=epCTnx8SXj)](https://codecov.io/gh/YaoYinYing/RosettaPy)
[![CodeFactor](https://www.codefactor.io/repository/github/yaoyinying/rosettapy/badge)](https://www.codefactor.io/repository/github/yaoyinying/rosettapy)
[![Maintainability](https://api.codeclimate.com/v1/badges/56830e8844e9ef6075c2/maintainability)](https://codeclimate.com/github/YaoYinYing/RosettaPy/maintainability)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/4d6b6f78e59b4c38a0362d2d83fc9815)](https://app.codacy.com/gh/YaoYinYing/RosettaPy/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Pylint](https://github-image-cache.yaoyy.moe/badge_dir_with_uniq_name/RosettaPy/pylint/pylint_scan.svg)](https://github.com/YaoYinYing/pylint-github-action)
[![GitHub repo size](https://img.shields.io/github/repo-size/YaoYinYing/RosettaPy)](https://github.com/YaoYinYing/RosettaPy)

[![DeepSource](https://app.deepsource.com/gh/YaoYinYing/RosettaPy.svg/?label=active+issues&show_trend=true&token=1lA-hDEsz7RiQl-oBFsiLziT)](https://app.deepsource.com/gh/YaoYinYing/RosettaPy/)
[![DeepSource](https://app.deepsource.com/gh/YaoYinYing/RosettaPy.svg/?label=resolved+issues&show_trend=true&token=1lA-hDEsz7RiQl-oBFsiLziT)](https://app.deepsource.com/gh/YaoYinYing/RosettaPy/)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Syntax Upgrade: pyupgrade](https://img.shields.io/badge/pyupgrade-white?style=plastic&logo=python&logoColor=ebedf0&label=Syntax&labelColor=da394b&color=white&link=https%3A%2F%2Fgithub.com%2Fasottile%2Fpyupgrade)](https://github.com/asottile/pyupgrade)
[![Pycln](https://img.shields.io/badge/pycln-white?style=plastic&logo=python&logoColor=35475c&label=Imports%20Clean&labelColor=c4fcfd&color=c6fdbc&link=https%3A%2F%2Fgithub.com%2Fhadialqattan%2Fpycln)](https://github.com/hadialqattan/pycln)
[![Flake8](https://img.shields.io/badge/Flake8-white?style=plastic&logo=python&logoColor=silver&label=Style&link=https%3A%2F%2Fgithub.com%2FPyCQA%2Fflake8)](https://github.com/PyCQA/flake8)

## Release

[![GitHub Release](https://img.shields.io/github/v/release/YaoYinYing/RosettaPy)](https://github.com/YaoYinYing/RosettaPy/releases)
[![GitHub Release Date](https://img.shields.io/github/release-date/YaoYinYing/RosettaPy)](https://github.com/YaoYinYing/RosettaPy/releases)

[![PyPI - Format](https://img.shields.io/pypi/format/RosettaPy)](https://pypi.org/project/RosettaPy/)
[![PyPI - Version](https://img.shields.io/pypi/v/RosettaPy)](https://pypi.org/project/RosettaPy/#history)
[![PyPI - Status](https://img.shields.io/pypi/status/RosettaPy)](https://pypi.org/project/RosettaPy/)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/RosettaPy)](https://pypi.org/project/RosettaPy/)

## Python version supported

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/RosettaPy)](https://pypi.org/project/RosettaPy/)
[![PyPI - Implementation](https://img.shields.io/pypi/implementation/RosettaPy)](https://pypi.org/project/RosettaPy/)

## Overview

`RosettaPy` is a Python module designed to locate Rosetta biomolecular modeling suite binaries that follow a specific naming pattern and execute Rosetta in command line. The module includes:

### Building Blocks provided by `RosettaPy`

- An object-oriented `RosettaFinder` class to search for binaries.
- A `RosettaBinary` dataclass to represent the binary and its attributes.
- A `RosettaCmdTask` dataclass to represent a single Rosetta run task.
- A `RosettaContainer` dataclass to wrap runs into Rosetta Containers.
- A `MPI_node` dataclass to manage MPI resourses. _Not Seriously Tested_
- A `RosettaRepoManager` dataclass to fetch necessary directories and files, and setup as an environment variable.
- A shortcut method `partial_clone` to handle repository clonings and setups.
  > [!NOTE]
  > _Before run this tool, please **DO** make sure that you have abtained the correct license from Rosetta Commons._
  > _For more details, please see this [page](https://rosettacommons.org/software/download/)._
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
```

### Fetching additional scripts/database files from the Rosetta GitHub repository.

> [!WARNING]
> _AGAIN, before run this method, please **DO** make sure that you have licensed by Rosetta Commons._
> _For more details of licensing, please see this [page](https://rosettacommons.org/software/download/)._

This tool is helpful for fetching additional scripts/database files from the Rosetta GitHub repository.

For example, if your local machine does not have Rosetta built and installed, and you wich check some files from `$ROSETTA3_DB` or `$ROSETTA_PYTHON_SCRIPTS` before run Rosetta tasks within Rosetta Container, you may quickly use this tool to fetch them into your local machine.

The `partial_clone` function do will do the following steps:

1. Check if the Git binary is feasible and the git version `>=2.34.1`. If not, then raise an error to notify the user to upgrade git.
2. Check if the target directory is empty or not and the repository is not cloned yet.
3. Setup partial clone and sparse checkout stuffs.
4. Clone the repository and subdirectory to the target directory.
5. Setup the environment variable with the target directory.

```python

import os
from RosettaPy.utils import partial_clone

def clone_db_relax_script():
    """
    A example for cloning the relax scripts from the Rosetta database.

    This function uses the `partial_clone` function to clone specific relax scripts from the RosettaCommons GitHub repository.
    It sets an environment variable to specify the location of the cloned subdirectory and prints the value of the environment variable after cloning.
    """
    # Clone the relax scripts from the Rosetta repository to a specified directory
    partial_clone(
        repo_url="https://github.com/RosettaCommons/rosetta",
        target_dir="rosetta_db_clone_relax_script",
        subdirectory_as_env="database",
        subdirectory_to_clone="database/sampling/relax_scripts",
        env_variable="ROSETTA3_DB",
    )

    # Print the value of the environment variable after cloning
    print(f'ROSETTA3_DB={os.environ.get("ROSETTA3_DB")}')

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
   ```

2. Navigate to the project directory and install the required dependencies:

   ```bash
   cd RosettaPy
   pip install '.[test]'
   ```

3. Run the tests:

   ```bash
   # quick test cases
   python -m pytest ./tests -m 'not integration'

   # test integration cases
   python -m pytest ./tests -m 'integration'
   ```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for bug reports and feature requests.

## Acknowledgements

- **Rosetta Commons**: The Rosetta software suite for the computational modeling and analysis of protein structures.

## Contact

For questions or support, please contact:

- **Name**: Yinying Yao
- **Email**:yaoyy.hi(a)gmail.com
