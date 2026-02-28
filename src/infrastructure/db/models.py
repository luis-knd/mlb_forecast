"""
Database models for the application.
This module defines the SQLAlchemy models for the entities.
"""

from typing import Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func

from src.infrastructure.db.database import Base


class TeamModel(Base):
    """SQLAlchemy model for teams."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    mlb_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    abbreviation = Column(String(10), nullable=False)
    city = Column(String(50), nullable=False)
    division = Column(String(50), nullable=False)
    league = Column(String(20), nullable=False)
    venue_name = Column(String(100))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships with proper type annotations
    home_games: Mapped[list["GameModel"]] = relationship(
        "GameModel", foreign_keys="GameModel.home_team_id", back_populates="home_team"
    )
    away_games: Mapped[list["GameModel"]] = relationship(
        "GameModel", foreign_keys="GameModel.away_team_id", back_populates="away_team"
    )
    hitting_stats: Mapped[list["HittingStatsModel"]] = relationship("HittingStatsModel", back_populates="team")
    pitching_stats: Mapped[list["PitchingStatsModel"]] = relationship("PitchingStatsModel", back_populates="team")
    fielding_stats: Mapped[list["FieldingStatsModel"]] = relationship("FieldingStatsModel", back_populates="team")
    catching_stats: Mapped[list["CatchingStatsModel"]] = relationship("CatchingStatsModel", back_populates="team")
    players: Mapped[list["PlayerModel"]] = relationship("PlayerModel", back_populates="current_team")


class PlayerModel(Base):
    """SQLAlchemy model for players."""

    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    mlb_id = Column(Integer, unique=True, nullable=False, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    position = Column(String(20), nullable=False)
    bats = Column(String(1))  # L, R, S (switch)
    throws = Column(String(1))  # L, R
    birth_date = Column(DateTime)
    active = Column(Boolean, default=True)

    current_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships with proper type annotations
    current_team: Mapped[Optional["TeamModel"]] = relationship("TeamModel", back_populates="players")

    # Indices
    __table_args__ = (
        Index("idx_player_name", "last_name", "first_name"),
        Index("idx_player_position_team", "position", "current_team_id"),
    )


class GameModel(Base):
    """SQLAlchemy model for games."""

    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    mlb_game_id = Column(Integer, unique=True, nullable=False, index=True)

    # Teams
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    # Dates and status
    game_date = Column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_innings = Column(Integer, default=9)
    status = Column(String(20), nullable=False)  # scheduled, in_progress, completed, cancelled

    # Results (null if the game has not finished)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    winning_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships with proper type annotations
    home_team: Mapped["TeamModel"] = relationship("TeamModel", foreign_keys=[home_team_id], back_populates="home_games")
    away_team: Mapped["TeamModel"] = relationship("TeamModel", foreign_keys=[away_team_id], back_populates="away_games")
    winning_team: Mapped[Optional["TeamModel"]] = relationship("TeamModel", foreign_keys=[winning_team_id])
    predictions: Mapped[list["PredictionModel"]] = relationship("PredictionModel", back_populates="game")

    # Indices
    __table_args__ = (
        Index("idx_game_date_teams", "game_date", "home_team_id", "away_team_id"),
        Index("idx_game_status_date", "status", "game_date"),
        Index("idx_game_team_date", "home_team_id", "game_date"),
        Index("idx_game_away_date", "away_team_id", "game_date"),
    )


class HittingStatsModel(Base):
    """SQLAlchemy model for team hitting statistics."""

    __tablename__ = "hitting_stats"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(Integer, nullable=False)

    # Basic stats
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
    ground_into_double_play = Column(Integer, default=0)
    left_on_base = Column(Integer, default=0)

    # Advanced stats
    batting_average = Column(Float, default=0.0)
    on_base_percentage = Column(Float, default=0.0)
    slugging_percentage = Column(Float, default=0.0)
    ops = Column(Float, default=0.0)  # On-base Plus Slugging
    babip = Column(Float, default=0.0)  # Batting Average on Balls In Play
    total_bases = Column(Integer, default=0)
    at_bats_per_home_run = Column(Float, default=0.0)
    stolen_base_percentage = Column(Float, default=0.0)

    # Additional stats
    ground_outs = Column(Integer, default=0)
    air_outs = Column(Integer, default=0)
    ground_outs_to_airouts = Column(Float, default=0.0)
    number_of_pitches = Column(Integer, default=0)
    intentional_walks = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    team: Mapped["TeamModel"] = relationship("TeamModel", back_populates="hitting_stats")

    # Constraints and indices
    __table_args__ = (
        UniqueConstraint("team_id", "season", name="uq_team_season_hitting"),
        Index("idx_hitting_stats_season", "season"),
    )


class PitchingStatsModel(Base):
    """SQLAlchemy model for team pitching statistics."""

    __tablename__ = "pitching_stats"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(Integer, nullable=False)

    # Basic stats
    games_played = Column(Integer, default=0)
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
    games_started = Column(Integer, default=0)
    ground_outs = Column(Integer, default=0)
    air_outs = Column(Integer, default=0)

    # Additional basic stats from MLB API
    doubles = Column(Integer, default=0)
    triples = Column(Integer, default=0)
    at_bats = Column(Integer, default=0)
    outs = Column(Integer, default=0)
    strikes = Column(Integer, default=0)
    pickoffs = Column(Integer, default=0)
    total_bases = Column(Integer, default=0)
    games_finished = Column(Integer, default=0)
    catchers_interference = Column(Integer, default=0)
    sacrifice_bunts = Column(Integer, default=0)
    sacrifice_flies = Column(Integer, default=0)
    ground_into_double_play = Column(Integer, default=0)
    caught_stealing = Column(Integer, default=0)

    # Advanced stats
    earned_run_average = Column(Float, default=0.0)
    whip = Column(Float, default=0.0)  # Walks plus Hits per Inning Pitched
    strikeouts_per_nine = Column(Float, default=0.0)
    walks_per_nine = Column(Float, default=0.0)
    hits_per_nine = Column(Float, default=0.0)
    home_runs_per_nine = Column(Float, default=0.0)
    strikeout_to_walk_ratio = Column(Float, default=0.0)
    ground_outs_to_airouts = Column(Float, default=0.0)
    pitches_per_inning = Column(Float, default=0.0)
    batting_average_against = Column(Float, default=0.0)
    inherited_runners = Column(Integer, default=0)
    inherited_runners_scored = Column(Integer, default=0)
    quality_starts = Column(Integer, default=0)

    # Additional advanced stats from MLB API
    on_base_percentage = Column(Float, default=0.0)
    slugging_percentage = Column(Float, default=0.0)
    ops = Column(Float, default=0.0)
    stolen_base_percentage = Column(Float, default=0.0)
    strike_percentage = Column(Float, default=0.0)
    win_percentage = Column(Float, default=0.0)
    runs_scored_per_nine = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    team: Mapped["TeamModel"] = relationship("TeamModel", back_populates="pitching_stats")

    # Constraints and indices
    __table_args__ = (
        UniqueConstraint("team_id", "season", name="uq_team_season_pitching"),
        Index("idx_pitching_stats_season", "season"),
    )


class FieldingStatsModel(Base):
    """SQLAlchemy model for team fielding statistics."""

    __tablename__ = "fielding_stats"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(Integer, nullable=False)

    # Basic stats
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
    fielding_percentage = Column(Float, default=0.0)
    defensive_efficiency_ratio = Column(Float, default=0.0)
    range_factor_per_game = Column(Float, default=0.0)
    range_factor_per_nine = Column(Float, default=0.0)
    outfield_assists = Column(Integer, default=0)
    passed_balls = Column(Integer, default=0)
    wild_pitches = Column(Integer, default=0)
    stolen_bases_allowed = Column(Integer, default=0)
    caught_stealing = Column(Integer, default=0)
    stolen_base_percentage = Column(Float, default=0.0)
    catchers_interference = Column(Integer, default=0)
    pickoffs = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships with proper type annotations
    team: Mapped["TeamModel"] = relationship("TeamModel", back_populates="fielding_stats")

    # Constraints and indices
    __table_args__ = (
        UniqueConstraint("team_id", "season", name="uq_team_season_fielding"),
        Index("idx_fielding_stats_season", "season"),
    )


class CatchingStatsModel(Base):
    """SQLAlchemy model for team catching statistics."""

    __tablename__ = "catching_stats"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(Integer, nullable=False)

    # Basic game stats
    games_played = Column(Integer, default=0)
    games_pitched = Column(Integer, default=0)

    # Offensive stats (catchers can bat)
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

    # Batting averages and percentages
    batting_average = Column(Float, default=0.0)
    on_base_percentage = Column(Float, default=0.0)
    slugging_percentage = Column(Float, default=0.0)
    ops = Column(Float, default=0.0)

    # Catching-specific defensive stats
    passed_balls = Column(Integer, default=0)
    wild_pitches = Column(Integer, default=0)
    stolen_bases_allowed = Column(Integer, default=0)
    caught_stealing = Column(Integer, default=0)
    stolen_base_percentage = Column(Float, default=0.0)
    pickoffs = Column(Integer, default=0)
    pickoff_attempts = Column(Integer, default=0)
    catchers_interference = Column(Integer, default=0)

    # Pitching stats (catchers may occasionally pitch)
    earned_runs = Column(Integer, default=0)
    batters_faced = Column(Integer, default=0)
    hit_batsmen = Column(Integer, default=0)
    strikeout_walk_ratio = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    team: Mapped["TeamModel"] = relationship("TeamModel", back_populates="catching_stats")

    # Constraints and indices
    __table_args__ = (
        UniqueConstraint("team_id", "season", name="uq_team_season_catching"),
        Index("idx_catching_stats_season", "season"),
    )


class PredictionModel(Base):
    """SQLAlchemy model for predictions."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)

    # Prediction type
    prediction_type = Column(String(50), nullable=False)  # winner, total_runs, player_performance

    # Probabilities
    home_win_probability = Column(Float, nullable=True)
    away_win_probability = Column(Float, nullable=True)
    over_under_runs = Column(Float, nullable=True)
    total_runs_prediction = Column(Float, nullable=True)

    # Detailed predictions
    detailed_predictions = Column(JSON, nullable=True)  # hits, strikeouts, etc.

    # Model metadata
    model_version = Column(String(20), nullable=False)
    confidence_score = Column(Float, nullable=True)
    feature_importance = Column(JSON, nullable=True)

    # Actual results (for model evaluation)
    actual_result = Column(JSON, nullable=True)
    prediction_accuracy = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    game: Mapped["GameModel"] = relationship("GameModel", back_populates="predictions")

    # Indices
    __table_args__ = (
        Index("idx_prediction_game_type", "game_id", "prediction_type"),
        Index("idx_prediction_created", "created_at"),
        Index("idx_prediction_model", "model_version", "created_at"),
    )


class ModelPerformanceModel(Base):
    """SQLAlchemy model for ML model performance metrics."""

    __tablename__ = "model_performance"

    id = Column(Integer, primary_key=True, index=True)
    model_version = Column(String(20), nullable=False)
    evaluation_date = Column(DateTime(timezone=True), nullable=False)

    # Performance metrics
    accuracy = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)

    # MLB-specific metrics
    winner_prediction_accuracy = Column(Float, nullable=True)
    runs_prediction_mae = Column(Float, nullable=True)  # Mean Absolute Error

    # Metadata
    games_evaluated = Column(Integer, nullable=False)
    training_data_size = Column(Integer, nullable=False)
    feature_count = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Indices
    __table_args__ = (Index("idx_model_perf_version_date", "model_version", "evaluation_date"),)
