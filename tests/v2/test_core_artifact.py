"""Unit tests for the v2 artifact model."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from RosettaPy.core import Artifact, ArtifactExpectation, ArtifactManifest, ArtifactRole


def make_artifact(name: str = "out.pdb", role: ArtifactRole = ArtifactRole.STRUCTURE, **kwargs) -> Artifact:
    return Artifact(path=Path("/out") / name, role=role, size_bytes=kwargs.pop("size_bytes", 10), **kwargs)


class TestArtifactRole:
    def test_declares_the_initial_roles(self):
        assert {role.value for role in ArtifactRole} == {
            "structure",
            "scorefile",
            "silent_file",
            "log",
            "generic_output",
        }

    def test_is_a_string_enum(self):
        assert ArtifactRole.STRUCTURE == "structure"
        assert str(ArtifactRole.LOG) == "log"


class TestArtifactExpectation:
    def test_defaults_to_optional(self):
        expectation = ArtifactExpectation(role=ArtifactRole.SCOREFILE, pattern="*.sc")
        assert expectation.required is False
        assert expectation.relative_parts == ("*.sc",)

    def test_accepts_nested_relative_patterns(self):
        expectation = ArtifactExpectation(role=ArtifactRole.LOG, pattern="logs/*.txt")
        assert expectation.relative_parts == ("logs", "*.txt")

    def test_accepts_single_character_and_double_star(self):
        assert ArtifactExpectation(role=ArtifactRole.STRUCTURE, pattern="?.pdb").pattern == "?.pdb"
        assert ArtifactExpectation(role=ArtifactRole.STRUCTURE, pattern="**/*.pdb").pattern == "**/*.pdb"

    def test_rejects_empty_pattern(self):
        with pytest.raises(ValueError, match="must not be empty"):
            ArtifactExpectation(role=ArtifactRole.STRUCTURE, pattern="")

    def test_rejects_absolute_pattern(self):
        with pytest.raises(ValueError, match="relative to the task output root"):
            ArtifactExpectation(role=ArtifactRole.STRUCTURE, pattern="/out/*.pdb")

    def test_rejects_pattern_escaping_output_root(self):
        with pytest.raises(ValueError, match="escape the task output root"):
            ArtifactExpectation(role=ArtifactRole.STRUCTURE, pattern="../*.pdb")

    def test_rejects_nul_byte(self):
        with pytest.raises(ValueError, match="NUL byte"):
            ArtifactExpectation(role=ArtifactRole.STRUCTURE, pattern="*.pd\x00b")

    def test_rejects_non_role(self):
        with pytest.raises(TypeError, match="ArtifactRole"):
            ArtifactExpectation(role="structure", pattern="*.pdb")

    def test_rejects_non_string_pattern(self):
        with pytest.raises(TypeError, match="must be a str"):
            ArtifactExpectation(role=ArtifactRole.STRUCTURE, pattern=Path("*.pdb"))

    def test_rejects_non_bool_required(self):
        with pytest.raises(TypeError, match="must be a bool"):
            ArtifactExpectation(role=ArtifactRole.STRUCTURE, pattern="*.pdb", required="yes")


class TestArtifact:
    def test_coerces_path(self):
        artifact = Artifact(path="/out/out.pdb", role=ArtifactRole.STRUCTURE, size_bytes=1)
        assert artifact.path == Path("/out/out.pdb")

    def test_sha256_is_optional(self):
        assert make_artifact().sha256 is None
        assert make_artifact(sha256="abc").sha256 == "abc"

    def test_rejects_negative_size(self):
        with pytest.raises(ValueError, match="must not be negative"):
            make_artifact(size_bytes=-1)

    def test_rejects_bool_size(self):
        with pytest.raises(TypeError, match="must be an int"):
            make_artifact(size_bytes=True)

    def test_rejects_non_role(self):
        with pytest.raises(TypeError, match="ArtifactRole"):
            Artifact(path=Path("out.pdb"), role="structure", size_bytes=1)

    def test_rejects_non_string_sha256(self):
        with pytest.raises(TypeError, match="sha256 must be a str or None"):
            make_artifact(sha256=123)

    def test_as_dict(self):
        artifact = make_artifact(name="run.score.sc", role=ArtifactRole.SCOREFILE, size_bytes=42)
        assert artifact.as_dict() == {
            "path": "/out/run.score.sc",
            "role": "scorefile",
            "size_bytes": 42,
            "sha256": None,
        }


class TestArtifactManifest:
    def test_empty_manifest_is_complete(self):
        manifest = ArtifactManifest()
        assert len(manifest) == 0
        assert manifest.complete is True
        assert manifest.by_role(ArtifactRole.STRUCTURE) == ()

    def test_is_a_sequence_not_a_role_mapping(self):
        manifest = ArtifactManifest(
            artifacts=(
                make_artifact("a.pdb"),
                make_artifact("b.pdb"),
                make_artifact("run.score.sc", ArtifactRole.SCOREFILE),
            )
        )
        assert len(list(manifest)) == 3
        assert [artifact.path.name for artifact in manifest.by_role(ArtifactRole.STRUCTURE)] == ["a.pdb", "b.pdb"]
        assert manifest.first(ArtifactRole.SCOREFILE).path.name == "run.score.sc"

    def test_missing_required_makes_manifest_incomplete(self):
        manifest = ArtifactManifest(missing_required=("*.silent",))
        assert manifest.complete is False
        assert manifest.first(ArtifactRole.SILENT_FILE) is None

    def test_rejects_foreign_artifact_entries(self):
        with pytest.raises(TypeError, match="Artifact instances"):
            ArtifactManifest(artifacts=("a.pdb",))

    def test_rejects_non_string_missing_pattern(self):
        with pytest.raises(TypeError, match="must contain strings"):
            ArtifactManifest(missing_required=(Path("*.silent"),))

    def test_rejects_negative_unexpected_count(self):
        with pytest.raises(ValueError, match="must not be negative"):
            ArtifactManifest(unexpected_count=-1)

    def test_rejects_bool_unexpected_count(self):
        with pytest.raises(TypeError, match="must be an int"):
            ArtifactManifest(unexpected_count=True)

    def test_is_frozen_and_hashable(self):
        manifest = ArtifactManifest(artifacts=(make_artifact(),))
        assert len({manifest, ArtifactManifest(artifacts=(make_artifact(),))}) == 1
        with pytest.raises(dataclasses.FrozenInstanceError):
            manifest.artifacts = ()  # type: ignore[misc]

    def test_from_artifacts_accepts_any_sequence(self):
        manifest = ArtifactManifest.from_artifacts([make_artifact()], unexpected_count=1)
        assert len(manifest) == 1
        assert manifest.unexpected_count == 1

    def test_as_dict(self):
        manifest = ArtifactManifest(artifacts=(make_artifact(name="a.pdb"),), missing_required=("*.silent",))
        payload = manifest.as_dict()
        assert payload["missing_required"] == ["*.silent"]
        assert payload["unexpected_count"] == 0
        assert payload["artifacts"][0]["role"] == "structure"
