from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias

from domain.entities.game import Game
from domain.entities.player import Player
from domain.entities.team import Team
from interface.rest.adapters.mappers import to_team_dto
from interface.rest.exception_handlers import DomainExceptions

IncludeTree: TypeAlias = dict[str, "IncludeTree"]
AllowedIncludeTree: TypeAlias = Mapping[str, "AllowedIncludeTree"]

_TEAM_ALLOWED_INCLUDES: IncludeTree = {
    "id": {},
    "mlb_id": {},
    "name": {},
    "abbreviation": {},
    "city": {},
    "division": {},
    "league": {},
    "venue_name": {},
    "created_at": {},
    "updated_at": {},
}

PLAYER_ALLOWED_INCLUDES: AllowedIncludeTree = {"current_team": _TEAM_ALLOWED_INCLUDES}
GAME_ALLOWED_INCLUDES: AllowedIncludeTree = {
    "home_team": _TEAM_ALLOWED_INCLUDES,
    "away_team": _TEAM_ALLOWED_INCLUDES,
    "winning_team": _TEAM_ALLOWED_INCLUDES,
}
TEAM_PAYLOAD_FIELDS = tuple(_TEAM_ALLOWED_INCLUDES.keys())


@dataclass(frozen=True)
class IncludeSelection:
    tree: IncludeTree
    full_relations: frozenset[str]

    def includes(self, relation_name: str) -> bool:
        return relation_name in self.tree

    def includes_full_relation(self, relation_name: str) -> bool:
        return relation_name in self.full_relations

    def relation_fields(self, relation_name: str) -> IncludeTree:
        return self.tree.get(relation_name, {})


def parse_include_selection(
    raw_include: str | Sequence[str] | None,
    allowed_tree: AllowedIncludeTree,
) -> IncludeSelection:
    include_tree: IncludeTree = {}
    full_relations: set[str] = set()

    for include_path in _normalize_include_values(raw_include):
        _validate_include_path(include_path, allowed_tree)
        segments = include_path.split(".")
        _merge_include_path(include_tree, segments)
        if len(segments) == 1:
            full_relations.add(segments[0])

    return IncludeSelection(tree=include_tree, full_relations=frozenset(full_relations))


def to_player_response_payload(player: Player, include: IncludeSelection) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": player.id,
        "mlb_id": player.mlb_id,
        "first_name": player.first_name,
        "last_name": player.last_name,
        "full_name": player.full_name(),
        "position": player.position,
        "bats": player.bats,
        "throws": player.throws,
        "birth_date": player.birth_date,
        "active": player.active,
        "current_team_id": player.current_team_id,
        "created_at": player.created_at,
        "updated_at": player.updated_at,
    }

    if include.includes("current_team"):
        payload["current_team"] = _to_team_payload(
            player.current_team,
            selected_fields=include.relation_fields("current_team"),
            include_full_relation=include.includes_full_relation("current_team"),
        )

    return payload


def to_player_response_payload_list(players: Sequence[Player], include: IncludeSelection) -> list[dict[str, Any]]:
    return [to_player_response_payload(player, include) for player in players]


def to_game_response_payload(game: Game, include: IncludeSelection) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": game.id,
        "mlb_game_id": game.mlb_game_id,
        "home_team_id": game.home_team_id,
        "away_team_id": game.away_team_id,
        "game_date": game.game_date,
        "status": game.status,
        "scheduled_innings": game.scheduled_innings,
        "home_score": game.home_score,
        "away_score": game.away_score,
        "winning_team_id": game.winning_team_id,
        "created_at": game.created_at,
        "updated_at": game.updated_at,
    }

    if include.includes("home_team"):
        payload["home_team"] = _to_team_payload(
            game.home_team,
            selected_fields=include.relation_fields("home_team"),
            include_full_relation=include.includes_full_relation("home_team"),
        )
    if include.includes("away_team"):
        payload["away_team"] = _to_team_payload(
            game.away_team,
            selected_fields=include.relation_fields("away_team"),
            include_full_relation=include.includes_full_relation("away_team"),
        )
    if include.includes("winning_team"):
        payload["winning_team"] = _to_team_payload(
            game.winning_team,
            selected_fields=include.relation_fields("winning_team"),
            include_full_relation=include.includes_full_relation("winning_team"),
        )

    return payload


def to_game_response_payload_list(games: Sequence[Game], include: IncludeSelection) -> list[dict[str, Any]]:
    return [to_game_response_payload(game, include) for game in games]


def _normalize_include_values(raw_include: str | Sequence[str] | None) -> tuple[str, ...]:
    if raw_include is None:
        return ()

    include_values = [raw_include] if isinstance(raw_include, str) else list(raw_include)
    normalized_values: list[str] = []
    seen_values: set[str] = set()

    for include_value in include_values:
        for raw_path in include_value.split(","):
            include_path = raw_path.strip()
            if not include_path or include_path in seen_values:
                continue
            normalized_values.append(include_path)
            seen_values.add(include_path)

    return tuple(normalized_values)


def _validate_include_path(include_path: str, allowed_tree: AllowedIncludeTree) -> None:
    current_tree = allowed_tree

    for segment in include_path.split("."):
        if not segment or segment not in current_tree:
            allowed_paths = ", ".join(sorted(allowed_tree.keys()))
            raise DomainExceptions.InvalidDataError(
                f"Invalid include path '{include_path}'. Allowed include roots: {allowed_paths}"
            )
        current_tree = current_tree[segment]


def _merge_include_path(include_tree: IncludeTree, segments: list[str]) -> None:
    current_tree = include_tree

    for segment in segments:
        current_tree = current_tree.setdefault(segment, {})


def _to_team_payload(
    team: Team | None,
    selected_fields: IncludeTree,
    include_full_relation: bool,
) -> Any:
    if team is None:
        return None
    team_payload = to_team_dto(team).model_dump()

    if include_full_relation or not selected_fields:
        return team_payload

    return {field_name: team_payload[field_name] for field_name in TEAM_PAYLOAD_FIELDS if field_name in selected_fields}
