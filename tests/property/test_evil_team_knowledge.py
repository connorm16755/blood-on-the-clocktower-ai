# Feature: blood-on-the-clocktower-ai, Property 2: Conditional Evil Team Knowledge
"""Property test: Conditional Evil Team Knowledge.

For any game setup with 7 or more players, every Minion player SHALL know the
identity of the Demon, and the Demon player SHALL know the identities of all
Minion players. For any game setup with fewer than 7 players, no evil team
knowledge SHALL be distributed.

**Validates: Requirements 1.6, 1.7, 1.8**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from game_engine.engine import GameEngine
from models.game import RoleType


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_conditional_evil_team_knowledge(player_count: int) -> None:
    """Evil team knowledge is distributed only in 7+ player games.

    In 7+ player games: Minions learn Demon identity, Demon learns Minion IDs.
    In <7 player games: No evil knowledge distributed at all.
    """
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    players = session.grimoire.players

    # Identify evil team members
    demons = [p for p in players if p.role and p.role.role_type == RoleType.DEMON]
    minions = [p for p in players if p.role and p.role.role_type == RoleType.MINION]

    # There should be exactly one Demon
    assert len(demons) == 1, f"Expected 1 Demon, got {len(demons)}"
    demon = demons[0]

    if player_count >= 7:
        # Every Minion knows the Demon's identity
        for minion in minions:
            assert "demon_id" in minion.evil_knowledge, (
                f"Minion {minion.name} has no 'demon_id' in evil_knowledge"
            )
            assert minion.evil_knowledge["demon_id"] == demon.id, (
                f"Minion {minion.name} thinks Demon is "
                f"{minion.evil_knowledge['demon_id']}, but actual Demon is {demon.id}"
            )

        # The Demon knows all Minion identities
        assert "minion_ids" in demon.evil_knowledge, (
            f"Demon {demon.name} has no 'minion_ids' in evil_knowledge"
        )
        expected_minion_ids = set(m.id for m in minions)
        actual_minion_ids = set(demon.evil_knowledge["minion_ids"])
        assert actual_minion_ids == expected_minion_ids, (
            f"Demon knows minion_ids={actual_minion_ids}, "
            f"but actual Minion IDs are {expected_minion_ids}"
        )
    else:
        # No evil team knowledge for <7 player games
        for minion in minions:
            assert minion.evil_knowledge == {}, (
                f"Minion {minion.name} should have empty evil_knowledge in "
                f"{player_count}-player game, got {minion.evil_knowledge}"
            )
        assert demon.evil_knowledge == {}, (
            f"Demon {demon.name} should have empty evil_knowledge in "
            f"{player_count}-player game, got {demon.evil_knowledge}"
        )
