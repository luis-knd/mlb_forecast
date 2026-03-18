import pytest

from domain.entities.player import Player


class TestPlayerEntity:
    def test_create_initializes_defaults(self):
        # Given
        mlb_id = 123
        first_name = "Jane"
        last_name = "Doe"
        position = "C"

        # When
        player = Player.create(
            mlb_id=mlb_id,
            first_name=first_name,
            last_name=last_name,
            position=position,
        )

        # Then
        assert player.id is None
        assert player.mlb_id == mlb_id
        assert player.first_name == first_name
        assert player.last_name == last_name
        assert player.position == position
        assert player.created_at is not None
        assert player.updated_at is not None

    def test_full_name_returns_expected_value(self):
        # Given
        player = Player(
            id=1,
            mlb_id=321,
            first_name="Max",
            last_name="Power",
            position="SS",
        )

        # When
        result = player.full_name()

        # Then
        assert result == "Max Power"

    @pytest.mark.parametrize("position", ["P", "Pitcher", "p", "pitcher"])
    def test_is_pitcher_handles_variations(self, position):
        # Given
        player = Player(id=2, mlb_id=456, first_name="Alex", last_name="Ace", position=position)

        # When
        result = player.is_pitcher()

        # Then
        assert result is True

    def test_is_batter_returns_complement(self):
        # Given
        player = Player(id=3, mlb_id=789, first_name="Sam", last_name="Slugger", position="RF")

        # When
        result = player.is_batter()

        # Then
        assert result is True
        assert player.is_pitcher() is False
