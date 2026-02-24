"""Domain-level exceptions shared across application and interface layers."""


class TeamNotFoundError(Exception):
    """Raised when a team is not found."""

    def __init__(self, team_id: int) -> None:
        self.team_id = team_id
        super().__init__(f"Team with ID {team_id} not found")


class PlayerNotFoundError(Exception):
    """Raised when a player is not found."""

    def __init__(self, player_id: int) -> None:
        self.player_id = player_id
        super().__init__(f"Player with ID {player_id} not found")


class GameNotFoundError(Exception):
    """Raised when a game is not found."""

    def __init__(self, game_id: int) -> None:
        self.game_id = game_id
        super().__init__(f"Game with ID {game_id} not found")


class InvalidDataError(Exception):
    """Raised when invalid data is provided."""


class ExternalServiceError(Exception):
    """Raised when external service fails."""

    def __init__(self, service: str, message: str) -> None:
        self.service = service
        super().__init__(f"{service} service error: {message}")
