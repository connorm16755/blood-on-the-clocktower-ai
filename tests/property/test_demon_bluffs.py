# Feature: blood-on-the-clocktower-ai, Property 22: Demon Bluffs
"""Property test: Demon Bluffs.

For any game setup with 7 or more players, the Demon SHALL receive exactly 3
not-in-play good character names from the Script as Demon_Bluffs. Each bluff
character SHALL be a good-aligned role that exists in the Script but is not
assigned to any player in the game. For games with fewer than 7 players, no
bluffs are distributed.

**Validates: Requirements 1.9**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from game_engine.engine import GameEngine
from models.game import RoleType


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_demon_bluffs(player_count: int) -> None:
    """Demon receives not-in-play good character bluffs only in 7+ player games."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    players = session.grimoire.players

    # Identify the Demon
    demons = [p for p in players if p.role and p.role.role_type == RoleType.DEMON]
    assert len(demons) == 1, f"Expected 1 Demon, got {len(demons)}"
    demon = demons[0]

    # Determine good roles available in the script
    script = engine._registry.get_script("trouble_brewing")
    good_role_names = list(script.roles.get("townsfolk", []))
    good_role_names += list(script.roles.get("outsiders", []))

    # Determine which roles are assigned to players
    assigned_role_names = {p.role.name for p in players if p.role is not None}

    # Not-in-play good roles
    not_in_play_good = [
        name for name in good_role_names if name not in assigned_role_names
    ]

    if player_count >= 7:
        # Demon should have bluffs in evil_knowledge
        assert "bluffs" in demon.evil_knowledge, (
            f"Demon {demon.name} has no 'bluffs' in evil_knowledge "
            f"for {player_count}-player game"
        )

        bluffs = demon.evil_knowledge["bluffs"]

        # Each bluff is a string (role name)
        for bluff in bluffs:
            assert isinstance(bluff, str), (
                f"Bluff {bluff!r} is not a string"
            )

        # Each bluff is a good-aligned role from the script
        for bluff in bluffs:
            assert bluff in good_role_names, (
                f"Bluff '{bluff}' is not a good role in the script. "
                f"Good roles: {good_role_names}"
            )

        # No bluff is assigned to any player (not-in-play)
        for bluff in bluffs:
            assert bluff not in assigned_role_names, (
                f"Bluff '{bluff}' is assigned to a player (in-play). "
                f"Assigned: {assigned_role_names}"
            )

        # All bluffs are unique (no duplicates)
        assert len(bluffs) == len(set(bluffs)), (
            f"Bluffs contain duplicates: {bluffs}"
        )

        # Number of bluffs is min(3, number of not-in-play good roles)
        expected_count = min(3, len(not_in_play_good))
        assert len(bluffs) == expected_count, (
            f"Expected {expected_count} bluffs "
            f"(min(3, {len(not_in_play_good)}) not-in-play good roles), "
            f"got {len(bluffs)}: {bluffs}"
        )
    else:
        # No bluffs for <7 player games
        assert demon.evil_knowledge == {}, (
            f"Demon {demon.name} should have empty evil_knowledge in "
            f"{player_count}-player game, got {demon.evil_knowledge}"
        )
