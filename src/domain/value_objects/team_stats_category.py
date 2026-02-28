"""Value object representing supported team statistics categories."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum


class TeamStatsCategory(str, Enum):
    """Enumeration of the supported statistics categories for a team season."""

    HITTING = "hitting"
    PITCHING = "pitching"
    FIELDING = "fielding"
    CATCHING = "catching"
    ALL = "all"

    @classmethod
    def allowed_values(cls) -> Iterable[str]:
        """Return the canonical list of allowed string values."""
        return tuple(member.value for member in cls)
