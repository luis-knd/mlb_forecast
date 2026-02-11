from src.domain.entities.team_stats import TeamStats


def test_pythagorean_expectation_perfect():
    """Test perfect record (no runs allowed)."""
    stats = TeamStats.create(team_id=1, season=2023, runs_scored=10, runs_allowed=0)
    assert stats.pythagorean_expectation == 1.0


def test_pythagorean_expectation_zero_scored():
    """Test zero runs scored."""
    stats = TeamStats.create(team_id=1, season=2023, runs_scored=0, runs_allowed=10)
    assert stats.pythagorean_expectation == 0.0


def test_pythagorean_expectation_both_zero():
    """Test both zero runs."""
    stats = TeamStats.create(team_id=1, season=2023, runs_scored=0, runs_allowed=0)
    assert stats.pythagorean_expectation == 0.0


def test_pythagorean_expectation_normal():
    """Test normal calculation."""
    # 5 runs scored, 5 allowed -> 25 / 50 = 0.5
    stats = TeamStats.create(team_id=1, season=2023, runs_scored=5, runs_allowed=5)
    assert stats.pythagorean_expectation == 0.5

    # 10 scored, 5 allowed -> 100 / 125 = 0.8
    stats = TeamStats.create(team_id=1, season=2023, runs_scored=10, runs_allowed=5)
    assert stats.pythagorean_expectation == 0.8


def test_update_run_differential_recalculates_pythagorean():
    """Test that updating run differential also updates expectation correctly."""
    stats = TeamStats.create(team_id=1, season=2023, runs_scored=5, runs_allowed=5)
    assert stats.pythagorean_expectation == 0.5

    stats.runs_scored = 10
    stats.runs_allowed = 0
    stats.update_run_differential()

    assert stats.pythagorean_expectation == 1.0
