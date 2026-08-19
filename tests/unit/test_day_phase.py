"""Unit tests for Day Phase, Nomination, and Voting."""

import pytest

from game_engine.engine import GameEngine
from game_engine.exceptions import (
    DeadPlayerActionError,
    InvalidPhaseError,
    InvalidTargetError,
    NominationLimitError,
)
from models.game import GamePhase, PlayerStatus, RoleType


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

    def test_begin_day_phase_resets_nominators_today(self, engine: GameEngine):
        """Test that begin_day_phase resets nominators_today to empty."""
        session = _create_day_session(engine)
        assert session.grimoire.nominators_today == []

    def test_begin_day_phase_resets_nominees_today(self, engine: GameEngine):
        """Test that begin_day_phase resets nominees_today to empty."""
        session = _create_day_session(engine)
        assert session.grimoire.nominees_today == []

    def test_begin_day_phase_resets_about_to_die(self, engine: GameEngine):
        """Test that begin_day_phase resets about_to_die tracking."""
        session = _create_day_session(engine)
        assert session.grimoire.about_to_die_player_id is None
        assert session.grimoire.about_to_die_votes == 0


class TestDayDiscussionMessages:
    """Tests for message sending during day discussion."""

    def test_alive_player_can_send_message_during_day(self, engine: GameEngine):
        """Test that an alive player can send a message during day phase."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        alive_player = players[0]

        message = engine.send_message(session, alive_player.id, "I am the Washerwoman!")

        assert message.sender_id == alive_player.id
        assert message.content == "I am the Washerwoman!"
        assert message in session.grimoire.messages

    def test_dead_player_can_send_message_during_day(self, engine: GameEngine):
        """Test that a dead player can send a message during day phase."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        dead_player = players[1]
        dead_player.status = PlayerStatus.DEAD

        message = engine.send_message(session, dead_player.id, "I was the Chef, trust me.")

        assert message.sender_id == dead_player.id
        assert message.content == "I was the Chef, trust me."
        assert message in session.grimoire.messages

    def test_send_message_rejected_during_night_phase(self, engine: GameEngine):
        """Test that sending a message is rejected during NIGHT phase."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)
        players = session.grimoire.players

        with pytest.raises(InvalidPhaseError):
            engine.send_message(session, players[0].id, "Hello")

    def test_send_message_rejected_during_setup_phase(self, engine: GameEngine):
        """Test that sending a message is rejected during SETUP phase."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        players = session.grimoire.players

        with pytest.raises(InvalidPhaseError):
            engine.send_message(session, players[0].id, "Hello")


class TestNominateSuccess:
    """Tests for successful nominations."""

    def test_nominate_succeeds_when_both_alive(self, engine: GameEngine):
        """Test nominate succeeds when nominator and target are alive."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nominator = players[0]
        target = players[1]

        nomination = engine.nominate(session, nominator.id, target.id)

        assert nomination is not None
        assert nomination.nominator_id == nominator.id
        assert nomination.target_id == target.id

    def test_nominate_tracks_nominator(self, engine: GameEngine):
        """Test that nominating adds nominator to nominators_today."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nominator = players[0]
        target = players[1]

        engine.nominate(session, nominator.id, target.id)

        assert nominator.id in session.grimoire.nominators_today

    def test_nominate_tracks_nominee(self, engine: GameEngine):
        """Test that nominating adds target to nominees_today."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nominator = players[0]
        target = players[1]

        engine.nominate(session, nominator.id, target.id)

        assert target.id in session.grimoire.nominees_today


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


class TestNominateRejectsLimitViolations:
    """Tests for nomination per-day limit enforcement."""

    def test_nominate_rejects_when_nominator_already_nominated(self, engine: GameEngine):
        """Test that nominating twice raises NominationLimitError."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        # First nomination succeeds
        engine.nominate(session, players[0].id, players[1].id)

        # Second nomination from same nominator should fail
        with pytest.raises(NominationLimitError):
            engine.nominate(session, players[0].id, players[2].id)

    def test_nominate_rejects_when_target_already_nominated(self, engine: GameEngine):
        """Test that nominating an already-nominated target raises NominationLimitError."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        # First nomination targeting players[1] succeeds
        engine.nominate(session, players[0].id, players[1].id)

        # Second nomination targeting players[1] from a different nominator should fail
        with pytest.raises(NominationLimitError):
            engine.nominate(session, players[2].id, players[1].id)

    def test_multiple_nominations_from_different_nominators_allowed(self, engine: GameEngine):
        """Test that different nominators can each nominate different targets."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        # Two different nominators, two different targets
        nom1 = engine.nominate(session, players[0].id, players[1].id)
        nom2 = engine.nominate(session, players[2].id, players[3].id)

        assert nom1 is not None
        assert nom2 is not None
        assert len(session.grimoire.nominations_today) == 2


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

    def test_cast_vote_dead_player_with_token_can_vote(self, engine: GameEngine):
        """Test that a dead player with a vote token can vote."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        # Kill a player and give them a token
        dead_player = players[2]
        dead_player.status = PlayerStatus.DEAD
        dead_player.has_vote_token = True

        nomination = engine.nominate(session, players[0].id, players[1].id)
        engine.cast_vote(session, dead_player.id, nomination.id, True)

        assert dead_player.id in nomination.votes_for

    def test_cast_vote_dead_player_token_is_spent(self, engine: GameEngine):
        """Test that dead player's token is spent after voting."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        dead_player = players[2]
        dead_player.status = PlayerStatus.DEAD
        dead_player.has_vote_token = True

        nomination = engine.nominate(session, players[0].id, players[1].id)
        engine.cast_vote(session, dead_player.id, nomination.id, True)

        assert dead_player.has_vote_token is False

    def test_cast_vote_dead_player_without_token_rejected(self, engine: GameEngine):
        """Test that a dead player without a token is rejected."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        dead_player = players[2]
        dead_player.status = PlayerStatus.DEAD
        dead_player.has_vote_token = False

        nomination = engine.nominate(session, players[0].id, players[1].id)

        with pytest.raises(DeadPlayerActionError):
            engine.cast_vote(session, dead_player.id, nomination.id, True)

    def test_cast_vote_dead_player_voting_against_spends_token(self, engine: GameEngine):
        """Test that dead player voting False also spends their token."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        dead_player = players[2]
        dead_player.status = PlayerStatus.DEAD
        dead_player.has_vote_token = True

        nomination = engine.nominate(session, players[0].id, players[1].id)
        engine.cast_vote(session, dead_player.id, nomination.id, False)

        assert dead_player.has_vote_token is False


class TestResolveNomination:
    """Tests for resolve_nomination tallying votes and tracking about_to_die."""

    def test_resolve_updates_about_to_die_when_threshold_met(self, engine: GameEngine):
        """Test that about_to_die is set when votes >= ceil(N/2)."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nomination = engine.nominate(session, players[0].id, players[1].id)

        # 5 living players, threshold = ceil(5/2) = 3 votes
        engine.cast_vote(session, players[2].id, nomination.id, True)
        engine.cast_vote(session, players[3].id, nomination.id, True)
        engine.cast_vote(session, players[4].id, nomination.id, True)

        result = engine.resolve_nomination(session, nomination.id)

        assert result is True
        assert session.grimoire.about_to_die_player_id == players[1].id
        assert session.grimoire.about_to_die_votes == 3

    def test_resolve_does_not_execute_immediately(self, engine: GameEngine):
        """Test that target remains ALIVE after resolve (not executed yet)."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nomination = engine.nominate(session, players[0].id, players[1].id)

        # Give enough votes to meet threshold
        engine.cast_vote(session, players[2].id, nomination.id, True)
        engine.cast_vote(session, players[3].id, nomination.id, True)
        engine.cast_vote(session, players[4].id, nomination.id, True)

        engine.resolve_nomination(session, nomination.id)

        # Target should still be alive — execution happens at end of day
        assert players[1].status == PlayerStatus.ALIVE
        assert session.grimoire.execution_today is False

    def test_resolve_does_not_update_about_to_die_when_below_threshold(self, engine: GameEngine):
        """Test that about_to_die is NOT set when votes < ceil(N/2)."""
        session = _create_day_session(engine)
        players = session.grimoire.players
        nomination = engine.nominate(session, players[0].id, players[1].id)

        # 5 living players, threshold = 3, give only 2
        engine.cast_vote(session, players[2].id, nomination.id, True)
        engine.cast_vote(session, players[3].id, nomination.id, True)

        result = engine.resolve_nomination(session, nomination.id)

        assert result is False
        assert session.grimoire.about_to_die_player_id is None
        assert players[1].status == PlayerStatus.ALIVE

    def test_resolve_clears_about_to_die_on_tie(self, engine: GameEngine):
        """Test that tied qualifying votes clear about_to_die (no execution)."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        # First nomination: 3 votes (meets threshold for 5 players)
        nom1 = engine.nominate(session, players[0].id, players[1].id)
        engine.cast_vote(session, players[2].id, nom1.id, True)
        engine.cast_vote(session, players[3].id, nom1.id, True)
        engine.cast_vote(session, players[4].id, nom1.id, True)
        engine.resolve_nomination(session, nom1.id)
        assert session.grimoire.about_to_die_player_id == players[1].id

        # Second nomination: also 3 votes (tie)
        nom2 = engine.nominate(session, players[2].id, players[3].id)
        engine.cast_vote(session, players[0].id, nom2.id, True)
        engine.cast_vote(session, players[1].id, nom2.id, True)
        engine.cast_vote(session, players[4].id, nom2.id, True)
        engine.resolve_nomination(session, nom2.id)

        # Tie: about_to_die should be cleared
        assert session.grimoire.about_to_die_player_id is None
        assert session.grimoire.about_to_die_votes == 0

    def test_later_nomination_with_more_votes_replaces_about_to_die(self, engine: GameEngine):
        """Test that a later nomination with more votes replaces current about_to_die."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        # First nomination: 3 votes
        nom1 = engine.nominate(session, players[0].id, players[1].id)
        engine.cast_vote(session, players[2].id, nom1.id, True)
        engine.cast_vote(session, players[3].id, nom1.id, True)
        engine.cast_vote(session, players[4].id, nom1.id, True)
        engine.resolve_nomination(session, nom1.id)
        assert session.grimoire.about_to_die_player_id == players[1].id

        # Second nomination: 4 votes (more than 3)
        nom2 = engine.nominate(session, players[2].id, players[3].id)
        engine.cast_vote(session, players[0].id, nom2.id, True)
        engine.cast_vote(session, players[1].id, nom2.id, True)
        engine.cast_vote(session, players[4].id, nom2.id, True)
        # Need one more vote to exceed 3
        # Actually players[3] is the target, let's use another voter
        # All 5 players: 0,1,2,3,4. nom2 target is players[3]
        # Voters: 0, 1, 4 already voted True (3 votes). Need 4 votes.
        # players[3] is the target so they can also vote for themselves
        engine.cast_vote(session, players[3].id, nom2.id, True)
        engine.resolve_nomination(session, nom2.id)

        assert session.grimoire.about_to_die_player_id == players[3].id
        assert session.grimoire.about_to_die_votes == 4


class TestEndDayPhase:
    """Tests for end_day_phase executing the about_to_die player."""

    def test_end_day_phase_executes_about_to_die_player(self, engine: GameEngine):
        """Test that end_day_phase executes the about_to_die player."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        # Set up about_to_die
        nom = engine.nominate(session, players[0].id, players[1].id)
        engine.cast_vote(session, players[2].id, nom.id, True)
        engine.cast_vote(session, players[3].id, nom.id, True)
        engine.cast_vote(session, players[4].id, nom.id, True)
        engine.resolve_nomination(session, nom.id)

        result = engine.end_day_phase(session)

        assert result == players[1].id
        assert players[1].status == PlayerStatus.DEAD
        assert session.grimoire.execution_today is True

    def test_end_day_phase_returns_none_when_no_about_to_die(self, engine: GameEngine):
        """Test that end_day_phase returns None when no about_to_die player."""
        session = _create_day_session(engine)

        result = engine.end_day_phase(session)

        assert result is None
        assert session.grimoire.execution_today is False

    def test_end_day_phase_grants_vote_token(self, engine: GameEngine):
        """Test that executed player receives a vote token."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        nom = engine.nominate(session, players[0].id, players[1].id)
        engine.cast_vote(session, players[2].id, nom.id, True)
        engine.cast_vote(session, players[3].id, nom.id, True)
        engine.cast_vote(session, players[4].id, nom.id, True)
        engine.resolve_nomination(session, nom.id)

        engine.end_day_phase(session)

        assert players[1].has_vote_token is True

    def test_end_day_phase_lifts_poison_if_poisoner_executed(self, engine: GameEngine):
        """Test that poison is lifted if the executed player is the Poisoner."""
        session = _create_day_session(engine)
        players = session.grimoire.players

        # Find or set up the poisoner
        poisoner = None
        for p in players:
            if p.role and p.role.name.lower() == "poisoner":
                poisoner = p
                break

        if poisoner is None:
            # Manually assign Poisoner role to a player for this test
            pytest.skip("No Poisoner in this game setup")

        # Poison someone
        victim = next(p for p in players if p.id != poisoner.id)
        victim.is_poisoned = True

        # Set up about_to_die to be the poisoner
        session.grimoire.about_to_die_player_id = poisoner.id
        session.grimoire.about_to_die_votes = 3

        engine.end_day_phase(session)

        # Poison should be lifted
        assert victim.is_poisoned is False
