"""Exception types for the platform-neutral core.

Deliberately few. The core's job is to be embeddable in a KBase SDK app, a
Celery task, a CTS container and an agent-driven CLI, and each of those reports
failure differently — so the core raises typed exceptions and lets the adapter
decide whether that becomes an output.json error block, a job-status row, a
non-zero exit, or a message in a chat.
"""

from __future__ import annotations

__all__ = [
    "PlantSEEDError",
    "ReservedDelimiterError",
    "DataVersionError",
    "CapabilityError",
]


class PlantSEEDError(Exception):
    """Base class for every error raised by the PlantSEED core."""


class ReservedDelimiterError(PlantSEEDError, ValueError):
    """A role or function string contains a delimiter that would corrupt it.

    Subclasses ValueError so that callers written against the stdlib
    convention still catch it.
    """


class DataVersionError(PlantSEEDError):
    """Curated data is missing, unreadable, or fails its manifest checksum."""


class CapabilityError(PlantSEEDError):
    """A capability was invoked with parameters the registry rejects."""
