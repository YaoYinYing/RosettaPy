"""Unit tests for the v2 Rosetta compiler (PR 2 milestone).

These tests are deliberately pure: they never require Rosetta to be installed,
they never launch a process, and they never touch the filesystem. They cover the
canonical cases named by the migration plan that belong to compilation:

- plain Rosetta binary invocation;
- ``rosetta_scripts`` with script variables;
- FastRelax-style execution;
- ``nstruct > 1`` in native mode;
- ``nstruct > 1`` in external mode;
- paths containing spaces.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from RosettaPy.core import ArtifactRole, ExecutionResult, Executor, TaskSpec
from RosettaPy.core.errors import CompilationError
from RosettaPy.rosetta import (
    CompileContext,
    NStructMode,
    RosettaBinaryRequest,
    RosettaCompiler,
    RosettaInvocation,
)


@pytest.fixture
def compiler() -> RosettaCompiler:
    return RosettaCompiler()


@pytest.fixture
def context() -> CompileContext:
    return CompileContext(
        run_id="relax-run",
        work_dir=Path("/work"),
        output_dir=Path("/work/output"),
        env={"OMP_NUM_THREADS": "1"},
        inputs=(Path("/work/input.pdb"),),
    )


def compile_one(compiler: RosettaCompiler, invocation: RosettaInvocation, context: CompileContext) -> TaskSpec:
    tasks = compiler.compile(invocation, context)
    assert isinstance(tasks, tuple)
    assert len(tasks) == 1
    return tasks[0]


def option_value(argv: tuple[str, ...], option: str) -> str:
    """Return the value that follows ``option`` in ``argv``."""
    return argv[argv.index(option) + 1]


def option_values(argv: tuple[str, ...], option: str) -> list[str]:
    """Return every value that follows an occurrence of ``option`` in ``argv``."""
    return [argv[index + 1] for index, token in enumerate(argv) if token == option]


class TestCompilerContract:
    def test_returns_a_tuple(self, compiler, context):
        tasks = compiler.compile(RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts")), context)
        assert isinstance(tasks, tuple)
        assert len(tasks) == 1

    def test_rejects_wrong_invocation_type(self, compiler, context):
        with pytest.raises(TypeError, match="RosettaInvocation"):
            compiler.compile({"binary": "rosetta_scripts"}, context)  # type: ignore[arg-type]

    def test_rejects_wrong_context_type(self, compiler):
        with pytest.raises(TypeError, match="CompileContext"):
            compiler.compile(
                RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts")), None
            )  # type: ignore[arg-type]

    def test_declares_its_identity(self, compiler):
        assert compiler.identity == "rosetta_compiler"

    def test_holds_no_executor_reference(self, compiler):
        assert isinstance(compiler, RosettaCompiler)
        assert not isinstance(compiler, Executor)

    def test_has_no_result_type_dependency_at_runtime(self, compiler, context):
        """Compilation produces tasks, never execution results."""
        tasks = compiler.compile(RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts")), context)
        assert all(isinstance(task, TaskSpec) for task in tasks)
        assert not any(isinstance(task, ExecutionResult) for task in tasks)


class TestCompilerIsPure:
    def test_does_not_require_the_binary_to_exist(self, compiler, context):
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts_not_installed_anywhere"))
        task = compile_one(compiler, invocation, context)
        assert task.argv[0] == "rosetta_scripts_not_installed_anywhere"

    def test_does_not_require_flag_files_to_exist(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            flags=("does-not-exist.flags",),
        )
        assert "@does-not-exist.flags" in compile_one(compiler, invocation, context).argv

    def test_does_not_mutate_the_invocation(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            flags=("flags.txt",),
            options=("-suffix", "user"),
            script_vars={"n": "3"},
        )
        before = invocation.as_dict()
        compiler.compile(invocation, context)
        assert invocation.as_dict() == before

    def test_compilation_is_deterministic(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            options=("-relax", "relax.xml"),
            script_vars={"a": "1", "b": "2"},
            nstruct=3,
            nstruct_mode=NStructMode.EXTERNAL,
        )
        first = compiler.compile(invocation, context)
        second = compiler.compile(invocation, context)
        assert first == second

    def test_script_var_order_follows_the_supplied_mapping(self, compiler, context):
        ordered = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            script_vars={"b": "2", "a": "1"},
        )
        assert option_values(compile_one(compiler, ordered, context).argv, "-parser:script_vars") == [
            "b=2",
            "a=1",
        ]


class TestBinaryRendering:
    def test_preserves_logical_binary_name(self, compiler, context):
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts"))
        assert compile_one(compiler, invocation, context).argv[0] == "rosetta_scripts"

    def test_preserves_explicit_binary_path(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(path="/opt/rosetta/bin/rosetta_scripts.static.linuxgccrelease")
        )
        assert (
            compile_one(compiler, invocation, context).argv[0]
            == "/opt/rosetta/bin/rosetta_scripts.static.linuxgccrelease"
        )

    def test_rendering_is_backend_independent(self, compiler, context):
        """The same invocation renders identically regardless of the output root."""
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts"))
        other_context = CompileContext(run_id="relax-run", work_dir=Path("/mnt/elsewhere"), output_dir=Path("/mnt/out"))
        native_argv = compile_one(compiler, invocation, context).argv
        other_argv = compile_one(compiler, invocation, other_context).argv
        assert native_argv[0] == other_argv[0] == "rosetta_scripts"


class TestArgumentRendering:
    def test_canonical_plain_invocation(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            flags=("flags.txt",),
            options=("-s", "input.pdb"),
        )
        assert compile_one(compiler, invocation, context).argv == (
            "rosetta_scripts",
            "@flags.txt",
            "-s",
            "input.pdb",
            "-mute",
            "all",
            "-out:path:pdb",
            "/work/output/relax-run",
            "-out:path:score",
            "/work/output/relax-run",
            "-out:file:scorefile",
            "relax-run.scorefile.sc",
        )

    def test_flag_references_do_not_modify_the_file(self, compiler, context, tmp_path):
        flag_file = tmp_path / "flags.txt"
        original = "-s input.pdb\r\n-ex1\r\n"
        flag_file.write_text(original)
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            flags=(flag_file,),
        )
        argv = compile_one(compiler, invocation, context).argv
        assert f"@{flag_file}" in argv
        assert argv.index(f"@{flag_file}") == 1
        assert flag_file.read_bytes() == original.encode()

    def test_crlf_flag_files_are_not_rewritten(self, compiler, context, tmp_path):
        flag_file = tmp_path / "flags.txt"
        original = "-s input.pdb\r\n"
        flag_file.write_text(original)
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            flags=(flag_file,),
        )
        compile_one(compiler, invocation, context)
        assert flag_file.read_bytes() == original.encode()

    def test_rosetta_scripts_variables_are_rendered_as_options(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            script_vars={"input": "protein.pdb", "n": "3"},
        )
        argv = compile_one(compiler, invocation, context).argv
        assert option_values(argv, "-parser:script_vars") == ["input=protein.pdb", "n=3"]

    def test_mute_is_emitted_by_default(self, compiler, context):
        argv = compile_one(
            compiler, RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts")), context
        ).argv
        assert argv[argv.index("-mute") + 1] == "all"

    def test_mute_can_be_disabled(self, compiler, context):
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts"), mute=False)
        assert "-mute" not in compile_one(compiler, invocation, context).argv

    def test_output_paths_use_host_canonical_namespace(self, compiler, context):
        task = compile_one(compiler, RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts")), context)
        assert option_value(task.argv, "-out:path:pdb") == str(context.output_dir / context.run_id)
        assert option_value(task.argv, "-out:path:score") == str(context.output_dir / context.run_id)
        assert task.output_root == context.output_dir / context.run_id

    def test_paths_containing_spaces_stay_tokenized(self, compiler, tmp_path):
        spaced_context = CompileContext(
            run_id="spaced-run",
            work_dir=tmp_path / "my work dir",
            output_dir=tmp_path / "my output dir",
            inputs=(tmp_path / "my input dir" / "in.pdb",),
        )
        input_path = str(tmp_path / "my input dir" / "in.pdb")
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            options=("-s", input_path),
        )
        task = compile_one(compiler, invocation, spaced_context)
        assert task.cwd == tmp_path / "my work dir"
        assert option_value(task.argv, "-s") == input_path
        assert option_value(task.argv, "-out:path:pdb") == str(tmp_path / "my output dir" / "spaced-run")
        assert input_path in task.argv


class TestNativeNStruct:
    def test_single_replica_omits_nstruct(self, compiler, context):
        argv = compile_one(
            compiler, RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts")), context
        ).argv
        assert "-nstruct" not in argv

    @pytest.mark.parametrize("nstruct", [2, 10])
    def test_native_replication_is_one_task_with_nstruct(self, compiler, context, nstruct):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            nstruct=nstruct,
            nstruct_mode=NStructMode.NATIVE,
        )
        tasks = compiler.compile(invocation, context)
        assert len(tasks) == 1
        assert option_value(tasks[0].argv, "-nstruct") == str(nstruct)

    def test_native_mode_is_the_default(self, compiler, context):
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts"), nstruct=4)
        assert invocation.nstruct_mode is NStructMode.NATIVE
        assert len(compiler.compile(invocation, context)) == 1

    def test_native_mode_task_uses_the_run_id(self, compiler, context):
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts"), nstruct=4)
        assert compile_one(compiler, invocation, context).task_id == "relax-run"

    def test_native_mode_does_not_add_output_collision_options(self, compiler, context):
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts"), nstruct=4)
        argv = compile_one(compiler, invocation, context).argv
        assert "-suffix" not in argv
        assert "-no_nstruct_label" not in argv


class TestExternalNStruct:
    def test_fans_out_one_task_per_replica(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            nstruct=3,
            nstruct_mode=NStructMode.EXTERNAL,
        )
        tasks = compiler.compile(invocation, context)
        assert len(tasks) == 3
        assert [task.task_id for task in tasks] == ["relax-run-00001", "relax-run-00002", "relax-run-00003"]

    def test_each_replica_has_its_own_output_namespace(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            nstruct=2,
            nstruct_mode=NStructMode.EXTERNAL,
        )
        roots = [task.output_root for task in compiler.compile(invocation, context)]
        assert roots == [context.output_dir / "relax-run-00001", context.output_dir / "relax-run-00002"]
        assert len(set(roots)) == 2

    def test_each_replica_has_collision_free_arguments(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            nstruct=2,
            nstruct_mode=NStructMode.EXTERNAL,
        )
        tasks = compiler.compile(invocation, context)
        suffixes = [option_value(task.argv, "-suffix") for task in tasks]
        scorefiles = [option_value(task.argv, "-out:file:scorefile") for task in tasks]
        assert suffixes == ["_00001", "_00002"]
        assert scorefiles == ["relax-run.scorefile.00001.sc", "relax-run.scorefile.00002.sc"]
        assert all("-no_nstruct_label" in task.argv for task in tasks)

    def test_external_mode_does_not_emit_nstruct(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            nstruct=3,
            nstruct_mode=NStructMode.EXTERNAL,
        )
        assert all("-nstruct" not in task.argv for task in compiler.compile(invocation, context))

    def test_merges_a_user_supplied_suffix(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            options=("-suffix", "user"),
            nstruct=2,
            nstruct_mode=NStructMode.EXTERNAL,
        )
        tasks = compiler.compile(invocation, context)
        assert [option_value(task.argv, "-suffix") for task in tasks] == ["user_00001", "user_00002"]
        assert tasks[0].metadata["user_suffix"] == "user"

    def test_nstruct_one_in_either_mode_produces_one_task(self, compiler, context):
        for mode in (NStructMode.NATIVE, NStructMode.EXTERNAL):
            invocation = RosettaInvocation(
                binary=RosettaBinaryRequest(name="rosetta_scripts"),
                nstruct=1,
                nstruct_mode=mode,
            )
            assert len(compiler.compile(invocation, context)) == 1


class TestCompiledTaskContent:
    def test_task_carries_context_paths_environment_and_inputs(self, compiler, context):
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts"))
        task = compile_one(compiler, invocation, context)
        assert task.cwd == context.work_dir
        assert task.env == {"OMP_NUM_THREADS": "1"}
        assert task.inputs == (Path("/work/input.pdb"),)

    def test_task_declares_expected_artifacts(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            options=("-out:file:silent", "run.silent"),
        )
        task = compile_one(compiler, invocation, context)
        roles = {expectation.role for expectation in task.expected_artifacts}
        assert roles == {ArtifactRole.STRUCTURE, ArtifactRole.SCOREFILE, ArtifactRole.SILENT_FILE}
        assert all(not expectation.required for expectation in task.expected_artifacts)

    def test_expected_scorefile_pattern_matches_the_rendered_name(self, compiler, context):
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts"))
        task = compile_one(compiler, invocation, context)
        scorefile = option_value(task.argv, "-out:file:scorefile")
        assert any(expectation.pattern == scorefile for expectation in task.expected_artifacts)

    def test_expected_artifact_patterns_are_relative(self, compiler, context):
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts"))
        task = compile_one(compiler, invocation, context)
        assert all(not Path(expectation.pattern).is_absolute() for expectation in task.expected_artifacts)

    def test_compiler_does_not_request_cores_for_native_replication(self, compiler, context):
        invocation = RosettaInvocation(binary=RosettaBinaryRequest(name="rosetta_scripts"), nstruct=8)
        assert compile_one(compiler, invocation, context).resources.cpu_cores is None

    def test_metadata_records_compilation_provenance(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            options=("-relax", "relax.xml"),
            script_vars={"n": "3"},
        )
        metadata = compile_one(compiler, invocation, context).metadata
        assert metadata["compiler"] == "rosetta_compiler"
        assert metadata["run_id"] == "relax-run"
        assert metadata["binary_request"] == {"name": "rosetta_scripts", "path": None}
        assert metadata["script_vars"] == {"n": "3"}
        assert metadata["nstruct"] == 1
        assert metadata["nstruct_mode"] == "native"
        assert metadata["replica_index"] == 1

    def test_external_metadata_records_the_replica_index(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            nstruct=2,
            nstruct_mode=NStructMode.EXTERNAL,
        )
        tasks = compiler.compile(invocation, context)
        assert [task.metadata["replica_index"] for task in tasks] == [1, 2]
        assert [task.metadata["replica_suffix"] for task in tasks] == ["_00001", "_00002"]

    def test_task_is_json_serializable(self, compiler, context):
        import json

        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            options=("-relax", "relax.xml"),
        )
        json.loads(json.dumps(compile_one(compiler, invocation, context).as_dict()))


class TestCanonicalFastRelaxInvocation:
    """The canonical FastRelax-style invocation named by the migration plan."""

    @pytest.fixture
    def fastrelax(self) -> RosettaInvocation:
        return RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            options=("-s", "input.pdb", "-parser:protocol", "relax.xml"),
            script_vars={"input": "input.pdb", "nstruct": "1"},
            nstruct=1,
        )

    def test_compiles_deterministically(self, compiler, context, fastrelax):
        first = compiler.compile(fastrelax, context)
        second = compiler.compile(fastrelax, context)
        assert first == second
        assert len(first) == 1

    def test_renders_the_canonical_argument_vector(self, compiler, context, fastrelax):
        assert compile_one(compiler, fastrelax, context).argv == (
            "rosetta_scripts",
            "-s",
            "input.pdb",
            "-parser:protocol",
            "relax.xml",
            "-parser:script_vars",
            "input=input.pdb",
            "-parser:script_vars",
            "nstruct=1",
            "-mute",
            "all",
            "-out:path:pdb",
            "/work/output/relax-run",
            "-out:path:score",
            "/work/output/relax-run",
            "-out:file:scorefile",
            "relax-run.scorefile.sc",
        )

    def test_replicates_natively_by_default(self, compiler, context, fastrelax):
        from dataclasses import replace

        invocation = replace(fastrelax, nstruct=5)
        tasks = compiler.compile(invocation, context)
        assert len(tasks) == 1
        assert option_value(tasks[0].argv, "-nstruct") == "5"

    def test_needs_no_rosetta_installation(self, compiler, context, fastrelax, monkeypatch):
        import subprocess

        def fail(*args, **kwargs):  # pragma: no cover - only runs on regression
            raise AssertionError("compilation must not launch a process")

        monkeypatch.setattr(subprocess, "run", fail)
        monkeypatch.setattr(subprocess, "Popen", fail)
        assert len(compiler.compile(fastrelax, context)) == 1


class TestCompileContextValidation:
    def test_requires_a_safe_run_id(self):
        for bad_id in ["", "a/b", "../escape", "a b", "x" * 129]:
            with pytest.raises((TypeError, ValueError)):
                CompileContext(run_id=bad_id, work_dir=Path("/w"), output_dir=Path("/o"))

    def test_rejects_string_inputs(self):
        with pytest.raises(TypeError, match="not a string"):
            CompileContext(run_id="run", work_dir=Path("/w"), output_dir=Path("/o"), inputs="/data/in.pdb")

    def test_rejects_non_string_env_value(self):
        with pytest.raises(TypeError, match="must be a string"):
            CompileContext(run_id="run", work_dir=Path("/w"), output_dir=Path("/o"), env={"N": 1})

    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            CompileContext(
                run_id="run", work_dir=Path("/w"), output_dir=Path("/o")
            ).run_id = "other"  # type: ignore[misc]

    def test_requires_no_execution_environment_information(self):
        fields = set(CompileContext.__dataclass_fields__)
        assert fields == {"run_id", "work_dir", "output_dir", "env", "inputs"}

    def test_as_dict(self):
        context = CompileContext(
            run_id="run",
            work_dir=Path("/w"),
            output_dir=Path("/o"),
            env={"N": "1"},
            inputs=(Path("/data/in.pdb"),),
        )
        assert context.as_dict() == {
            "run_id": "run",
            "work_dir": "/w",
            "output_dir": "/o",
            "env": {"N": "1"},
            "inputs": ["/data/in.pdb"],
        }


class TestInvocationValidation:
    def test_surfaces_compilation_errors(self, compiler, context):
        invocation = RosettaInvocation(
            binary=RosettaBinaryRequest(name="rosetta_scripts"),
            options=("-nstruct", "3"),
            nstruct_mode=NStructMode.EXTERNAL,
        )
        with pytest.raises(CompilationError, match="must not contain '-nstruct'"):
            compiler.compile(invocation, context)
