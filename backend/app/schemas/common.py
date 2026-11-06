"""Reusable field types shared by request schemas."""

from typing import Annotated

from pydantic import StringConstraints


# Public, human-readable identifiers (batch_id, rfid_id, qr_id, ...).
# Surrounding whitespace is removed *before* validation so that a value such as
# "BATCH-TEST-001 " can neither be stored nor looked up in a form that silently
# fails to match the canonical identifier.  100 matches the String(100) columns.
PublicId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]

# Statuses that gate QR/RFID verification.
TAG_STATUSES = ("ACTIVE", "INACTIVE")


def normalize_tag_status(value: str) -> str:
    """Upper-case and validate a QR/RFID status."""
    normalized = str(value).strip().upper()
    if normalized not in TAG_STATUSES:
        raise ValueError(
            "status must be one of: " + ", ".join(TAG_STATUSES)
        )
    return normalized
