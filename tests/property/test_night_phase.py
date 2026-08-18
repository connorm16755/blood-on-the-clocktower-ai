# Feature: blood-on-the-clocktower-ai, Property 4: Night Order Preservation
# Feature: blood-on-the-clocktower-ai, Property 5: Demon Kill Resolution
# Feature: blood-on-the-clocktower-ai, Property 6: First Night Information Distribution
"""Property tests for Night Phase mechanics.

Tests that:
- Night abilities are processed in script-defined order, skipping dead players (Property 4)
- Demon kill resolves correctly, summary reveals only identity (Property 5)
- Info-gathering roles receive data on first night (Property 6)

**Validates: Requirements 2.1, 2.3, 2.4, 2.6**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from game_engine.engine import GameEngine
from game_engine.storyteller import generate_info_for_role
from models.actions import NightAction
from models.game import PlayerStatus, RoleType


# --- Property 4: Night Order Preservation ---


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_night_order_preservation(player_count: int) -> None:
    """Night abilities are processed in script-defined order, and dead players
    are skipped in subsequent night order calls."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Begin the first night
    engine.begin_night_phase(session)

    # Get the script's defined night order
    script = engine._registry.get_script("trouble_brewing")
    first_night_roles = script.night_order["first_night"]

    # Get the engine's computed night order for first night
    first_night_order = engine.get_night_order(session, is_first_night=True)

    # Build mapping: player_id -> role_name (lowercase)
    id_to_role = {
        p.id: p.role.name.lower()
        for p in session.grimoire.players
        if p.role is not None
    }

    # Verify order matches script definition (same relative sequence)
    role_order_from_engine = [id_to_role[pid] for pid in first_night_order]

    # Filter script order to only include roles that are actually in the game
    roles_in_game = set(id_to_role.values())
    expected_order = [r.lower() for r in first_night_roles if r.lower() in roles_in_game]

    assert role_order_from_engine == expected_order, (
        f"First night order mismatch.\n"
        f"Engine produced: {role_order_from_engine}\n"
        f"Script defines: {expected_order}"
    )

    # Now test other_nights order
    other_nights_roles = script.night_order["other_nights"]
    other_night_order = engine.get_night_order(session, is_first_night=False)
    other_role_order = [id_to_role[pid] for pid in other_night_order]
    expected_other_order = [r.lower() for r in other_nights_roles if r.lower() in roles_in_game]

    assert other_role_order == expected_other_order, (
        f"Other nights order mismatch.\n"
        f"Engine produced: {other_role_order}\n"
        f"Script defines: {expected_other_order}"
    )

    # Kill a player and verify they are skipped in subsequent night order
    # Find a player who acts at night (from first_night_order)
    if first_night_order:
        player_to_kill_id = first_night_order[0]
        player_to_kill = next(
            p for p in session.grimoire.players if p.id == player_to_kill_id
        )
        player_to_kill.status = PlayerStatus.DEAD
        killed_role = id_to_role[player_to_kill_id]

        # Re-check night order — killed player should be skipped
        updated_first_night_order = engine.get_night_order(session, is_first_night=True)
        updated_roles = [id_to_role[pid] for pid in updated_first_night_order]

        assert killed_role not in updated_roles, (
            f"Dead player with role '{killed_role}' should be skipped "
            f"but still appears in night order: {updated_roles}"
        )


# --- Property 5: Demon Kill Resolution ---


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_demon_kill_resolution(player_count: int) -> None:
    """Demon kill target dies after night resolution, and the NightSummary
    reveals only player identities (player_ids), not role or cause."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Begin night phase
    engine.begin_night_phase(session)

    # Find the Demon player
    demon = next(
        p for p in session.grimoire.players
        if p.role and p.role.role_type == RoleType.DEMON
    )

    # Find a non-Demon living target
    target = next(
        p for p in session.grimoire.players
        if p.id != demon.id and p.status == PlayerStatus.ALIVE
    )

    # Demon performs a kill action
    kill_action = NightAction(
        player_id=demon.id,
        action_type="kill",
        target_id=target.id,
    )
    result = engine.resolve_night_action(session, demon.id, kill_action)
    assert result.success is True, "Demon kill action should succeed"

    # Complete the night phase
    summary = engine.complete_night_phase(session)

    # Assert: target is now DEAD
    assert target.status == PlayerStatus.DEAD, (
        f"Target {target.name} should be DEAD after Demon kill, "
        f"but status is {target.status}"
    )

    # Assert: NightSummary.deaths contains the target's player_id
    assert target.id in summary.deaths, (
        f"Target {target.name} (id={target.id}) should appear in "
        f"summary.deaths={summary.deaths}"
    )

    # Assert: NightSummary reveals only player_ids (strings), no role or cause
    # The deaths list should contain only string player_ids
    for death_entry in summary.deaths:
        assert isinstance(death_entry, str), (
            f"NightSummary.deaths should contain only player_id strings, "
            f"got {type(death_entry)}: {death_entry}"
        )

    # Assert: NightSummary has no attributes revealing role or cause
    assert not hasattr(summary, "causes"), (
        "NightSummary should not reveal cause of death"
    )
    assert not hasattr(summary, "roles"), (
        "NightSummary should not reveal roles of dead players"
    )

    # Assert: summary has correct night_number
    assert summary.night_number == session.grimoire.night_number, (
        f"NightSummary night_number={summary.night_number} should match "
        f"grimoire night_number={session.grimoire.night_number}"
    )


# --- Property 6: First Night Information Distribution ---


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_first_night_information_distribution(player_count: int) -> None:
    """Info-gathering roles (Washerwoman, Librarian, Investigator, Chef, Empath)
    receive non-None information on the first night. Non-info roles do not."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    # Begin first night
    engine.begin_night_phase(session)

    info_gathering_roles = {"washerwoman", "librarian", "investigator", "chef", "empath"}

    for player in session.grimoire.players:
        if player.role is None:
            continue

        role_name = player.role.name.lower()
        result = generate_info_for_role(session, player.id)

        if role_name in info_gathering_roles:
            # Info-gathering roles MUST receive information
            assert result.success is True, (
                f"Info role '{player.role.name}' (player {player.name}) "
                f"should have success=True, got success={result.success}"
            )
            assert result.information is not None, (
                f"Info role '{player.role.name}' (player {player.name}) "
                f"should receive non-None information on first night, "
                f"got information=None"
            )
        else:
            # Non-info roles should NOT receive information
            assert result.success is True, (
                f"Non-info role '{player.role.name}' (player {player.name}) "
                f"should still have success=True"
            )
            assert result.information is None, (
                f"Non-info role '{player.role.name}' (player {player.name}) "
                f"should have information=None, "
                f"got information='{result.information}'"
            )
