"""Unit tests for the v2 ``core`` JSON validation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from RosettaPy.core._json import (
    ensure_argument_token,
    ensure_json_value,
    freeze_json_mapping,
    freeze_string_mapping,
)


class TestEnsureJsonValue:
    @pytest.mark.parametrize("value", [None, True, 1, 1.5, "text", [1, "a"], {"a": [1, {"b": None}]}])
    def test_accepts_json_values(self, value):
        assert ensure_json_value(value) is None

    def test_rejects_non_string_keys(self):
        with pytest.raises(TypeError, match="keys must be strings"):
            ensure_json_value({1: "one"})

    def test_rejects_nested_non_string_keys(self):
        with pytest.raises(TypeError, match="keys must be strings"):
            ensure_json_value({"outer": [{2: "two"}]})

    def test_rejects_non_finite_floats(self):
        with pytest.raises(TypeError, match="JSON-serializable"):
            ensure_json_value({"value": float("inf")})

    def test_rejects_arbitrary_objects(self):
        with pytest.raises(TypeError, match="JSON-serializable"):
            ensure_json_value({"path": Path("/tmp")})

    def test_reports_the_field_name(self):
        with pytest.raises(TypeError, match="TaskSpec.metadata"):
            ensure_json_value({"path": Path("/tmp")}, where="TaskSpec.metadata")

    def test_tolerates_a_cycle(self):
        """Cycle detection must not recurse forever; json.dumps is the authority."""
        value: dict = {}
        value["self"] = value
        with pytest.raises(TypeError, match="JSON-serializable"):
            ensure_json_value(value)

    def test_accepts_a_dag_returning_to_one_object(self):
        shared = {"a": 1}
        assert ensure_json_value({"x": shared, "y": shared}) is None


class TestFreezeJsonMapping:
    def test_returns_a_detached_dict(self):
        source = {"a": 1}
        frozen = freeze_json_mapping(source)
        source["a"] = 2
        assert frozen == {"a": 1}
        assert isinstance(frozen, dict)

    def test_rejects_non_mapping(self):
        with pytest.raises(TypeError, match="must be a mapping"):
            freeze_json_mapping(["a"])

    def test_rejects_non_serializable_content(self):
        with pytest.raises(TypeError, match="JSON-serializable"):
            freeze_json_mapping({"path": Path("/tmp")})


class TestFreezeStringMapping:
    def test_returns_a_detached_dict(self):
        source = {"NPROC": "4"}
        frozen = freeze_string_mapping(source)
        source["NPROC"] = "8"
        assert frozen == {"NPROC": "4"}

    def test_rejects_non_mapping(self):
        with pytest.raises(TypeError, match="must be a mapping"):
            freeze_string_mapping("NPROC=4")

    def test_rejects_non_string_keys(self):
        with pytest.raises(TypeError, match="keys must be strings"):
            freeze_string_mapping({1: "one"})

    def test_rejects_non_string_values(self):
        with pytest.raises(TypeError, match=r"env\['NPROC'\] must be a string"):
            freeze_string_mapping({"NPROC": 4})


class TestEnsureArgumentToken:
    def test_accepts_a_plain_token(self):
        assert ensure_argument_token("-s") == "-s"

    def test_accepts_tokens_containing_spaces(self):
        assert ensure_argument_token("/data/my input.pdb") == "/data/my input.pdb"

    def test_rejects_empty_token(self):
        with pytest.raises(ValueError, match="empty token"):
            ensure_argument_token("")

    def test_rejects_nul_byte(self):
        with pytest.raises(ValueError, match="NUL byte"):
            ensure_argument_token("a\x00b")

    def test_rejects_non_string(self):
        with pytest.raises(TypeError, match="must be a str"):
            ensure_argument_token(Path("-s"))

    def test_reports_the_field_name(self):
        with pytest.raises(ValueError, match=r"TaskSpec.argv\[2\]"):
            ensure_argument_token("", where="TaskSpec.argv[2]")
