"""Unit tests for the v2 execution result, failure semantics, and run manifest."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from RosettaPy.core import (
    RUN_MANIFEST_SCHEMA_VERSION,
    Artifact,
    ArtifactManifest,
    ArtifactRole,
    ExecutionResult,
    ExecutionStatus,
    RunManifest,
    TaskSpec,
)

STARTED = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
FINISHED = STARTED + timedelta(seconds=2.5)


def make_result(**overrides) -> ExecutionResult:
    kwargs = {
        "task_id": "run-a",
        "status": ExecutionStatus.SUCCEEDED,
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "started_at": STARTED,
        "finished_at": FINISHED,
        "duration_seconds": 2.5,
        "executor": "native",
    }
    kwargs.update(overrides)
    return ExecutionResult(**kwargs)


class TestExecutionStatus:
    def test_declares_the_contract_values(self):
        assert {status.value for status in ExecutionStatus} == {"succeeded", "failed", "timed_out", "cancelled"}

    def test_is_a_string_enum(self):
        assert ExecutionStatus.FAILED == "failed"
        assert str(ExecutionStatus.SUCCEEDED) == "succeeded"


class TestFailureSemantics:
    def test_non_zero_exit_is_a_failed_result_not_an_exception(self):
        result = make_result(status=ExecutionStatus.FAILED, exit_code=1, stderr="boom")
        assert result.failed is True
        assert result.succeeded is False
        assert result.exit_code == 1

    def test_zero_exit_is_a_successful_result(self):
        result = make_result()
        assert result.succeeded is True
        assert result.failed is False

    def test_exit_code_may_be_absent(self):
        assert make_result(status=ExecutionStatus.TIMED_OUT, exit_code=None).exit_code is None


class TestExecutionResultValidation:
    def test_rejects_empty_task_id(self):
        with pytest.raises(TypeError, match="non-empty str"):
            make_result(task_id="")

    def test_rejects_non_status(self):
        with pytest.raises(TypeError, match="ExecutionStatus"):
            make_result(status="succeeded")

    def test_rejects_bool_exit_code(self):
        with pytest.raises(TypeError, match="int or None"):
            make_result(exit_code=True)

    @pytest.mark.parametrize("field", ["stdout", "stderr", "executor"])
    def test_rejects_non_string_text_fields(self, field):
        with pytest.raises(TypeError, match="must be a str"):
            make_result(**{field: None})

    def test_rejects_empty_executor(self):
        with pytest.raises(ValueError, match="executor must not be empty"):
            make_result(executor="")

    @pytest.mark.parametrize("field", ["started_at", "finished_at"])
    def test_rejects_non_datetime_timestamps(self, field):
        with pytest.raises(TypeError, match="must be a datetime"):
            make_result(**{field: "2026-01-02T03:04:05Z"})

    @pytest.mark.parametrize("field", ["started_at", "finished_at"])
    def test_rejects_naive_timestamps(self, field):
        with pytest.raises(ValueError, match="must be timezone-aware"):
            make_result(**{field: datetime(2026, 1, 2, 3, 4, 5)})

    def test_rejects_negative_duration(self):
        with pytest.raises(ValueError, match="must not be negative"):
            make_result(duration_seconds=-0.1)

    def test_rejects_bool_duration(self):
        with pytest.raises(TypeError, match="must be a number"):
            make_result(duration_seconds=True)

    def test_rejects_foreign_artifacts(self):
        with pytest.raises(TypeError, match="ArtifactManifest"):
            make_result(artifacts=())

    def test_rejects_non_serializable_provenance(self):
        with pytest.raises(TypeError, match="JSON-serializable"):
            make_result(provenance={"resolved_binary": Path("/usr/bin/rosetta_scripts")})

    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            make_result().status = ExecutionStatus.FAILED  # type: ignore[misc]


class TestExecutionResultPayload:
    def test_as_dict_is_json_serializable(self):
        result = make_result(
            artifacts=ArtifactManifest(
                artifacts=(Artifact(path=Path("/out/a.pdb"), role=ArtifactRole.STRUCTURE, size_bytes=3),)
            ),
            provenance={"resolved_binary": "/usr/bin/rosetta_scripts"},
        )
        payload = result.as_dict()
        assert payload["status"] == "succeeded"
        assert payload["started_at"] == "2026-01-02T03:04:05+00:00"
        assert payload["finished_at"] == "2026-01-02T03:04:07.500000+00:00"
        assert payload["artifacts"]["artifacts"][0]["path"] == "/out/a.pdb"
        assert payload["provenance"] == {"resolved_binary": "/usr/bin/rosetta_scripts"}
        assert "task" not in payload
        json.loads(json.dumps(payload))

    def test_timestamps_are_normalized_to_utc(self):
        offset = timezone(timedelta(hours=8))
        result = make_result(started_at=STARTED.astimezone(offset), finished_at=FINISHED.astimezone(offset))
        assert result.as_dict()["started_at"] == "2026-01-02T03:04:05+00:00"

    def test_optional_task_is_embedded_when_supplied(self):
        task = TaskSpec(task_id="run-a", argv=("rosetta_scripts", "-s", "in.pdb"), cwd=Path("/work"))
        payload = make_result().as_dict(task=task)
        assert payload["task"]["argv"] == ["rosetta_scripts", "-s", "in.pdb"]
        assert payload["task"]["cwd"] == "/work"


class TestRunManifestContract:
    def test_manifest_owns_a_versioned_schema(self):
        manifest = make_result().to_manifest()
        assert manifest["schema_version"] == RUN_MANIFEST_SCHEMA_VERSION
        assert isinstance(manifest["schema_version"], int)
        assert RUN_MANIFEST_SCHEMA_VERSION == 1

    def test_manifest_is_not_a_bare_asdict_dump(self):
        manifest = make_result().to_manifest()
        assert set(manifest) == {
            "schema_version",
            "task_id",
            "status",
            "exit_code",
            "stdout",
            "stderr",
            "started_at",
            "finished_at",
            "duration_seconds",
            "executor",
            "artifacts",
            "provenance",
        }

    def test_manifest_json_round_trips(self):
        manifest = make_result().to_manifest()
        assert json.loads(make_result().to_manifest_json()) == json.loads(json.dumps(manifest))

    def test_manifest_json_can_be_compact(self):
        assert "\n" not in make_result().to_manifest_json(indent=None)


class TestRunManifestContainer:
    def test_collects_results(self):
        manifest = RunManifest(results=(make_result(),), run_id="run-a")
        assert len(manifest) == 1
        assert len(list(manifest)) == 1
        assert manifest.run_id == "run-a"

    def test_rejects_foreign_results(self):
        with pytest.raises(TypeError, match="ExecutionResult"):
            RunManifest(results=("succeeded",))

    def test_rejects_non_int_schema_version(self):
        with pytest.raises(TypeError, match="schema_version must be an int"):
            RunManifest(schema_version="1")

    def test_rejects_empty_run_id(self):
        with pytest.raises(TypeError, match="non-empty str or None"):
            RunManifest(run_id="")

    def test_serializes_all_results(self):
        manifest = RunManifest(results=(make_result(), make_result(task_id="run-b")), run_id="run-a")
        payload = json.loads(manifest.to_json())
        assert payload["schema_version"] == RUN_MANIFEST_SCHEMA_VERSION
        assert payload["run_id"] == "run-a"
        assert [item["task_id"] for item in payload["results"]] == ["run-a", "run-b"]
