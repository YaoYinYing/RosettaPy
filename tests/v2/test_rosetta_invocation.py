"""Unit tests for the v2 Rosetta invocation model."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from RosettaPy.core.errors import CompilationError
from RosettaPy.rosetta import NStructMode, RosettaBinaryRequest, RosettaInvocation


def make_invocation(**overrides) -> RosettaInvocation:
    kwargs = {"binary": RosettaBinaryRequest(name="rosetta_scripts")}
    kwargs.update(overrides)
    return RosettaInvocation(**kwargs)


class TestRosettaInvocationDefaults:
    def test_defaults(self):
        invocation = make_invocation()
        assert invocation.flags == ()
        assert invocation.options == ()
        assert invocation.script_vars == {}
        assert invocation.nstruct == 1
        assert invocation.nstruct_mode is NStructMode.NATIVE
        assert invocation.mute is True

    def test_carries_rosetta_semantics_only(self):
        """The invocation must not acquire execution-environment state."""
        fields = set(RosettaInvocation.__dataclass_fields__)
        assert fields == {"binary", "flags", "options", "script_vars", "nstruct", "nstruct_mode", "mute"}
        for forbidden in ("image", "container", "executor", "mpi", "slurm", "wsl", "run_node", "nproc"):
            assert forbidden not in fields


class TestRosettaInvocationValidation:
    def test_rejects_foreign_binary(self):
        with pytest.raises(TypeError, match="RosettaBinaryRequest"):
            RosettaInvocation(binary="rosetta_scripts")  # type: ignore[arg-type]

    @pytest.mark.parametrize("value", [0, -1])
    def test_rejects_non_positive_nstruct(self, value):
        with pytest.raises(ValueError, match="must be a positive integer"):
            make_invocation(nstruct=value)

    def test_rejects_bool_nstruct(self):
        with pytest.raises(TypeError, match="must be an int"):
            make_invocation(nstruct=True)

    def test_rejects_non_string_nstruct(self):
        with pytest.raises(TypeError, match="must be an int"):
            make_invocation(nstruct="3")

    def test_rejects_non_mode(self):
        with pytest.raises(TypeError, match="NStructMode"):
            make_invocation(nstruct_mode="native")

    def test_rejects_non_bool_mute(self):
        with pytest.raises(TypeError, match="must be a bool"):
            make_invocation(mute="yes")

    def test_rejects_non_string_script_var_value(self):
        with pytest.raises(TypeError, match="must be a string"):
            make_invocation(script_vars={"n": 3})

    @pytest.mark.parametrize("key", ["", "a=b"])
    def test_rejects_unusable_script_var_keys(self, key):
        with pytest.raises(ValueError, match="script_vars keys"):
            make_invocation(script_vars={key: "1"})

    def test_rejects_empty_option_token(self):
        with pytest.raises(ValueError, match="empty token"):
            make_invocation(options=("",))

    def test_rejects_nul_byte_in_flag_path(self):
        with pytest.raises(ValueError, match="NUL byte"):
            make_invocation(flags=("flags\x00.txt",))


class TestRosettaInvocationFrozenBehaviour:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            make_invocation().nstruct = 3  # type: ignore[misc]

    def test_flags_are_coerced_to_paths(self):
        assert make_invocation(flags=["flags.txt"]).flags == (Path("flags.txt"),)

    def test_detaches_script_vars_from_caller_mapping(self):
        variables = {"n": "3"}
        invocation = make_invocation(script_vars=variables)
        variables["n"] = "9"
        assert invocation.script_vars == {"n": "3"}


class TestRosettaInvocationCopies:
    def test_with_script_vars_preserves_existing_order(self):
        invocation = make_invocation(script_vars={"a": "1", "b": "2"})
        updated = invocation.with_script_vars({"a": "9", "c": "3"})
        assert list(updated.script_vars) == ["a", "b", "c"]
        assert updated.script_vars == {"a": "9", "b": "2", "c": "3"}
        assert invocation.script_vars == {"a": "1", "b": "2"}

    def test_with_options_appends(self):
        updated = make_invocation(options=("-a",)).with_options(["-b", "-c"])
        assert updated.options == ("-a", "-b", "-c")

    def test_with_flags_appends(self):
        updated = make_invocation(flags=("one.txt",)).with_flags(["two.txt"])
        assert updated.flags == (Path("one.txt"), Path("two.txt"))


class TestRosettaInvocationFanOut:
    @pytest.mark.parametrize("nstruct", [1, 4])
    def test_native_mode_compiles_to_a_single_task(self, nstruct):
        assert make_invocation(nstruct=nstruct).fan_out == 1

    @pytest.mark.parametrize("nstruct", [1, 4])
    def test_external_mode_fans_out_per_replica(self, nstruct):
        invocation = make_invocation(nstruct=nstruct, nstruct_mode=NStructMode.EXTERNAL)
        assert invocation.fan_out == nstruct


class TestRosettaInvocationValidationHook:
    def test_accepts_a_plain_request(self):
        assert make_invocation().validate_for_compilation() is None

    def test_accepts_native_nstruct_option(self):
        assert make_invocation(options=("-nstruct", "3")).validate_for_compilation() is None

    def test_rejects_rosetta_internal_nstruct_in_external_mode(self):
        invocation = make_invocation(options=("-nstruct", "3"), nstruct_mode=NStructMode.EXTERNAL)
        with pytest.raises(CompilationError, match="must not contain '-nstruct'"):
            invocation.validate_for_compilation()

    def test_rejects_empty_flag_path(self):
        with pytest.raises(ValueError, match="not empty strings"):
            make_invocation(flags=("",))

    def test_as_dict_is_json_friendly(self):
        invocation = make_invocation(
            flags=("flags.txt",),
            options=("-ex1",),
            script_vars={"n": "3"},
            nstruct=2,
            nstruct_mode=NStructMode.EXTERNAL,
        )
        assert invocation.as_dict() == {
            "binary": {"name": "rosetta_scripts", "path": None},
            "flags": ["flags.txt"],
            "options": ["-ex1"],
            "script_vars": {"n": "3"},
            "nstruct": 2,
            "nstruct_mode": "external",
            "mute": True,
        }
