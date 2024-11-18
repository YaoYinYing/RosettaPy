# RosettaPy

A Python Utility for Wrapping Rosetta Macromolecural Modeling Suite.

> [!CAUTION]
> `RosettaPy` requires `Rosetta` [compiled and installed](https://docs.rosettacommons.org/docs/latest/build_documentation/Build-Documentation).
> _Before running `RosettaPy`, please **DO** make sure that you have obtained the correct license from Rosetta Commons._
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
| **RosettaRepoManager**          | Fetches necessary directories and files, sets up environment variables, and provides a `partial_clone` method for cloning and setting up repositories.                                                                        |
| **Rosetta**                     | A command-line wrapper for executing Rosetta runs, simplifying the process of setting up and running commands.                                                                                                                |
| **RosettaScriptsVariableGroup** | Represents variables used in Rosetta scripts, facilitating their management and use.                                                                                                                                          |
| **RosettaEnergyUnitAnalyser**   | Analyzes and interprets Rosetta output score files, providing a simplified interface for result analysis.                                                                                                                     |
| **Example Applications**        | Demonstrates the use of the above components through specific Rosetta applications like PROSS, FastRelax, RosettaLigand, Supercharge, MutateRelax, and Cartesian ddG, each tailored to different computational biology tasks. |

## Features

- **Flexible Binary Search**: Finds Rosetta binaries based on their naming convention.
- **Platform Support**: Supports Windows, Linux and macOS operating systems.
- **Container Support**: Works with Docker containers running upon the official Rosetta Docker image.
- **Customizable Search Paths**: Allows specification of custom directories to search.
- **Structured Binary Representation**: Uses a dataclass to encapsulate binary attributes.
- **Command-Line Shortcut**: Provides a quick way to find binaries via the command line.
- **Available on PyPI**: Installable via `pip` without the need to clone the repository.
- **Unit Tested**: Includes tests for both classes to ensure functionality.

## Naming Convention

The Rosetta binaries are expected to follow this naming pattern:

```text
rosetta_scripts[[.mode].oscompilerrelease]
```

- **Binary Name**: `rosetta_scripts` (default) or specified.
- **Mode** (optional): `default`, `mpi`, or `static`.
- **OS** (optional): `linux` or `macos`.
- **Compiler** (optional): `gcc` or `clang`.
- **Release** (optional): `release` or `debug`.

For reg expression to match the basenames:

```regex
^(?P<binary_name>[\w]+)((\.(?P<mode>static|mpi|default|cxx11threadserialization|cxx11threadmpiserialization))?(\.(?P<os>linux|macos)(?P<compiler>gcc|clang)(?P<release>release|debug)))?$
```

See this [regex101](https://regex101.com/r/Z1XM9b/1) page for more details.

Examples of valid binary filenames:

- `rosetta_scripts` (dockerized Rosetta)
- `rosetta_scripts.linuxgccrelease`
- `rosetta_scripts.mpi.macosclangdebug`
- `rosetta_scripts.static.linuxgccrelease`

## Installation

One can install `RosettaPy` directly from PyPI:

```bash
pip install RosettaPy -U
```

## Basic Usages

`RosettaPy` is designed to handle the complexities of locating and running Rosetta binaries within Python.

### Build Rosetta Workflow from scratch

1. Import necessary modules

    ```python
    from RosettaPy import Rosetta, RosettaScriptsVariableGroup, RosettaEnergyUnitAnalyser
    from RosettaPy.node import RosettaContainer, MpiNode, Native
    ```

2. Create a `Rosetta` proxy with parameters

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

    RosettaPy uses `Native` node by default.

    It has to be noted that `Native` and `MpiNode` are only available on Linux and macOS.
    For Windows users, please refer to the `Full Operating System Compatibility Table` and `Get Windows Ready for Rosetta Runs` sections below.

3. Compose rosetta tasks matrix as inputs

    ```python
    tasks: list[Dict[str, Any]] = [ # Create tasks for each variant
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

4. Using structure labels (`-nstruct`)

    Create distributed runs with structure labels (`-nstruct <int>`) is feasible. For local runs without MPI or container, `RosettaPy` implemented this feature by ignoring the build-in job distributer of Rosetta, canceling the default output structure label, attaching external structural label as unique job identifier to each other, then run these tasks only once for each. This enables massive parallalism.

    ```python
    options=[...] # Passing an optional list of options that will be used to all structure models
    rosetta.run(nstruct=nstruct, inputs=options) # input options will be passed to all runs equally
    ```

5. Call Analyzer to check the results

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

    One can also build a customized analyser by re-using the `analyser.df` Dataframe.

## Advanced Usages

Here are some tips for advanced usages to adjust the workflow in respect to behaviors of some Rosetta workflows and applications.

### Isolation Mode

Some Rosetta Apps (Superchange, Cartesian ddG, etc.) may produce files at their working directory, and this may not threadsafe if one runs multiple jobs in parallel in the same directory. In this case, the `isolation` flag can be used to create a temporary directory for each run.

```diff
Rosetta(
    ...
+   isolation=True,
)
```

### Run Node Configurations

There are various node configurations that can be used to run Rosetta jobs.

#### Full Operating System Compatibility Table

|             Node | Linux | macOS | Windows | Architectures       | Prerequisite                                           |
| ---------------: | :---: | :---: | :-----: | ------------------- | ------------------------------------------------------ |
|           Native | ✅[^1] |   ✅   |    ❌    | x86_64, aarch64     | Rosetta compiled.                                      |
|          MpiNode | ✅[^1] |   ✅   |    ❌    | x86_64, aarch64     | Rosetta compiled with `extras=mpi` flag; MPI installed |
| RosettaContainer |   ✅   | ✅[^3] |    ✅    | x86_64              | Docker or Docker Desktop installed and launched.       |
|   WslWrapper[^2] |   ❌   |   ❌   |  ✅[^1]  | x86_64, aarch64[^4] | WSL2, with Rosetta built and installed on.             |

[^1]: For building Rosetta upon aarch64, please refer to this [example](https://github.com/YaoYinYing/BuildRosetta_aarch64/blob/main/README.md).
[^2]: Windows Subsystem for Linux(WSL) installed and switched to WSL2, with Rosetta built and installed on.
[^3]: Translated with Rosetta2 framework if runs on Apple Silicon Mac, which may cause worthy slow performance.
[^4]: It's theoretically possible yet no testing is done at all.

#### Reallocate CPU Cores

By default, `RosettaPy` uses `Native` node, representing the local machine with Rosetta installed.
To specify the number of cores, use the `nproc` parameter.

```diff
Rosetta(
    ...
+   run_node=Native(nproc=8)
)
```

#### Native MPI Support for local builds of Rosetta

**Requires MPI(mpich, openmpi, etc.) installed.**

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

#### Rosetta Container

If one wishes to use the Rosetta container as the task worker, (WSL + Docker Desktop, for example)
setting a `run_node` option as `RosettaContainer` class would tell the proxy to use it.
This image names can be found at <https://hub.docker.com/r/rosettacommons/rosetta>
Note that the paths of each task will be mounted into the container and rewritten to the container's path.
This rewriting feature may fail if the path is mixed with complicated expressions as options.

Non-mpi image:

```diff
Rosetta(
    ...
+   run_node=RosettaContainer(image="rosettacommons/rosetta:latest"),
)
```

or MPI image:

```diff
Rosetta(
    ...
+   run_node=RosettaContainer(image="rosettacommons/rosetta:mpi"),
+   use_mpi=True, # one still needs to enable MPI by this flag if MPI is required.
)
```

During the workflow processing, one will see some active containers at `Containers` tab of `Docker Desktop`, if `Docker Desktop` is installed. Also, typing `docker ps` in the terminal will show them too. Each of these containers will be destructed immediately after its task finished or stopped.

#### Pick Node Accordingly

One can still pick the desire node quickly by calling `node_picker` method.

```diff
from RosettaPy.node import node_picker, NodeHintT

node_hint: NodeHintT = 'docker_mpi'

Rosetta(
    ...
+   run_node=node_picker(node_type=node_hint),
+   use_mpi=...,
)
```

Where `node_hint` is one of `["docker", "docker_mpi", "mpi", "wsl", "wsl_mpi", "native"]`

#### Fetching additional scripts/database files from the Rosetta GitHub repository

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

#### Get Windows Ready for Rosetta Runs

Thanks for Windows Subsystem for Linux(WSL), we provide two simple ways to run Rosetta on Windows.

One must enable `Windows Subsystem for Linux`, then switch to `WSL2` following the instructions on this [page](https://aka.ms/wsl2kernel).

##### Docker Desktop

1. Install `Docker Desktop` and enable `WSL2 docker engine`.
2. Search for the Image `rosettacommons/rosetta:<label>` where `<label>` is the version of Rosetta build one want to use.
   - Note: network proxies or docker registry mirror setting may be required for users behind the GFW.
3. Use `RosettaContainer` class as the run node, with the image name one just pulled.
4. Make sure all the input files are using `LF` ending instead of `CRLF`. This is fatal for Rosetta to parse input files.
   - Note: this issue now can be done by using a context manager `convert_crlf_to_lf` from `RosettaPy.utils.tools`. Example:

    ```python
    from RosettaPy.utils.tools import convert_crlf_to_lf

    with convert_crlf_to_lf(input_file) as output_file:
        """Use `output_file` to replace `input_file`."""
    ```

5. Build Rosetta workflow with `RosettaPy` and run it.

##### WSL Wrapper

1. Install any recent release of Linux Distribution (e.g., `Ubuntu-22.04`) and setup for the account.
2. Install build essential tools: `apt-get update && apt-get install build-essential git -y`
   - Note: network proxies or apt repostory mirror setting may be required for users behind the GFW.
3. Install MPI: `apt-get install mpich -y`. MPICH is sufficient for Rosetta.
4. Install Python: `apt-get install python-is-python3 -y`
5. Fetch the source code of Rosetta and un-tar it to anywhere convenient. e.g. `/opt/rosetta`
6. Go to the source code directory and build it according to the Official Rosetta [Build Documentation](https://docs.rosettacommons.org/docs/latest/build_documentation/Build-Documentation).
7. Environment variables required by RosettaPy are:
   1. `ROSETTA_BIN`: path to the Rosetta executables
   2. `ROSETTA3_DB`: path to the Rosetta database
   3. `ROSETTA_PYTHON_SCRIPTS`: path to the Rosetta scripts
8. Use `WslWrapper` class as the run node. Parameters:
   1. `rosetta_bin`: `RosettaBinary` with in-wsl `dirname`(the absolute path of Rosetta binary directory in WSL distro).
   2. `distro`: the name of the Linux Distribution. for example, `'Ubuntu-22.04'`
   3. `user`: the name one just setup as the user in the Linux Distribution.
   4. `nproc`: number of CPU cores to be used.
   5. `prohibit_mpi`: whether to prohibit MPI.

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
