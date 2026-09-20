"""
Internal JSON value handling for the v2 kernel.

The v2 contracts require task metadata, execution provenance, and serialized run
manifests to be JSON-serializable. This module provides the shared type aliases
and the validation helpers used by the data models so that a contract violation
is reported where the object is constructed rather than when a manifest is
written.
"""

from __future__ import annotations

import json
from collections.abc import Mapping as MappingABC
from typing import Any, Dict, Mapping, Sequence, Union

JSONScalar = Union[None, bool, int, float, str]
"""Scalar values representable as JSON."""

JSONValue = Union[JSONScalar, Sequence["JSONValue"], Mapping[str, "JSONValue"]]
"""Any value representable as JSON.

Metadata and provenance mappings are validated against this type at
construction time. Instances are stored as ordinary (picklable) containers and
MUST be treated as read-only by consumers.
"""


def _assert_string_keys(value: Any, *, where: str, seen: set) -> None:
    """
    Recursively assert that every mapping key in ``value`` is a string.

    ``json.dumps`` silently converts non-string scalar keys into strings, so this
    check runs before the JSON-serializability check to keep the failure
    explicit.
    """
    if isinstance(value, MappingABC):
        if id(value) in seen:  # pragma: no cover - circular input; json.dumps rejects it too
            return
        seen.add(id(value))
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{where} keys must be strings, got {type(key).__name__}")
            _assert_string_keys(item, where=where, seen=seen)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_string_keys(item, where=where, seen=seen)


def ensure_json_value(value: Any, *, where: str = "value") -> None:
    """
    Validate that ``value`` can be represented as JSON.

    Args:
        value: Candidate JSON value.
        where: Field name used in error messages.

    Raises:
        TypeError: If ``value`` contains non-string mapping keys, non-finite
            floats, or objects that the JSON encoder cannot represent.
    """
    _assert_string_keys(value, where=where, seen=set())
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{where} must be JSON-serializable: {exc}") from exc


def freeze_json_mapping(value: Any, *, where: str = "metadata") -> Dict[str, JSONValue]:
    """
    Validate a JSON mapping and return a detached, plain-``dict`` copy.

    The copy prevents later mutation of the caller's mapping from leaking into a
    frozen data model. Consumers MUST still treat the returned mapping as
    read-only; the contract does not require a persistent-map dependency.
    """
    if not isinstance(value, MappingABC):
        raise TypeError(f"{where} must be a mapping, got {type(value).__name__}")
    ensure_json_value(value, where=where)
    return dict(value)


def freeze_string_mapping(value: Any, *, where: str = "env") -> Dict[str, str]:
    """
    Validate a ``str``-to-``str`` mapping and return a detached copy.

    Used for ``TaskSpec.env`` and ``CompileContext.env``, which are environment
    overlays rather than arbitrary JSON payloads.
    """
    if not isinstance(value, MappingABC):
        raise TypeError(f"{where} must be a mapping, got {type(value).__name__}")
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{where} keys must be strings, got {type(key).__name__}")
        if not isinstance(item, str):
            raise TypeError(f"{where}[{key!r}] must be a string, got {type(item).__name__}")
    return dict(value)


def ensure_argument_token(value: Any, *, where: str = "argv") -> str:
    """
    Validate a single shell-free argument token.

    Tokens are passed to executors as elements of an argument vector, never as a
    shell string, so an embedded NUL byte and an empty token are both rejected.
    Spaces *inside* a token are legal and are the reason the kernel keeps
    argument vectors tokenized.
    """
    if not isinstance(value, str):
        raise TypeError(f"{where} must be a str, got {type(value).__name__}")
    if not value:
        raise ValueError(f"{where} must not be an empty token")
    if "\x00" in value:
        raise ValueError(f"{where} must not contain a NUL byte")
    return value
