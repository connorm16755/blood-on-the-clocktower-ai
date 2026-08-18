# Feature: blood-on-the-clocktower-ai, Property 7: Living Players Discussion Access
# Feature: blood-on-the-clocktower-ai, Property 8: Nomination Validity
# Feature: blood-on-the-clocktower-ai, Property 9: Majority Vote Execution
"""Property tests for Day Phase and Voting mechanics.

Tests that:
- Only living players can participate (dead players cannot nominate) (Property 7)
- Nominations are accepted iff nominator alive, target alive, no execution today (Property 8)
- Execution occurs iff votes_for > N/2 (strict majority) (Property 9)

**Validates: Requirements 3.1, 4.1, 4.3, 4.4, 4.5**
"""

import random

from hypothesis import given, settings
from hypothesis import strategies as st

from game_engine.engine import GameEngine
from game_engine.exceptions import (
    DeadPlayerActionError,
    InvalidTargetError,
    NominationError,
)
from models.game import PlayerStatus


def _safe_cast_vote(engine, session, voter_id, nomination_id, vote):
    """Cast a vote, handling Butler restriction gracefully.

    The Butler cannot vote True unless their master has already voted True.
    This helper catches that restriction and casts a False vote instead.
    """
    try:
        engine.cast_vote(session, voter_id, nomination_id, vote)
    except InvalidTargetError:
        # Butler can't vote True without master voting first — vote against
        engine.cast_vote(session, voter_id, nomination_id, False)


def _cast_votes_excluding_butler(engine, session, players, nomination_id, vote):
    """Cast votes for all players, skipping the Butler to avoid restriction issues.

    For tests that need guaranteed unanimous votes, this ensures Butler
    voting restrictions don't interfere.
    """
    for player in players:
        if player.role and player.role.name.lower() == "butler":
            # Butler votes against to avoid master restriction
            engine.cast_vote(session, player.id, nomination_id, False)
        else:
            engine.cast_vote(session, player.id, nomination_id, vote)


# --- Property 7: Living Players Discussion Access ---


@settings(max_examples=100, deadline=None)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_living_players_can_nominate(player_count: int) -> None:
    """Living players CAN successfully nominate other living players,
    demonstrating they have discussion/action access."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    # Get living players
    living_players = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]
    assert len(living_players) >= 2, "Need at least 2 living players"

    # Pick a random nominator and a different target, both living
    nominator = living_players[0]
    target = living_players[1]

    # Living player should be able to nominate successfully
    nomination = engine.nominate(session, nominator.id, target.id)
    assert nomination is not None, (
        f"Living player '{nominator.name}' should be able to nominate "
        f"living player '{target.name}'"
    )
    assert nomination.nominator_id == nominator.id
    assert nomination.target_id == target.id


@settings(max_examples=100, deadline=None)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_dead_players_cannot_nominate(player_count: int) -> None:
    """Dead players CANNOT nominate, enforcing discussion access restriction."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    # Kill a player manually to simulate a death
    living_players = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]
    dead_player = living_players[0]
    dead_player.status = PlayerStatus.DEAD

    # Find a living target
    remaining_living = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]
    assert len(remaining_living) >= 1, "Need at least 1 living target"
    target = remaining_living[0]

    # Dead player should NOT be able to nominate
    try:
        engine.nominate(session, dead_player.id, target.id)
        assert False, (
            f"Dead player '{dead_player.name}' should not be able to nominate, "
            f"but nomination succeeded."
        )
    except DeadPlayerActionError:
        pass  # Expected: dead players cannot nominate


# --- Property 8: Nomination Validity ---


@settings(max_examples=100, deadline=None)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_nomination_validity_success(player_count: int) -> None:
    """Nomination succeeds when nominator alive AND target alive AND no
    execution today."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    living_players = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]

    # Preconditions: nominator alive, target alive, no execution today
    assert not session.grimoire.execution_today
    nominator = living_players[0]
    target = living_players[1]
    assert nominator.status == PlayerStatus.ALIVE
    assert target.status == PlayerStatus.ALIVE

    # Nomination should succeed
    nomination = engine.nominate(session, nominator.id, target.id)
    assert nomination is not None, "Nomination should succeed with valid preconditions"
    assert nomination.nominator_id == nominator.id
    assert nomination.target_id == target.id


@settings(max_examples=100, deadline=None)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_nomination_rejected_dead_nominator(player_count: int) -> None:
    """Nomination raises DeadPlayerActionError when nominator is dead."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    living_players = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]

    # Kill the nominator
    nominator = living_players[0]
    nominator.status = PlayerStatus.DEAD
    target = living_players[1]

    try:
        engine.nominate(session, nominator.id, target.id)
        assert False, "Should raise DeadPlayerActionError for dead nominator"
    except DeadPlayerActionError:
        pass  # Expected


@settings(max_examples=100, deadline=None)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_nomination_rejected_dead_target(player_count: int) -> None:
    """Nomination raises InvalidTargetError when target is dead."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    living_players = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]

    # Kill the target
    nominator = living_players[0]
    target = living_players[1]
    target.status = PlayerStatus.DEAD

    try:
        engine.nominate(session, nominator.id, target.id)
        assert False, "Should raise InvalidTargetError for dead target"
    except InvalidTargetError:
        pass  # Expected


@settings(max_examples=100, deadline=None)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_nomination_rejected_after_execution(player_count: int) -> None:
    """Nomination raises NominationError when an execution has already
    occurred today."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    living_players = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]

    # Create a nomination and force an execution
    nominator = living_players[0]
    target = living_players[1]
    nomination = engine.nominate(session, nominator.id, target.id)

    # Have non-Butler living players vote for the nomination to guarantee majority
    # Use helper that handles Butler restriction
    non_butler_living = [
        p for p in living_players
        if not (p.role and p.role.name.lower() == "butler")
    ]
    for player in non_butler_living:
        engine.cast_vote(session, player.id, nomination.id, True)

    # Resolve the nomination — should execute (non-Butler majority is sufficient)
    executed = engine.resolve_nomination(session, nomination.id)
    assert executed is True, (
        f"Should execute with {len(non_butler_living)} non-Butler votes "
        f"out of {len(living_players)} living players"
    )
    assert session.grimoire.execution_today is True

    # Now try a second nomination — should be rejected
    remaining_living = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]
    if len(remaining_living) >= 2:
        new_nominator = remaining_living[0]
        new_target = remaining_living[1]
        try:
            engine.nominate(session, new_nominator.id, new_target.id)
            assert False, (
                "Should raise NominationError after execution already occurred today"
            )
        except NominationError:
            pass  # Expected


# --- Property 9: Majority Vote Execution ---


@settings(max_examples=100, deadline=None)
@given(
    player_count=st.sampled_from([5, 6, 7]),
    votes_for_count=st.integers(min_value=0, max_value=7),
)
def test_majority_vote_execution(player_count: int, votes_for_count: int) -> None:
    """Execution occurs iff votes_for > living_count / 2 (strict majority).
    Generate random vote distributions and verify execution correctness."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    living_players = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]
    living_count = len(living_players)

    # Clamp votes_for_count to valid range
    votes_for_count = min(votes_for_count, living_count)

    # Separate Butler from other players to handle voting restriction
    butler_player = None
    non_butler_players = []
    for p in living_players:
        if p.role and p.role.name.lower() == "butler":
            butler_player = p
        else:
            non_butler_players.append(p)

    # Create a nomination
    nominator = living_players[0]
    target = living_players[1]
    nomination = engine.nominate(session, nominator.id, target.id)

    # Assign votes to non-Butler players first
    actual_votes_for = 0
    non_butler_count = len(non_butler_players)

    # Determine how many non-Butler "for" votes we need
    non_butler_for = min(votes_for_count, non_butler_count)

    random.shuffle(non_butler_players)
    for i, voter in enumerate(non_butler_players):
        vote = i < non_butler_for
        engine.cast_vote(session, voter.id, nomination.id, vote)
        if vote:
            actual_votes_for += 1

    # Handle Butler vote if present
    if butler_player:
        # Butler can only vote True if master voted True
        # For simplicity, Butler always votes against in this test
        engine.cast_vote(session, butler_player.id, nomination.id, False)

    # Resolve and check
    executed = engine.resolve_nomination(session, nomination.id)

    # Strict majority: votes_for > living_count / 2
    expected_execution = actual_votes_for > living_count / 2

    assert executed == expected_execution, (
        f"With {actual_votes_for} votes for out of {living_count} living players, "
        f"execution should be {expected_execution} but got {executed}. "
        f"Threshold: votes_for > {living_count}/2 = {living_count / 2}"
    )

    # Verify target status matches execution result
    if expected_execution:
        assert target.status == PlayerStatus.DEAD, (
            f"Target should be DEAD after execution with "
            f"{actual_votes_for}/{living_count} votes"
        )
        assert session.grimoire.execution_today is True
    else:
        assert target.status == PlayerStatus.ALIVE, (
            f"Target should remain ALIVE without majority "
            f"({actual_votes_for}/{living_count} votes)"
        )


@settings(max_examples=100, deadline=None)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_at_most_one_execution_per_day(player_count: int) -> None:
    """After one execution, further nominations are rejected, ensuring
    at most one execution per day."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    living_players = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]

    # First nomination: force execution with non-Butler unanimous vote
    nominator = living_players[0]
    target = living_players[1]
    nomination = engine.nominate(session, nominator.id, target.id)

    non_butler_living = [
        p for p in living_players
        if not (p.role and p.role.name.lower() == "butler")
    ]
    for player in non_butler_living:
        engine.cast_vote(session, player.id, nomination.id, True)

    executed = engine.resolve_nomination(session, nomination.id)
    assert executed is True, "First nomination should execute with non-Butler unanimous vote"

    # Second nomination attempt should be rejected
    remaining_living = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]
    if len(remaining_living) >= 2:
        try:
            engine.nominate(session, remaining_living[0].id, remaining_living[1].id)
            assert False, "Should reject nomination after execution today"
        except NominationError:
            pass  # Expected: at most one execution per day
