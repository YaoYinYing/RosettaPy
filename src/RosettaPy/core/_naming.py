"""
Internal helpers for validating v2 logical identifiers.

A logical identifier is a name that RosettaPy may safely use as an in-memory
key, a file name component, or a directory name component. Identifiers must not
contain path separators so that they can be joined into a path without escaping
the intended parent directory.
"""

from __future__ import annotations

import re
from typing import Any

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
"""Accepted spelling of a logical identifier: an alphanumeric lead character
followed by alphanumerics, dots, underscores, and dashes."""

MAX_IDENTIFIER_LENGTH = 128
"""Upper bound that keeps identifier-derived file names portable."""


def validate_logical_identifier(value: Any, *, where: str = "identifier") -> str:
    """
    Validate that ``value`` is safe to use as a logical identifier.

    Args:
        value: Candidate identifier.
        where: Field name used in error messages.

    Returns:
        The identifier unchanged.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If ``value`` is empty, too long, or contains characters that
            are not allowed in a logical identifier.
    """
    if not isinstance(value, str):
        raise TypeError(f"{where} must be a str, got {type(value).__name__}")
    if not value:
        raise ValueError(f"{where} must not be empty")
    if len(value) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(f"{where} must be at most {MAX_IDENTIFIER_LENGTH} characters, got {len(value)}")
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(
            f"{where} {value!r} is not a valid logical identifier; "
            "expected an alphanumeric lead character followed by [A-Za-z0-9._-]"
        )
    return value
