"""Unit tests for win condition detection in the GameEngine."""

import pytest

from game_engine.engine import GameEngine
from models.game import (
    GamePhase,
    GameResult,
    GameSession,
    Grimoire,
    Player,
    PlayerStatus,
    RoleDefinition,
    RoleType,
    Team,
)


def _make_role(name: str, role_type: RoleType, team: Team) -> RoleDefinition:
    """Create a minimal RoleDefinition for testing."""
    return RoleDefinition(
        name=name,
        role_type=role_type,
        team=team,
        ability_description="",
        first_night_order=None,
        other_nights_order=None,
        setup_requirements={},
        information_provided="",
        game_rules=[],
    )


def _make_session(players: list[Player], phase: GamePhase = GamePhase.DAY) -> GameSession:
    """Create a GameSession with the given players."""
    grimoire = Grimoire(
        players=players,
        phase=phase,
        day_number=1,
        night_number=1,
    )
    return GameSession(script_name="trouble_brewing", grimoire=grimoire)


@pytest.fixture
def engine() -> GameEngine:
    """Create a GameEngine instance."""
    return GameEngine()


class TestGoodVictory:
    """Tests for Good team winning when the Demon is executed."""

    def test_good_wins_when_demon_is_dead(self, engine: GameEngine):
        """Good team wins when the Demon player is dead."""
        demon = Player(name="Demon", status=PlayerStatus.DEAD)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        townsfolk = Player(name="Townsfolk", status=PlayerStatus.ALIVE)
        townsfolk.role = _make_role("Washerwoman", RoleType.TOWNSFOLK, Team.GOOD)
        townsfolk.team = Team.GOOD

        session = _make_session([demon, townsfolk])
        result = engine.check_win_condition(session)

        assert result is not None
        assert result.winning_team == Team.GOOD
        assert result.reason == "demon_executed"

    def test_good_victory_sets_session_result(self, engine: GameEngine):
        """When Good wins, session.result is set."""
        demon = Player(name="Demon", status=PlayerStatus.DEAD)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        townsfolk = Player(name="Townsfolk", status=PlayerStatus.ALIVE)
        townsfolk.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        townsfolk.team = Team.GOOD

        session = _make_session([demon, townsfolk])
        engine.check_win_condition(session)

        assert session.result is not None
        assert session.result.winning_team == Team.GOOD

    def test_good_victory_sets_phase_to_ended(self, engine: GameEngine):
        """When Good wins, game phase transitions to ENDED."""
        demon = Player(name="Demon", status=PlayerStatus.DEAD)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        townsfolk = Player(name="Townsfolk", status=PlayerStatus.ALIVE)
        townsfolk.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        townsfolk.team = Team.GOOD

        session = _make_session([demon, townsfolk])
        engine.check_win_condition(session)

        assert session.grimoire.phase == GamePhase.ENDED

    def test_good_victory_includes_role_reveals(self, engine: GameEngine):
        """Role reveals include all players' roles."""
        demon = Player(name="Demon", status=PlayerStatus.DEAD)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        townsfolk = Player(name="Townsfolk", status=PlayerStatus.ALIVE)
        townsfolk.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        townsfolk.team = Team.GOOD

        session = _make_session([demon, townsfolk])
        result = engine.check_win_condition(session)

        assert result.role_reveals[demon.id] == "Imp"
        assert result.role_reveals[townsfolk.id] == "Chef"


class TestEvilVictory:
    """Tests for Evil team winning when only 2 players remain alive."""

    def test_evil_wins_with_two_alive_including_demon(self, engine: GameEngine):
        """Evil wins when exactly 2 players are alive and one is the Demon."""
        demon = Player(name="Demon", status=PlayerStatus.ALIVE)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        townsfolk = Player(name="Townsfolk", status=PlayerStatus.ALIVE)
        townsfolk.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        townsfolk.team = Team.GOOD

        dead1 = Player(name="Dead1", status=PlayerStatus.DEAD)
        dead1.role = _make_role("Washerwoman", RoleType.TOWNSFOLK, Team.GOOD)
        dead1.team = Team.GOOD

        dead2 = Player(name="Dead2", status=PlayerStatus.DEAD)
        dead2.role = _make_role("Empath", RoleType.TOWNSFOLK, Team.GOOD)
        dead2.team = Team.GOOD

        session = _make_session([demon, townsfolk, dead1, dead2])
        result = engine.check_win_condition(session)

        assert result is not None
        assert result.winning_team == Team.EVIL
        assert result.reason == "two_players_remain"

    def test_evil_victory_sets_session_result(self, engine: GameEngine):
        """When Evil wins, session.result is set."""
        demon = Player(name="Demon", status=PlayerStatus.ALIVE)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        townsfolk = Player(name="Townsfolk", status=PlayerStatus.ALIVE)
        townsfolk.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        townsfolk.team = Team.GOOD

        dead = Player(name="Dead", status=PlayerStatus.DEAD)
        dead.role = _make_role("Empath", RoleType.TOWNSFOLK, Team.GOOD)
        dead.team = Team.GOOD

        session = _make_session([demon, townsfolk, dead])
        engine.check_win_condition(session)

        assert session.result is not None
        assert session.result.winning_team == Team.EVIL

    def test_evil_victory_sets_phase_to_ended(self, engine: GameEngine):
        """When Evil wins, game phase transitions to ENDED."""
        demon = Player(name="Demon", status=PlayerStatus.ALIVE)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        townsfolk = Player(name="Townsfolk", status=PlayerStatus.ALIVE)
        townsfolk.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        townsfolk.team = Team.GOOD

        dead = Player(name="Dead", status=PlayerStatus.DEAD)
        dead.role = _make_role("Empath", RoleType.TOWNSFOLK, Team.GOOD)
        dead.team = Team.GOOD

        session = _make_session([demon, townsfolk, dead])
        engine.check_win_condition(session)

        assert session.grimoire.phase == GamePhase.ENDED

    def test_evil_victory_includes_role_reveals(self, engine: GameEngine):
        """Role reveals include all players' roles on Evil win."""
        demon = Player(name="Demon", status=PlayerStatus.ALIVE)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        townsfolk = Player(name="Townsfolk", status=PlayerStatus.ALIVE)
        townsfolk.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        townsfolk.team = Team.GOOD

        dead = Player(name="Dead", status=PlayerStatus.DEAD)
        dead.role = _make_role("Empath", RoleType.TOWNSFOLK, Team.GOOD)
        dead.team = Team.GOOD

        session = _make_session([demon, townsfolk, dead])
        result = engine.check_win_condition(session)

        assert result.role_reveals[demon.id] == "Imp"
        assert result.role_reveals[townsfolk.id] == "Chef"
        assert result.role_reveals[dead.id] == "Empath"


class TestNoWinCondition:
    """Tests for cases where no win condition is met."""

    def test_no_win_when_demon_alive_and_more_than_two_alive(self, engine: GameEngine):
        """No win condition when Demon is alive and more than 2 players alive."""
        demon = Player(name="Demon", status=PlayerStatus.ALIVE)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        t1 = Player(name="T1", status=PlayerStatus.ALIVE)
        t1.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        t1.team = Team.GOOD

        t2 = Player(name="T2", status=PlayerStatus.ALIVE)
        t2.role = _make_role("Empath", RoleType.TOWNSFOLK, Team.GOOD)
        t2.team = Team.GOOD

        session = _make_session([demon, t1, t2])
        result = engine.check_win_condition(session)

        assert result is None

    def test_no_win_when_two_alive_but_no_demon(self, engine: GameEngine):
        """No evil win when 2 players alive but neither is the Demon."""
        demon = Player(name="Demon", status=PlayerStatus.DEAD)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        # Note: If demon is dead, Good already wins, so this tests
        # priority: Good win is checked first.
        t1 = Player(name="T1", status=PlayerStatus.ALIVE)
        t1.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        t1.team = Team.GOOD

        t2 = Player(name="T2", status=PlayerStatus.ALIVE)
        t2.role = _make_role("Empath", RoleType.TOWNSFOLK, Team.GOOD)
        t2.team = Team.GOOD

        session = _make_session([demon, t1, t2])
        result = engine.check_win_condition(session)

        # Good wins because demon is dead (takes priority)
        assert result is not None
        assert result.winning_team == Team.GOOD

    def test_returns_none_when_no_demon_player_exists(self, engine: GameEngine):
        """Returns None when there is no player with a Demon role."""
        t1 = Player(name="T1", status=PlayerStatus.ALIVE)
        t1.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        t1.team = Team.GOOD

        t2 = Player(name="T2", status=PlayerStatus.ALIVE)
        t2.role = _make_role("Empath", RoleType.TOWNSFOLK, Team.GOOD)
        t2.team = Team.GOOD

        session = _make_session([t1, t2])
        result = engine.check_win_condition(session)

        assert result is None

    def test_no_win_when_demon_dies_at_night_but_starpass_promotes_minion(self, engine: GameEngine):
        """No win when original Imp dies at night via starpass and a Minion is promoted to Demon.

        In the Imp starpass scenario, the Imp kills itself at night, causing a Minion
        to become the new Imp (Demon). Since the promoted player is alive with a Demon role,
        the game should continue (no Good win, no Evil win) when 3+ players remain.
        """
        # Original Imp is dead (killed itself via starpass)
        original_imp = Player(name="OriginalImp", status=PlayerStatus.DEAD)
        original_imp.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        original_imp.team = Team.EVIL

        # Minion promoted to new Imp (now has Demon role)
        promoted_imp = Player(name="PromotedImp", status=PlayerStatus.ALIVE)
        promoted_imp.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        promoted_imp.team = Team.EVIL

        t1 = Player(name="T1", status=PlayerStatus.ALIVE)
        t1.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        t1.team = Team.GOOD

        t2 = Player(name="T2", status=PlayerStatus.ALIVE)
        t2.role = _make_role("Empath", RoleType.TOWNSFOLK, Team.GOOD)
        t2.team = Team.GOOD

        session = _make_session([original_imp, promoted_imp, t1, t2])
        result = engine.check_win_condition(session)

        # No win: there is a living Demon (promoted_imp), so Good hasn't won.
        # 4 players alive (3 alive + 1 dead original), so Evil hasn't won either.
        assert result is None
        assert session.result is None
        assert session.grimoire.phase == GamePhase.DAY

    def test_no_win_session_result_stays_none(self, engine: GameEngine):
        """When no win condition, session.result remains None."""
        demon = Player(name="Demon", status=PlayerStatus.ALIVE)
        demon.role = _make_role("Imp", RoleType.DEMON, Team.EVIL)
        demon.team = Team.EVIL

        t1 = Player(name="T1", status=PlayerStatus.ALIVE)
        t1.role = _make_role("Chef", RoleType.TOWNSFOLK, Team.GOOD)
        t1.team = Team.GOOD

        t2 = Player(name="T2", status=PlayerStatus.ALIVE)
        t2.role = _make_role("Empath", RoleType.TOWNSFOLK, Team.GOOD)
        t2.team = Team.GOOD

        session = _make_session([demon, t1, t2])
        engine.check_win_condition(session)

        assert session.result is None
        assert session.grimoire.phase == GamePhase.DAY
