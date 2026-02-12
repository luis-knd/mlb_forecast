from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class MLBTeamDTO:
    """DTO for team data from external MLB API."""

    id: int
    name: str
    abbreviation: str
    city: str
    division: str
    league: str
    venue_name: Optional[str] = None


@dataclass(frozen=True)
class MLBGameDTO:
    """DTO for game data from external MLB API."""

    id: int
    home_team_id: int
    away_team_id: int
    game_date: Optional[datetime]
    status: str
    scheduled_innings: int
    home_score: Optional[int]
    away_score: Optional[int]
    winning_team_id: Optional[int]


@dataclass(frozen=True)
class MLBPlayerDTO:
    """DTO for player data from external MLB API."""

    id: int
    first_name: str
    last_name: str
    position: str
    bats: str
    throws: str
    birth_date: Optional[datetime]
    active: bool
    current_team_id: Optional[int]
