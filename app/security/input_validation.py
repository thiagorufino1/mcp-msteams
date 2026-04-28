"""Input validation for Microsoft Graph API tool parameters."""

import re

from app.graph.errors import GraphValidationError

_UPN_RE = re.compile(r'^[\w.+\-]+@[\w\-]+\.[a-zA-Z]{2,}$')
_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


def validate_upn(upn: str) -> str:
    """
    Validate and normalize a UPN (User Principal Name).

    Args:
        upn: The user principal name to validate.

    Returns:
        The normalized (lowercased) UPN.

    Raises:
        GraphValidationError: If the UPN format is invalid.
    """
    if not _UPN_RE.match(upn.strip()):
        raise GraphValidationError(f"Invalid UPN format: {upn!r}")
    return upn.strip().lower()


def validate_uuid(value: str, name: str = "ID") -> str:
    """
    Validate and normalize a UUID.

    Args:
        value: The UUID string to validate.
        name: The name of the field being validated (for error messages).

    Returns:
        The normalized (lowercased) UUID.

    Raises:
        GraphValidationError: If the UUID format is invalid.
    """
    if not _UUID_RE.match(value.strip()):
        raise GraphValidationError(f"Invalid {name} format: {value!r}")
    return value.strip().lower()


def validate_days(days: int, *, min_days: int = 1, max_days: int = 30) -> int:
    """
    Validate a number of days within a specified range.

    Args:
        days: The number of days to validate.
        min_days: The minimum allowed value (inclusive). Defaults to 1.
        max_days: The maximum allowed value (inclusive). Defaults to 30.

    Returns:
        The validated days value.

    Raises:
        GraphValidationError: If days is outside the specified range.
    """
    if not (min_days <= days <= max_days):
        raise GraphValidationError(f"days must be between {min_days} and {max_days}, got {days}")
    return days
