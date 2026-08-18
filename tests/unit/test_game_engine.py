"""Unit tests for the GameEngine module - game creation and role assignment."""

import pytest

from game_engine.engine import GameEngine
from game_engine.exceptions import InvalidPlayerCountError
from models.game import RoleType
from role_registry.exceptions import ScriptNotFoundError


@pytest.fixture(scope="module")
def engine() -> GameEngine:
    """Create a GameEngine loaded with the default RoleRegistry."""
    return GameEngine()


class TestCreateGamePlayerCount:
    """Tests for correct player count in created games."""

    @pytest.mark.parametrize("player_count", [5, 6, 7])
    def test_create_game_produces_correct_player_count(
        self, engine: GameEngine, player_count: int
    ):
        """Test that create_game produces the correct number of players."""
        session = engine.create_game("trouble_brewing", player_count, "Human")
        assert len(session.grimoire.players) == player_count


class TestHumanPlayer:
    """Tests for human player identification."""

    def test_exactly_one_player_is_human(self, engine: GameEngine):
        """Test that exactly one player in the game is marked as human."""
        session = engine.create_game("trouble_brewing", 5, "TestHuman")
        human_players = [p for p in session.grimoire.players if p.is_human]
        assert len(human_players) == 1

    def test_human_player_has_correct_name(self, engine: GameEngine):
        """Test that the human player has the name provided at creation."""
        session = engine.create_game("trouble_brewing", 5, "MyName")
        human = next(p for p in session.grimoire.players if p.is_human)
        assert human.name == "MyName"


class TestRoleAssignment:
    """Tests for unique role assignment."""

    def test_each_player_has_a_unique_role(self, engine: GameEngine):
        """Test that no two players share the same role."""
        session = engine.create_game("trouble_brewing", 7, "Human")
        role_names = [p.role.name for p in session.grimoire.players]
        assert len(role_names) == len(set(role_names))

    def test_all_players_have_roles_assigned(self, engine: GameEngine):
        """Test that every player has a non-None role after game creation."""
        session = engine.create_game("trouble_brewing", 6, "Human")
        for player in session.grimoire.players:
            assert player.role is not None
            assert player.team is not None


class TestRoleDistribution:
    """Tests for role distribution matching the script's table."""

    @pytest.mark.parametrize(
        "player_count,expected_distribution",
        [
            (5, {"townsfolk": 3, "outsiders": 0, "minions": 1, "demons": 1}),
            (6, {"townsfolk": 3, "outsiders": 1, "minions": 1, "demons": 1}),
            (7, {"townsfolk": 5, "outsiders": 0, "minions": 1, "demons": 1}),
        ],
    )
    def test_role_distribution_matches_script_table(
        self, engine: GameEngine, player_count: int, expected_distribution: dict
    ):
        """Test that the role distribution matches the script's distribution table."""
        session = engine.create_game("trouble_brewing", player_count, "Human")
        players = session.grimoire.players

        actual = {
            "townsfolk": len([p for p in players if p.role.role_type == RoleType.TOWNSFOLK]),
            "outsiders": len([p for p in players if p.role.role_type == RoleType.OUTSIDER]),
            "minions": len([p for p in players if p.role.role_type == RoleType.MINION]),
            "demons": len([p for p in players if p.role.role_type == RoleType.DEMON]),
        }
        assert actual == expected_distribution


class TestEvilKnowledge:
    """Tests for evil team knowledge distribution."""

    def test_minion_receives_demon_identity(self, engine: GameEngine):
        """Test that Minion players receive the Demon's identity in evil_knowledge."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        players = session.grimoire.players

        demon = next(p for p in players if p.role.role_type == RoleType.DEMON)
        minions = [p for p in players if p.role.role_type == RoleType.MINION]

        for minion in minions:
            assert "demon_id" in minion.evil_knowledge
            assert minion.evil_knowledge["demon_id"] == demon.id

    def test_demon_receives_all_minion_identities(self, engine: GameEngine):
        """Test that the Demon player receives all Minion identities in evil_knowledge."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        players = session.grimoire.players

        demon = next(p for p in players if p.role.role_type == RoleType.DEMON)
        minions = [p for p in players if p.role.role_type == RoleType.MINION]

        assert "minion_ids" in demon.evil_knowledge
        minion_ids = demon.evil_knowledge["minion_ids"]
        assert len(minion_ids) == len(minions)
        for minion in minions:
            assert minion.id in minion_ids

    def test_townsfolk_receive_no_evil_knowledge(self, engine: GameEngine):
        """Test that Townsfolk players receive no evil team knowledge."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        players = session.grimoire.players

        townsfolk = [p for p in players if p.role.role_type == RoleType.TOWNSFOLK]
        for player in townsfolk:
            assert player.evil_knowledge == {}

    def test_outsider_receives_no_evil_knowledge(self, engine: GameEngine):
        """Test that Outsider players receive no evil team knowledge."""
        # Use 6 players to guarantee an Outsider is present
        session = engine.create_game("trouble_brewing", 6, "Human")
        players = session.grimoire.players

        outsiders = [p for p in players if p.role.role_type == RoleType.OUTSIDER]
        assert len(outsiders) > 0, "Expected at least one outsider for 6-player game"
        for player in outsiders:
            assert player.evil_knowledge == {}


class TestInvalidInputs:
    """Tests for error handling on invalid inputs."""

    @pytest.mark.parametrize("invalid_count", [4, 8])
    def test_invalid_player_count_raises_error(
        self, engine: GameEngine, invalid_count: int
    ):
        """Test that player counts outside 5-7 raise InvalidPlayerCountError."""
        with pytest.raises(InvalidPlayerCountError):
            engine.create_game("trouble_brewing", invalid_count, "Human")

    def test_invalid_script_name_raises_error(self, engine: GameEngine):
        """Test that an unknown script name raises ScriptNotFoundError."""
        with pytest.raises(ScriptNotFoundError):
            engine.create_game("nonexistent_script", 5, "Human")
