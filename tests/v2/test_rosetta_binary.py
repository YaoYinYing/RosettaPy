"""Unit tests for the v2 Rosetta binary request model."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from RosettaPy.rosetta import RosettaBinaryRequest


class TestRosettaBinaryRequest:
    def test_requires_exactly_one_of_name_and_path(self):
        with pytest.raises(ValueError, match="exactly one of 'name' or 'path'"):
            RosettaBinaryRequest()
        with pytest.raises(ValueError, match="exactly one of 'name' or 'path'"):
            RosettaBinaryRequest(name="rosetta_scripts", path="/usr/bin/rosetta_scripts")

    def test_logical_name_request(self):
        request = RosettaBinaryRequest(name="rosetta_scripts")
        assert request.token == "rosetta_scripts"
        assert request.is_logical is True
        assert request.path is None

    def test_explicit_path_request(self):
        request = RosettaBinaryRequest(path="/opt/rosetta/bin/rosetta_scripts.linuxgccrelease")
        assert request.token == "/opt/rosetta/bin/rosetta_scripts.linuxgccrelease"
        assert request.is_logical is False
        assert request.name is None

    def test_path_is_coerced(self):
        assert RosettaBinaryRequest(path=Path("/opt/bin/rosetta_scripts")).path == Path("/opt/bin/rosetta_scripts")

    def test_token_is_not_resolved_or_normalized(self):
        request = RosettaBinaryRequest(path="/opt/../opt/bin/rosetta_scripts")
        assert request.token == "/opt/../opt/bin/rosetta_scripts"

    @pytest.mark.parametrize("bad_name", ["", "bin/rosetta_scripts", "a b", "../rosetta_scripts", "x" * 129])
    def test_rejects_invalid_logical_names(self, bad_name):
        with pytest.raises((TypeError, ValueError)):
            RosettaBinaryRequest(name=bad_name)

    def test_rejects_non_string_name(self):
        with pytest.raises(TypeError, match="must be a str"):
            RosettaBinaryRequest(name=Path("rosetta_scripts"))

    def test_factories(self):
        assert RosettaBinaryRequest.from_name("rosetta_scripts").name == "rosetta_scripts"
        assert RosettaBinaryRequest.from_path("/usr/bin/rosetta_scripts").path == Path("/usr/bin/rosetta_scripts")

    def test_is_frozen_and_hashable(self):
        request = RosettaBinaryRequest(name="rosetta_scripts")
        assert len({request, RosettaBinaryRequest(name="rosetta_scripts")}) == 1
        with pytest.raises(dataclasses.FrozenInstanceError):
            request.name = "other"  # type: ignore[misc]

    def test_as_dict(self):
        assert RosettaBinaryRequest(name="rosetta_scripts").as_dict() == {"name": "rosetta_scripts", "path": None}
        assert RosettaBinaryRequest(path="/usr/bin/rosetta_scripts").as_dict() == {
            "name": None,
            "path": "/usr/bin/rosetta_scripts",
        }
