import pytest

from domain.entities.team_stats import TeamStats
from infrastructure.db.models import FieldingStatsModel, HittingStatsModel, PitchingStatsModel


@pytest.mark.asyncio
async def test_save_team_stats_persists_data(team_stats_repo, db_session):
    """
    Test that the save method correctly persists TeamStats to the database.
    This test is expected to FAIL initially because the save method is not implemented.
    """
    # Arrange
    team_stats = TeamStats.create(
        team_id=1,
        season=2023,
        games_played=162,
        wins=90,
        losses=72,
        runs_scored=800,
        runs_allowed=700,
        hits=1400,
        home_runs=200,
        batting_average=0.250,
        earned_run_average=3.50,
        fielding_percentage=0.980,
    )

    # Act
    saved_stats = await team_stats_repo.save(team_stats)

    # Assert
    assert saved_stats is not None

    # Verify persistence by querying the database directly using models
    hitting = db_session.query(HittingStatsModel).filter_by(team_id=1, season=2023).first()
    pitching = db_session.query(PitchingStatsModel).filter_by(team_id=1, season=2023).first()
    fielding = db_session.query(FieldingStatsModel).filter_by(team_id=1, season=2023).first()

    assert hitting is not None, "Hitting stats were not persisted"
    assert hitting.hits == 1400
    assert pitching is not None, "Pitching stats were not persisted"
    assert fielding is not None, "Fielding stats were not persisted"


@pytest.mark.asyncio
async def test_save_team_stats_updates_existing_data(team_stats_repo, db_session):
    """
    Test that the save method correctly updates existing TeamStats in the database.
    """
    # Arrange: Create initial stats
    initial_stats = TeamStats.create(
        team_id=1,
        season=2023,
        games_played=162,
        wins=90,
        losses=72,
        runs_scored=800,
        runs_allowed=700,
        hits=1400,
        home_runs=200,
        batting_average=0.250,
        earned_run_average=3.50,
        fielding_percentage=0.980,
    )
    await team_stats_repo.save(initial_stats)

    # Act: Update stats
    updated_stats = TeamStats.create(
        team_id=1,
        season=2023,
        games_played=162,
        wins=95,  # Changed
        losses=67,  # Changed
        runs_scored=850,  # Changed
        runs_allowed=650,  # Changed
        hits=1450,  # Changed
        home_runs=210,  # Changed
        batting_average=0.260,  # Changed
        earned_run_average=3.20,  # Changed
        fielding_percentage=0.990,  # Changed
    )

    saved_stats = await team_stats_repo.save(updated_stats)

    # Assert
    assert saved_stats is not None

    # Verify persistence of updates
    hitting = db_session.query(HittingStatsModel).filter_by(team_id=1, season=2023).first()
    pitching = db_session.query(PitchingStatsModel).filter_by(team_id=1, season=2023).first()
    fielding = db_session.query(FieldingStatsModel).filter_by(team_id=1, season=2023).first()

    assert hitting.hits == 1450
    assert hitting.runs_scored == 850
    assert pitching.wins == 95
    assert pitching.earned_run_average == 3.20
    assert fielding.fielding_percentage == 0.990

    assert pitching is not None, "Pitching stats were not persisted"
    assert fielding is not None, "Fielding stats were not persisted"


@pytest.mark.asyncio
async def test_get_by_id_returns_correct_entity(team_stats_repo, db_session):
    """
    Test that get_by_id returns a correctly mapped TeamStats entity.
    """
    # Arrange
    team_stats = TeamStats.create(
        team_id=1,
        season=2023,
        games_played=162,
        wins=90,
        runs_scored=800,
        runs_allowed=700,
        hits=1400,
    )
    saved_stats = await team_stats_repo.save(team_stats)
    stats_id = saved_stats.id

    # Act
    retrieved_stats = await team_stats_repo.get_by_id(stats_id)

    # Assert
    assert retrieved_stats is not None
    assert retrieved_stats.id == stats_id
    assert retrieved_stats.team_id == 1
    assert retrieved_stats.season == 2023
    assert retrieved_stats.runs_scored == 800
    assert retrieved_stats.hits == 1400
    # Check if mapper worked for calculated fields
    assert retrieved_stats.run_differential == 100
    assert retrieved_stats.pythagorean_expectation > 0.0
