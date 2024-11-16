# RosettaPy

A Python Utility for Wrapping Rosetta Macromolecural Modeling Suite.

> [!CAUTION]
> _Before running `RosettaPy`, please **DO** make sure that you have abtained the correct license from Rosetta Commons._
> _For more details, please see this [page](https://rosettacommons.org/software/download/)._

> [!IMPORTANT]
> **`RosettaPy`** is NOT [`PyRosetta`](http://www.pyrosetta.org/).
> You probably don't need to install this package if you are looking for `PyRosetta`.
> Please see this [page](http://www.pyrosetta.org/).

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
[![imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![syntax upgrade: pyupgrade](https://img.shields.io/badge/pyupgrade-white?style=plastic&logo=python&logoColor=ebedf0&label=syntax&labelColor=da394b&color=white&link=https%3A%2F%2Fgithub.com%2Fasottile%2Fpyupgrade)](https://github.com/asottile/pyupgrade)
[![pycln](https://img.shields.io/badge/pycln-white?style=plastic&logo=python&logoColor=35475c&label=imports&labelColor=c4fcfd&color=c6fdbc&link=https%3A%2F%2Fgithub.com%2Fhadialqattan%2Fpycln)](https://github.com/hadialqattan/pycln)
[![Flake8](https://img.shields.io/badge/flake8-white?style=plastic&logo=python&logoColor=silver&label=style&link=https%3A%2F%2Fgithub.com%2FPyCQA%2Fflake8)](https://github.com/PyCQA/flake8)
[![autoflake](https://img.shields.io/badge/autoflake-yellow?style=plastic&logo=python&logoColor=cyan&label=style&link=https%3A%2F%2Fgithub.com%2FPyCQA%2Fautoflake)](https://github.com/PyCQA/autoflake)

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

| Class/Component                 | Description                                                                                                                                                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **RosettaFinder**               | A class designed to search for binary files within specified directories.                                                                                                                                                     |
| **RosettaBinary**               | Represents a binary file and its associated attributes, such as path and version.                                                                                                                                             |
| **RosettaCmdTask**              | Encapsulates a single task for running Rosetta, including command-line arguments and input files.                                                                                                                             |
| **RosettaContainer**            | Wraps multiple Rosetta tasks into a container, managing file system mounts and resource allocation.                                                                                                                           |
| **MpiNode**                     | Manages MPI resources for parallel computing tasks; note that it is not thoroughly tested.                                                                                                                                    |
| **RosettaRepoManager**          | Fetches necessary directories and files, sets up environment variables, and provides a `partial_clone` method for cloning and setting up repositories.                                                                        |
| **WslWrapper**                  | Wrapper for running Rosetta on Windows Subsystem for Linux (WSL). Requires Rosetta installed in WSL.                                                                                                                          |
| **Rosetta**                     | A command-line wrapper for executing Rosetta runs, simplifying the process of setting up and running commands.                                                                                                                |
| **RosettaScriptsVariableGroup** | Represents variables used in Rosetta scripts, facilitating their management and use.                                                                                                                                          |
| **RosettaEnergyUnitAnalyser**   | Analyzes and interprets Rosetta output score files, providing a simplified interface for result analysis.                                                                                                                     |
| **Example Applications**        | Demonstrates the use of the above components through specific Rosetta applications like PROSS, FastRelax, RosettaLigand, Supercharge, MutateRelax, and Cartesian ddG, each tailored to different computational biology tasks. |

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

Ensure Python 3.8 or higher installed.

### Install via PyPI

You can install `RosettaPy` directly from PyPI:

```bash
pip install RosettaPy -U
```

## Usage

### Build Your Own Rosetta Workflow

**Import necessary modules**

```python
from RosettaPy import Rosetta, RosettaScriptsVariableGroup, RosettaEnergyUnitAnalyser
from RosettaPy.node import RosettaContainer, MpiNode, Native
```

**Create a Rosetta proxy with parameters**

```python
rosetta = Rosetta(
    # a binary name for locating the real binary path
    bin="rosetta_scripts",

    # flag file paths (please do not use `@` prefix here)
    flags=[...],

    # command-line options
    opts=[
        "-in:file:s", os.path.abspath(pdb),
        "-parser:protocol", "/path/to/my_rosetta_scripts.xml",
    ],

    # output directory
    output_dir=...,

    # save pdb and scorefile together
    save_all_together=True,

    # a job identifier
    job_id=...,

    # silent the rosetta logs from stdout
    verbose = False,
)
```

**Isolation Mode**

Some Rosetta Apps (Superchange, Cartesian ddG, etc.) may produce files at their working directory, and this may not threadsafe if one runs multiple jobs in parallel in the same directory. In this case, the `isolation` flag can be used to create a temporary directory for each run.

```diff
Rosetta(
    ...
+   isolation=True,
)
```

**Native as Run Node**

By default, `RosettaPy` uses `Native` node, representing the local machine with Rosetta installed.
To specify the number of cores, use the `nproc` parameter.

```diff
Rosetta(
    ...
+   run_node=Native(nproc=8)
)
```

**Run rosetta tasks with Rosetta Container**

If one wishes to use the Rosetta container as the task worker, (WSL + Docker Desktop, for example)
setting a `run_node` option as `RosettaContainer` class would tell the proxy to use it.
This image names can be found at <https://hub.docker.com/r/rosettacommons/rosetta>
Note that the paths of each task will be mounted into the container and rewritten to the container's path.
This rewriting feature may fail if the path is mixed with complicated expressions as options.

```diff
Rosetta(
    ...
+   run_node=RosettaContainer(image="rosettacommons/rosetta:latest"),
)
```

**Run rosetta tasks with MPI**

If one wish to run with Rosetta that was installed on local and built with `extra=mpi` flag via MPI,
consider using `MpiNode` instance as `run_node` instead. This enables native parallelism feature with MPI.

```diff
Rosetta(
    ...
+   run_node=MpiNode(nproc=10),
)
```

Also, if one wishes to use MpiNode with Slurm task manager, specifying `run_node` to `MpiNode.from_slurm()` may help
with fetching the node info from the environment.

_This is an experimental feature that has not been seriously tested in production._

```diff
Rosetta(
    ...
+   run_node=MpiNode.from_slurm(),
)
```

**Pick Your Node**

One can still pick the desire node quickly by calling `node_picker` method.

```diff
from RosettaPy.node import node_picker, NodeHintT

node_hint: NodeHintT = 'docker_mpi'

Rosetta(
    ...
+   run_node=node_picker(node_type=node_hint)
)
```

Where `node_hint` is one of `["docker", "docker_mpi", "mpi", "wsl", "wsl_mpi", "native"]`

**Compose rosetta tasks matrix as inputs**

```python
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

# pass task matrix to rosetta.run as `inputs`
rosetta.run(inputs=tasks)
```

**Using structure labels (-nstruct)**

Create distributed runs with structure labels (-nstruct) is feasible. For local runs without MPI or container, `RosettaPy` implemented this feature by ignoring the build-in job distributer of Rosetta, canceling the default output structure label, attaching external structural label as unique job identifier to each other, then run these tasks only once for each. This enables massive parallalism.

```python
options=[...] # Passing an optional list of options that will be used to all structure models
rosetta.run(nstruct=nstruct, inputs=options) # input options will be passed to all runs equally
```

**Call Analyzer to check the results**

```python
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

### Fetching additional scripts/database files from the Rosetta GitHub repository

> [!CAUTION]
> _AGAIN, before using this tool, please **DO** make sure that you have licensed by Rosetta Commons._
> _For more details of licensing, please check this [page](https://rosettacommons.org/software/download/)._

This tool is helpful for fetching additional scripts/database files/directories from the Rosetta GitHub repository.

For example, if one's local machine does not have Rosetta built and installed, and wishes to check some files from `$ROSETTA3_DB` or use some helper scripts at `$ROSETTA_PYTHON_SCRIPTS` before run Rosetta tasks within Rosetta Container, one can use this tool to fetch them into the local harddrive by doing a minimum cloning.

The `partial_clone` function do will do the following steps:

1. Check if Git is installed and versioned with `>=2.34.1`. If not satisfied, raise an error to notify the user to upgrade git.
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

## Windows? Yes

Thanks to the official container image, it is possible to run RosettaPy on Windows.
Here are the steps one should follow:

1. Enable `Windows Subsystem for Linux`, and switch to `WSL2`(<https://aka.ms/wsl2kernel>)
2. Install `Docker Desktop` and enable `WSL2 docker engine`.
3. Search for the Image `rosettacommons/rosetta:<label>` where `<label>` is the version of Rosetta build you want to use.
4. Use `RosettaContainer` class as the run node, with the image name you just pulled.
5. Make sure all your input files are using `LF` ending instead of `CRLF`. This is fatal for Rosetta to parse input files. For details on CRLF vs LF on git clone, please refer to this [page](https://stackoverflow.com/questions/2517190/how-do-i-force-git-to-use-lf-instead-of-crlf-under-windows)
6. Build you Rosetta workflow with `RosettaPy` and run it.

During the workflow processing, you will see some active containers at `Containers` tab of `Docker Desktop`.

## Full Operating System Compatibility Table

| Node                 | Linux[x86_64, aarch64] | macOS | Windows |
| -------------------- | ---------------------- | ----- | ------- |
| Native[^1]           | ✅                      | ✅     | ❌       |
| MpiNode[^2]          | ✅                      | ✅     | ❌       |
| RosettaContainer[^3] | ✅[^6]                  | ✅[^5] | ✅[^6]   |
| WslWrapper[^4]       | ❌                      | ❌     | ✅       |

[^1]: Rosetta built, installed on local machine.
[^2]: Rosetta built with `extras=mpi` flag and installed on local machine.
[^3]: Docker or Docker Desktop(Windows/macOS) installed and launched.
[^4]: Windows Subsystem for Linux(WSL) installed and switched to WSL2, with Rosetta built and installed on.
[^5]: Translated with Rosetta2 framework if runs on Apple Silicon Mac, which may cause worthy slow performance.
[^6]: The official Docker image provided by RosettaCommons exclusively supports machines with x86_64 architecture.

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
   pytest ./tests -m 'not integration'

   # test integration cases
   pytest ./tests -m 'integration'

   # run integration tests with both docker and local
   export GITHUB_CONTAINER_ROSETTA_TEST=YES
   pytest ./tests -m 'integration'

   ```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for bug reports and feature requests.

## Acknowledgements

- **Rosetta Commons**: The Rosetta software suite for the computational modeling and analysis of protein structures.
- **CIs, formatters, checkers and hooks** that save my life and make this tool improved.
- **ChatGPT, Tongyi Lingma, DeepSource Autofix™ AI and CodeRabbit** for the documentation, code improvements, test cases generations and code revisions.

## Contact

For questions or support, please contact:

- **Name**: Yinying Yao
- **Email**:yaoyy.hi(a)gmail.com

---
