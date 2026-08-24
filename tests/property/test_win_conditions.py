# Feature: blood-on-the-clocktower-ai, Property 10: Good Victory on Demon Execution
# Feature: blood-on-the-clocktower-ai, Property 11: Evil Victory at Two Players
"""Property tests for Win Condition detection.

Tests that:
- When the Demon is executed, the Game Engine declares a Good team victory (Property 10)
- When exactly two players remain alive and one is the Demon, the Game Engine declares
  an Evil team victory (Property 11)
- No win condition is detected when the Demon is alive and more than 2 players remain

**Validates: Requirements 5.1, 5.2**
"""

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from game_engine.engine import GameEngine
from models.game import GamePhase, GameResult, PlayerStatus, RoleType, Team


# --- Property 10: Good Victory on Demon Execution ---


@settings(max_examples=100, deadline=None)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_good_wins_when_demon_executed(player_count: int) -> None:
    """When the Demon is executed via end_day_phase, check_win_condition returns Good victory.

    **Validates: Requirements 5.1**
    """
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    # Find the Demon player
    demon = next(
        p for p in session.grimoire.players
        if p.role and p.role.role_type == RoleType.DEMON
    )
    assert demon.status == PlayerStatus.ALIVE

    # Set the Demon as about_to_die (simulating a successful nomination vote)
    session.grimoire.about_to_die_player_id = demon.id
    session.grimoire.about_to_die_votes = math.ceil(player_count / 2)

    # Execute end of day — this kills the Demon
    executed_id = engine.end_day_phase(session)
    assert executed_id == demon.id
    assert demon.status == PlayerStatus.DEAD

    # Check win condition — Good should win
    result = engine.check_win_condition(session)
    assert result is not None
    assert isinstance(result, GameResult)
    assert result.winning_team == Team.GOOD
    assert result.reason == "demon_executed"
    assert session.grimoire.phase == GamePhase.ENDED
    assert session.result == result

    # Role reveals should contain all players with roles
    for p in session.grimoire.players:
        if p.role is not None:
            assert p.id in result.role_reveals
            assert result.role_reveals[p.id] == p.role.name


# --- Property 11: Evil Victory at Two Players ---


@settings(max_examples=100, deadline=None)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_evil_wins_at_two_players_with_demon_alive(player_count: int) -> None:
    """When exactly 2 players remain alive and one is the Demon, Evil wins.

    **Validates: Requirements 5.2**
    """
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    # Find the Demon player
    demon = next(
        p for p in session.grimoire.players
        if p.role and p.role.role_type == RoleType.DEMON
    )

    # Kill all players except the Demon and one other player
    alive_kept = 0
    for player in session.grimoire.players:
        if player.id == demon.id:
            # Keep Demon alive
            continue
        elif alive_kept == 0:
            # Keep one non-Demon player alive
            alive_kept += 1
            continue
        else:
            # Kill everyone else
            player.status = PlayerStatus.DEAD
            player.has_vote_token = True

    # Verify exactly 2 players are alive
    alive_players = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]
    assert len(alive_players) == 2
    assert demon in alive_players

    # Check win condition — Evil should win
    result = engine.check_win_condition(session)
    assert result is not None
    assert isinstance(result, GameResult)
    assert result.winning_team == Team.EVIL
    assert result.reason == "two_players_remain"
    assert session.grimoire.phase == GamePhase.ENDED
    assert session.result == result

    # Role reveals should contain all players with roles
    for p in session.grimoire.players:
        if p.role is not None:
            assert p.id in result.role_reveals
            assert result.role_reveals[p.id] == p.role.name


# --- Additional: No Win When Demon Alive and 3+ Players Remain ---


@settings(max_examples=100, deadline=None)
@given(
    player_count=st.sampled_from([5, 6, 7]),
    players_to_kill=st.integers(min_value=0, max_value=4),
)
def test_no_win_when_demon_alive_and_more_than_two_remain(
    player_count: int, players_to_kill: int
) -> None:
    """No win condition when Demon is alive and more than 2 players remain alive.

    **Validates: Requirements 5.1, 5.2**
    """
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Transition to day phase
    engine.begin_night_phase(session)
    engine.complete_night_phase(session)
    engine.begin_day_phase(session)

    # Find the Demon player
    demon = next(
        p for p in session.grimoire.players
        if p.role and p.role.role_type == RoleType.DEMON
    )

    # Kill some non-Demon players, but ensure more than 2 remain alive
    non_demon_players = [
        p for p in session.grimoire.players if p.id != demon.id
    ]

    # Calculate how many we can kill while keeping 3+ alive (including Demon)
    # alive_count = player_count - killed_count >= 3
    max_killable = player_count - 3  # must keep at least 3 alive
    actual_kills = min(players_to_kill, max_killable, len(non_demon_players))

    for i in range(actual_kills):
        non_demon_players[i].status = PlayerStatus.DEAD
        non_demon_players[i].has_vote_token = True

    # Verify more than 2 players remain alive
    alive_players = [
        p for p in session.grimoire.players if p.status == PlayerStatus.ALIVE
    ]
    assert len(alive_players) >= 3
    assert demon.status == PlayerStatus.ALIVE

    # Check win condition — should be None (no win)
    result = engine.check_win_condition(session)
    assert result is None
    assert session.grimoire.phase == GamePhase.DAY  # Phase unchanged
    assert session.result is None
