"""Unit tests for the v2 logical identifier helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from RosettaPy.core._naming import (
    IDENTIFIER_PATTERN,
    MAX_IDENTIFIER_LENGTH,
    validate_logical_identifier,
)


class TestValidateLogicalIdentifier:
    @pytest.mark.parametrize(
        "value",
        ["run", "run-1", "run_1", "run.1", "RUN-1.2.3", "0", "a" * MAX_IDENTIFIER_LENGTH],
    )
    def test_accepts_reasonable_identifiers(self, value):
        assert validate_logical_identifier(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "",
            ".run",
            "-run",
            "_run",
            "run/1",
            "..",
            "run 1",
            "run\\1",
            "run\n",
            "run\x00",
            "é-run",
            "a" * (MAX_IDENTIFIER_LENGTH + 1),
        ],
    )
    def test_rejects_unsafe_identifiers(self, value):
        with pytest.raises(ValueError):
            validate_logical_identifier(value)

    def test_rejects_non_string(self):
        with pytest.raises(TypeError, match="must be a str"):
            validate_logical_identifier(Path("run"))

    def test_reports_the_field_name(self):
        with pytest.raises(ValueError, match="CompileContext.run_id"):
            validate_logical_identifier("", where="CompileContext.run_id")

    def test_pattern_matches_the_documented_alphabet(self):
        assert IDENTIFIER_PATTERN.fullmatch("Abc_1.2-3")
        assert not IDENTIFIER_PATTERN.fullmatch("has space")
        assert not IDENTIFIER_PATTERN.fullmatch("run\n")
