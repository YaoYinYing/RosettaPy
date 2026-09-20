"""Unit tests for the v2 ``core`` task contract."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from RosettaPy.core import ArtifactExpectation, ArtifactRole, ResourceRequest, TaskSpec


def make_task(**overrides) -> TaskSpec:
    kwargs = {
        "task_id": "run-a",
        "argv": ("rosetta_scripts", "-s", "input.pdb"),
        "cwd": Path("/work"),
    }
    kwargs.update(overrides)
    return TaskSpec(**kwargs)


class TestResourceRequest:
    def test_defaults_are_unset(self):
        request = ResourceRequest()
        assert request.cpu_cores is None
        assert request.memory_mb is None
        assert request.as_dict() == {"cpu_cores": None, "memory_mb": None}

    def test_accepts_positive_values(self):
        request = ResourceRequest(cpu_cores=8, memory_mb=4096)
        assert request.cpu_cores == 8
        assert request.memory_mb == 4096

    @pytest.mark.parametrize("field", ["cpu_cores", "memory_mb"])
    @pytest.mark.parametrize("value", [0, -1])
    def test_rejects_non_positive(self, field, value):
        with pytest.raises(ValueError, match="must be positive"):
            ResourceRequest(**{field: value})

    @pytest.mark.parametrize("field", ["cpu_cores", "memory_mb"])
    @pytest.mark.parametrize("value", ["4", 4.0, True])
    def test_rejects_non_int(self, field, value):
        with pytest.raises(TypeError, match="must be an int or None"):
            ResourceRequest(**{field: value})

    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            ResourceRequest().cpu_cores = 2  # type: ignore[misc]


class TestTaskSpecConstruction:
    def test_minimal_task_defaults(self):
        task = make_task()
        assert task.env == {}
        assert task.inputs == ()
        assert task.output_root == Path(".")
        assert task.expected_artifacts == ()
        assert task.resources == ResourceRequest()
        assert task.metadata == {}

    def test_argv_is_tokenized(self):
        task = make_task(argv=["rosetta_scripts", "-parser:script_vars", "a=1"])
        assert task.argv == ("rosetta_scripts", "-parser:script_vars", "a=1")

    def test_argv_names_the_executable_request(self):
        task = make_task(argv=("rosetta_scripts", "-s", "input.pdb"))
        assert task.executable_request == "rosetta_scripts"
        assert task.arguments == ("-s", "input.pdb")

    def test_paths_are_coerced(self):
        task = make_task(cwd="/work", output_root="/work/out", inputs=["/data/in.pdb"])
        assert task.cwd == Path("/work")
        assert task.output_root == Path("/work/out")
        assert task.inputs == (Path("/data/in.pdb"),)

    def test_tokens_may_contain_spaces(self):
        task = make_task(argv=("rosetta_scripts", "-s", "/data/my input.pdb"))
        assert task.argv[-1] == "/data/my input.pdb"

    def test_expected_artifacts_are_tupled(self):
        expectation = ArtifactExpectation(role=ArtifactRole.STRUCTURE, pattern="*.pdb")
        task = make_task(expected_artifacts=[expectation])
        assert task.expected_artifacts == (expectation,)


class TestTaskSpecValidation:
    @pytest.mark.parametrize("bad_id", ["", "a/b", "../escape", "a b", "a\\b", " lead", "x" * 129])
    def test_rejects_invalid_task_id(self, bad_id):
        with pytest.raises((TypeError, ValueError)):
            make_task(task_id=bad_id)

    @pytest.mark.parametrize("bad_id", [None, 1, Path("x")])
    def test_rejects_non_string_task_id(self, bad_id):
        with pytest.raises(TypeError, match="must be a str"):
            make_task(task_id=bad_id)

    def test_rejects_string_argv(self):
        with pytest.raises(TypeError, match="not a string"):
            make_task(argv="rosetta_scripts -s input.pdb")

    def test_rejects_empty_argv(self):
        with pytest.raises(ValueError, match="at least the executable request token"):
            make_task(argv=())

    def test_rejects_empty_token(self):
        with pytest.raises(ValueError, match="empty token"):
            make_task(argv=("rosetta_scripts", ""))

    def test_rejects_nul_byte_in_token(self):
        with pytest.raises(ValueError, match="NUL byte"):
            make_task(argv=("rosetta_scripts", "-s", "in\x00put.pdb"))

    def test_rejects_foreign_expected_artifact_entries(self):
        with pytest.raises(TypeError, match="ArtifactExpectation"):
            make_task(expected_artifacts=("*.pdb",))

    def test_rejects_foreign_resources(self):
        with pytest.raises(TypeError, match="ResourceRequest"):
            make_task(resources={"cpu_cores": 4})

    def test_rejects_non_string_env_value(self):
        with pytest.raises(TypeError, match="must be a string"):
            make_task(env={"NPROC": 4})

    def test_rejects_non_serializable_metadata(self):
        with pytest.raises(TypeError, match="JSON-serializable"):
            make_task(metadata={"path": Path("/work")})

    def test_rejects_non_string_metadata_keys(self):
        with pytest.raises(TypeError, match="keys must be strings"):
            make_task(metadata={1: "one"})

    def test_rejects_non_finite_metadata(self):
        with pytest.raises(TypeError, match="JSON-serializable"):
            make_task(metadata={"value": float("nan")})


class TestTaskSpecImmutability:
    def test_is_frozen(self):
        task = make_task()
        with pytest.raises(dataclasses.FrozenInstanceError):
            task.task_id = "other"  # type: ignore[misc]

    def test_detaches_env_from_caller_mapping(self):
        env = {"NPROC": "4"}
        task = make_task(env=env)
        env["NPROC"] = "8"
        assert task.env == {"NPROC": "4"}

    def test_detaches_metadata_from_caller_mapping(self):
        metadata = {"stage": "relax"}
        task = make_task(metadata=metadata)
        metadata["stage"] = "mutate"
        assert task.metadata == {"stage": "relax"}

    def test_equivalent_tasks_are_equal(self):
        assert make_task() == make_task()

    def test_tasks_are_unhashable_because_metadata_is_a_mapping(self):
        """Frozen means immutable fields, not hashability: mapping fields are unhashable."""
        with pytest.raises(TypeError, match="unhashable"):
            hash(make_task())

    def test_differing_tasks_are_not_equal(self):
        assert make_task(task_id="a") != make_task(task_id="b")


class TestTaskSpecSerialization:
    def test_as_dict_contains_json_friendly_values(self):
        task = make_task(
            argv=("rosetta_scripts", "-s", "input.pdb"),
            env={"NPROC": "4"},
            inputs=("/data/in.pdb",),
            output_root="/work/out",
            expected_artifacts=(ArtifactExpectation(role=ArtifactRole.SCOREFILE, pattern="*.sc", required=True),),
            resources=ResourceRequest(cpu_cores=4),
            metadata={"run_id": "run-a"},
        )
        payload = task.as_dict()

        assert payload["task_id"] == "run-a"
        assert payload["argv"] == ["rosetta_scripts", "-s", "input.pdb"]
        assert payload["cwd"] == "/work"
        assert payload["env"] == {"NPROC": "4"}
        assert payload["inputs"] == ["/data/in.pdb"]
        assert payload["output_root"] == "/work/out"
        assert payload["expected_artifacts"] == [{"role": "scorefile", "pattern": "*.sc", "required": True}]
        assert payload["resources"] == {"cpu_cores": 4, "memory_mb": None}
        assert payload["metadata"] == {"run_id": "run-a"}
