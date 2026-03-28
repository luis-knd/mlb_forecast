"""
Player stats persistence models.
These tables store forecast-oriented player stats and supporting history.
"""

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from infrastructure.db.database import Base


class _PlayerStatsMetadataMixin:
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(Integer, nullable=False)
    game_type = Column(String(5), nullable=False, default="R")
    source = Column(String(30), nullable=False, default="statsapi")
    source_updated_at = Column(DateTime(timezone=True), nullable=True)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PlayerHittingStatsModel(_PlayerStatsMetadataMixin, Base):
    """SQLAlchemy model for persisted player hitting stats."""

    __tablename__ = "player_hitting_stats"

    id = Column(Integer, primary_key=True, index=True)
    games_played = Column(Integer, default=0)
    at_bats = Column(Integer, default=0)
    plate_appearances = Column(Integer, default=0)
    hits = Column(Integer, default=0)
    doubles = Column(Integer, default=0)
    triples = Column(Integer, default=0)
    home_runs = Column(Integer, default=0)
    runs_scored = Column(Integer, default=0)
    runs_batted_in = Column(Integer, default=0)
    stolen_bases = Column(Integer, default=0)
    caught_stealing = Column(Integer, default=0)
    base_on_balls = Column(Integer, default=0)
    strikeouts = Column(Integer, default=0)
    hit_by_pitch = Column(Integer, default=0)
    sacrifice_hits = Column(Integer, default=0)
    sacrifice_flies = Column(Integer, default=0)
    left_on_base = Column(Integer, default=0)
    intentional_walks = Column(Integer, default=0)
    total_bases = Column(Integer, default=0)
    batting_average = Column(Float, default=0.0)
    on_base_percentage = Column(Float, default=0.0)
    slugging_percentage = Column(Float, default=0.0)
    ops = Column(Float, default=0.0)
    babip = Column(Float, default=0.0)
    at_bats_per_home_run = Column(Float, default=0.0)
    stolen_base_percentage = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("player_id", "team_id", "season", "game_type", name="uq_player_hitting_stats_context"),
        Index("idx_player_hitting_stats_player_season", "player_id", "season"),
        Index("idx_player_hitting_stats_player_group", "player_id", "game_type"),
    )


class PlayerPitchingStatsModel(_PlayerStatsMetadataMixin, Base):
    """SQLAlchemy model for persisted player pitching stats."""

    __tablename__ = "player_pitching_stats"

    id = Column(Integer, primary_key=True, index=True)
    games_played = Column(Integer, default=0)
    games_started = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    save_opportunities = Column(Integer, default=0)
    holds = Column(Integer, default=0)
    blown_saves = Column(Integer, default=0)
    innings_pitched = Column(Float, default=0.0)
    batters_faced = Column(Integer, default=0)
    hits_allowed = Column(Integer, default=0)
    runs_allowed = Column(Integer, default=0)
    earned_runs = Column(Integer, default=0)
    home_runs_allowed = Column(Integer, default=0)
    strikeouts = Column(Integer, default=0)
    base_on_balls = Column(Integer, default=0)
    intentional_walks = Column(Integer, default=0)
    hit_batsmen = Column(Integer, default=0)
    wild_pitches = Column(Integer, default=0)
    balks = Column(Integer, default=0)
    number_of_pitches = Column(Integer, default=0)
    complete_games = Column(Integer, default=0)
    shutouts = Column(Integer, default=0)
    outs = Column(Integer, default=0)
    strikes = Column(Integer, default=0)
    pickoffs = Column(Integer, default=0)
    quality_starts = Column(Integer, default=0)
    earned_run_average = Column(Float, default=0.0)
    whip = Column(Float, default=0.0)
    strikeouts_per_nine = Column(Float, default=0.0)
    walks_per_nine = Column(Float, default=0.0)
    hits_per_nine = Column(Float, default=0.0)
    home_runs_per_nine = Column(Float, default=0.0)
    strikeout_to_walk_ratio = Column(Float, default=0.0)
    pitches_per_inning = Column(Float, default=0.0)
    batting_average_against = Column(Float, default=0.0)
    on_base_percentage = Column(Float, default=0.0)
    slugging_percentage = Column(Float, default=0.0)
    ops = Column(Float, default=0.0)
    strike_percentage = Column(Float, default=0.0)
    win_percentage = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("player_id", "team_id", "season", "game_type", name="uq_player_pitching_stats_context"),
        Index("idx_player_pitching_stats_player_season", "player_id", "season"),
        Index("idx_player_pitching_stats_player_group", "player_id", "game_type"),
    )


class PlayerFieldingStatsModel(_PlayerStatsMetadataMixin, Base):
    """SQLAlchemy model for persisted player fielding stats."""

    __tablename__ = "player_fielding_stats"

    id = Column(Integer, primary_key=True, index=True)
    games_played = Column(Integer, default=0)
    games_started = Column(Integer, default=0)
    innings_played = Column(Float, default=0.0)
    total_chances = Column(Integer, default=0)
    putouts = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    throwing_errors = Column(Integer, default=0)
    double_plays = Column(Integer, default=0)
    triple_plays = Column(Integer, default=0)
    outfield_assists = Column(Integer, default=0)
    passed_balls = Column(Integer, default=0)
    wild_pitches = Column(Integer, default=0)
    stolen_bases_allowed = Column(Integer, default=0)
    caught_stealing = Column(Integer, default=0)
    catchers_interference = Column(Integer, default=0)
    pickoffs = Column(Integer, default=0)
    fielding_percentage = Column(Float, default=0.0)
    defensive_efficiency_ratio = Column(Float, default=0.0)
    range_factor_per_game = Column(Float, default=0.0)
    range_factor_per_nine = Column(Float, default=0.0)
    stolen_base_percentage = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("player_id", "team_id", "season", "game_type", name="uq_player_fielding_stats_context"),
        Index("idx_player_fielding_stats_player_season", "player_id", "season"),
        Index("idx_player_fielding_stats_player_group", "player_id", "game_type"),
    )


class PlayerCatchingStatsModel(_PlayerStatsMetadataMixin, Base):
    """SQLAlchemy model for persisted player catching stats."""

    __tablename__ = "player_catching_stats"

    id = Column(Integer, primary_key=True, index=True)
    games_played = Column(Integer, default=0)
    games_pitched = Column(Integer, default=0)
    at_bats = Column(Integer, default=0)
    hits = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    home_runs = Column(Integer, default=0)
    strikeouts = Column(Integer, default=0)
    base_on_balls = Column(Integer, default=0)
    intentional_walks = Column(Integer, default=0)
    hit_by_pitch = Column(Integer, default=0)
    total_bases = Column(Integer, default=0)
    sacrifice_bunts = Column(Integer, default=0)
    sacrifice_flies = Column(Integer, default=0)
    passed_balls = Column(Integer, default=0)
    wild_pitches = Column(Integer, default=0)
    stolen_bases_allowed = Column(Integer, default=0)
    caught_stealing = Column(Integer, default=0)
    pickoffs = Column(Integer, default=0)
    pickoff_attempts = Column(Integer, default=0)
    catchers_interference = Column(Integer, default=0)
    earned_runs = Column(Integer, default=0)
    batters_faced = Column(Integer, default=0)
    hit_batsmen = Column(Integer, default=0)
    batting_average = Column(Float, default=0.0)
    on_base_percentage = Column(Float, default=0.0)
    slugging_percentage = Column(Float, default=0.0)
    ops = Column(Float, default=0.0)
    stolen_base_percentage = Column(Float, default=0.0)
    strikeout_walk_ratio = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("player_id", "team_id", "season", "game_type", name="uq_player_catching_stats_context"),
        Index("idx_player_catching_stats_player_season", "player_id", "season"),
        Index("idx_player_catching_stats_player_group", "player_id", "game_type"),
    )


class PlayerRunningStatsModel(_PlayerStatsMetadataMixin, Base):
    """SQLAlchemy model for persisted player running stats."""

    __tablename__ = "player_running_stats"

    id = Column(Integer, primary_key=True, index=True)
    games_played = Column(Integer, default=0)
    plate_appearances = Column(Integer, default=0)
    stolen_bases = Column(Integer, default=0)
    stolen_base_percentage = Column(Float, default=0.0)
    caught_stealing = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    base_on_balls = Column(Integer, default=0)
    opportunities = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("player_id", "team_id", "season", "game_type", name="uq_player_running_stats_context"),
        Index("idx_player_running_stats_player_season", "player_id", "season"),
        Index("idx_player_running_stats_player_group", "player_id", "game_type"),
    )


class _PlayerStatsHistoryMixin:
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    season = Column(Integer, nullable=False)
    game_type = Column(String(5), nullable=False, default="R")
    stat_group = Column(String(20), nullable=False)
    external_reference = Column(String(128), nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False)
    context_key = Column(String(64), nullable=True)
    context_value = Column(String(128), nullable=True)
    context_label = Column(String(255), nullable=True)
    source = Column(String(30), nullable=False, default="statsapi")
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PlayerGameLogModel(_PlayerStatsHistoryMixin, Base):
    """SQLAlchemy model for persisted player game logs."""

    __tablename__ = "player_game_logs"

    id = Column(Integer, primary_key=True, index=True)

    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "game_type",
            "stat_group",
            "external_reference",
            name="uq_player_game_logs_context",
        ),
        Index("idx_player_game_logs_player_season", "player_id", "season"),
        Index("idx_player_game_logs_player_group", "player_id", "stat_group"),
        Index("idx_player_game_logs_event_date", "event_date"),
    )


class PlayerStatSplitModel(_PlayerStatsHistoryMixin, Base):
    """SQLAlchemy model for persisted player stat splits."""

    __tablename__ = "player_stat_splits"

    id = Column(Integer, primary_key=True, index=True)

    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "game_type",
            "stat_group",
            "external_reference",
            name="uq_player_stat_splits_context",
        ),
        Index("idx_player_stat_splits_player_season", "player_id", "season"),
        Index("idx_player_stat_splits_player_group", "player_id", "stat_group"),
        Index("idx_player_stat_splits_context", "context_key", "context_value"),
    )
