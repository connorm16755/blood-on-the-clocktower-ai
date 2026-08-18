"""Unit tests for Day Phase, Nomination, and Voting."""

import pytest

from game_engine.engine import GameEngine
from game_engine.exceptions import (
    DeadPlayerActionError,
    InvalidTargetError,
    NominationError,
)
from models.game import GamePhase, PlayerStatus


@pytest.fixture(scope="module")
def engine() -> GameEngine:
    """Create a GameEngine loaded with the default RoleRegistry."""
    return GameEngine()


def _create_day_session(engine: GameEngine):
    """Helper: create a game and transition through night into day phase."""
    session = engine.create_game("trouble_brewing", 5, "Human")
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)
    return session


class TestBeginDayPhase:
    """Tests for begin_day_phase transitioning game state."""

    def test_begin_day_phase_sets_phase_to_day(self, engine: GameEngine):
        """Test that begin_day_phase transitions the grimoire phase to DAY."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)
        engine.complete_night_phase(session)
        engine.begin_day_phase(session)
        assert session.grimoire.phase == GamePhase.DAY


class TestNominateSuccess:
    """Tests for successful nominations."""

    def test_nominate_succeeds_when_both_alive_no_execution(self, engine: GameEngine):
        """Test nominate succeeds when nominator and target are alive and no execution yet."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nominator = players[0]
        target = players[1]

        nomination = engine.nominate(session, nominator.id, target.id)

        assert nomination is not None
        assert nomination.nominator_id == nominator.id
        assert nomination.target_id == target.id


class TestNominateRejectsDeadNominator:
    """Tests for nomination rejection when nominator is dead."""

    def test_nominate_rejects_dead_nominator(self, engine: GameEngine):
        """Test that a dead nominator raises DeadPlayerActionError."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nominator = players[0]
        target = players[1]

        # Kill the nominator
        nominator.status = PlayerStatus.DEAD

        with pytest.raises(DeadPlayerActionError):
            engine.nominate(session, nominator.id, target.id)


class TestNominateRejectsDeadTarget:
    """Tests for nomination rejection when target is dead."""

    def test_nominate_rejects_dead_target(self, engine: GameEngine):
        """Test that a dead target raises InvalidTargetError."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nominator = players[0]
        target = players[1]

        # Kill the target
        target.status = PlayerStatus.DEAD

        with pytest.raises(InvalidTargetError):
            engine.nominate(session, nominator.id, target.id)


class TestNominateRejectsAfterExecution:
    """Tests for nomination rejection when an execution already occurred today."""

    def test_nominate_rejects_when_execution_already_occurred(self, engine: GameEngine):
        """Test that nominating after an execution today raises NominationError."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        # Create a nomination and get enough votes for execution
        nominator = players[0]
        target = players[1]
        nomination = engine.nominate(session, nominator.id, target.id)

        # All 5 players are alive, need > 2.5 = 3 votes for execution
        voters = [p for p in players if p.id != target.id]
        for voter in voters[:3]:
            engine.cast_vote(session, voter.id, nomination.id, True)

        # Resolve => execution occurs
        result = engine.resolve_nomination(session, nomination.id)
        assert result is True
        assert session.grimoire.execution_today is True

        # Now try to nominate again - should raise NominationError
        second_nominator = players[2]
        second_target = players[3]
        with pytest.raises(NominationError):
            engine.nominate(session, second_nominator.id, second_target.id)


class TestCastVote:
    """Tests for cast_vote recording votes correctly."""

    def test_cast_vote_records_for_correctly(self, engine: GameEngine):
        """Test that voting True adds voter to votes_for."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nomination = engine.nominate(session, players[0].id, players[1].id)

        engine.cast_vote(session, players[2].id, nomination.id, True)

        assert players[2].id in nomination.votes_for
        assert players[2].id not in nomination.votes_against

    def test_cast_vote_records_against_correctly(self, engine: GameEngine):
        """Test that voting False adds voter to votes_against."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nomination = engine.nominate(session, players[0].id, players[1].id)

        engine.cast_vote(session, players[2].id, nomination.id, False)

        assert players[2].id in nomination.votes_against
        assert players[2].id not in nomination.votes_for


class TestResolveNomination:
    """Tests for resolve_nomination tallying votes and determining execution."""

    def test_resolve_executes_target_when_votes_exceed_half(self, engine: GameEngine):
        """Test that target is executed when votes_for > N/2 living players."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nomination = engine.nominate(session, players[0].id, players[1].id)

        # 5 living players, need > 2.5 = 3 votes
        engine.cast_vote(session, players[2].id, nomination.id, True)
        engine.cast_vote(session, players[3].id, nomination.id, True)
        engine.cast_vote(session, players[4].id, nomination.id, True)

        result = engine.resolve_nomination(session, nomination.id)

        assert result is True
        assert players[1].status == PlayerStatus.DEAD
        assert session.grimoire.execution_today is True

    def test_resolve_does_not_execute_when_votes_not_majority(self, engine: GameEngine):
        """Test that target is NOT executed when votes_for <= N/2."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nomination = engine.nominate(session, players[0].id, players[1].id)

        # 5 living players, need > 2.5 but only give 2 votes
        engine.cast_vote(session, players[2].id, nomination.id, True)
        engine.cast_vote(session, players[3].id, nomination.id, True)

        result = engine.resolve_nomination(session, nomination.id)

        assert result is False
        assert players[1].status == PlayerStatus.ALIVE
        assert session.grimoire.execution_today is False


class TestAtMostOneExecutionPerDay:
    """Tests that at most one execution can occur per day."""

    def test_second_successful_nomination_rejected_after_execution(self, engine: GameEngine):
        """Test that a second nomination is rejected after an execution already occurred."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        # First nomination succeeds with execution
        nomination1 = engine.nominate(session, players[0].id, players[1].id)
        voters = [p for p in players if p.id != players[1].id]
        for voter in voters[:3]:
            engine.cast_vote(session, voter.id, nomination1.id, True)
        engine.resolve_nomination(session, nomination1.id)

        # Second nomination should be rejected
        with pytest.raises(NominationError):
            engine.nominate(session, players[2].id, players[3].id)
