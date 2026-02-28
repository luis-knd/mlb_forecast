from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MLBTeamDTO:
    """DTO for team data from external MLB API."""

    id: int
    name: str
    abbreviation: str
    city: str
    division: str
    league: str
    venue_name: str | None = None


@dataclass(frozen=True)
class MLBGameDTO:
    """DTO for game data from external MLB API."""

    id: int
    home_team_id: int
    away_team_id: int
    game_date: datetime | None
    status: str
    scheduled_innings: int
    home_score: int | None
    away_score: int | None
    winning_team_id: int | None


@dataclass(frozen=True)
class MLBPlayerDTO:
    """DTO for player data from external MLB API."""

    id: int
    first_name: str
    last_name: str
    position: str
    bats: str
    throws: str
    birth_date: datetime | None
    active: bool
    current_team_id: int | None
