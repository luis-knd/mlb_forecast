from datetime import datetime

from domain.entities.team_stats import TeamStats
from infrastructure.db.models import FieldingStatsModel, HittingStatsModel, PitchingStatsModel, TeamModel
from infrastructure.mappers.team_stats_mapper import TeamStatsMapper


def test_to_entity_maps_correctly():
    """Test mapping from models to TeamStats entity."""
    # Arrange
    team_model = TeamModel(
        id=1,
        mlb_id=100,
        name="Team A",
        abbreviation="TMA",
        city="City A",
        division="Div A",
        league="League A",
    )

    hitting_stats = HittingStatsModel(
        id=1,
        team_id=1,
        season=2023,
        games_played=10,
        runs_scored=50,
        hits=100,
        home_runs=10,
        batting_average=0.250,
        on_base_percentage=0.300,
        slugging_percentage=0.400,
        ops=0.700,
        stolen_bases=5,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        team=team_model,
    )

    pitching_stats = PitchingStatsModel(
        id=2,
        team_id=1,
        season=2023,
        wins=5,
        losses=5,
        runs_allowed=40,
        earned_run_average=3.50,
        whip=1.20,
        strikeouts_per_nine=9.0,
        walks_per_nine=3.0,
        home_runs_allowed=5,
    )

    fielding_stats = FieldingStatsModel(
        id=3,
        team_id=1,
        season=2023,
        fielding_percentage=0.980,
        errors=2,
        double_plays=4,
    )

    # Act
    entity = TeamStatsMapper.to_entity(hitting_stats, pitching_stats, fielding_stats)

    # Assert
    assert isinstance(entity, TeamStats)
    assert entity.id == 1
    assert entity.team_id == 1
    assert entity.season == 2023
    assert entity.runs_scored == 50
    assert entity.runs_allowed == 40
    # verify run differential calculation
    assert entity.run_differential == 10  # 50 - 40
    # verify pythagorean calculation (50^2 / (50^2 + 40^2)) = 2500 / (2500 + 1600) = 2500 / 4100 = 0.6097
    assert 0.60 < entity.pythagorean_expectation < 0.62

    # Verify relationships
    assert entity.team is not None
    assert entity.team.name == "Team A"


def test_to_entity_returns_none_if_hitting_missing():
    """Test that to_entity returns None if base hitting stats are missing."""
    assert TeamStatsMapper.to_entity(None, None, None) is None


def test_update_hitting_model():
    """Test updating hitting model from entity."""
    entity = TeamStats.create(team_id=1, season=2023, runs_scored=10, hits=20)

    model = HittingStatsModel(team_id=1, season=2023)
    updated_model = TeamStatsMapper.update_hitting_model(entity, model)

    assert updated_model.runs_scored == 10
    assert updated_model.hits == 20
    assert updated_model.team_id == 1


def test_update_pitching_model():
    """Test updating pitching model from entity."""
    entity = TeamStats.create(team_id=1, season=2023, wins=10, runs_allowed=5)

    model = PitchingStatsModel(team_id=1, season=2023)
    updated_model = TeamStatsMapper.update_pitching_model(entity, model)

    assert updated_model.wins == 10
    assert updated_model.runs_allowed == 5


def test_update_fielding_model():
    """Test updating fielding model from entity."""
    entity = TeamStats.create(team_id=1, season=2023, errors=3)

    model = FieldingStatsModel(team_id=1, season=2023)
    updated_model = TeamStatsMapper.update_fielding_model(entity, model)

    assert updated_model.errors == 3
