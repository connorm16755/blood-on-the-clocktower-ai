# Feature: blood-on-the-clocktower-ai, Property 2: Evil Team Knowledge Symmetry
"""Property test: Evil Team Knowledge Symmetry.

For any game setup, every Minion player SHALL know the identity of the Demon,
and the Demon player SHALL know the identities of all Minion players.

**Validates: Requirements 1.6, 1.7**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from game_engine.engine import GameEngine
from models.game import RoleType


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_evil_team_knowledge_symmetry(player_count: int) -> None:
    """Every Minion knows the Demon's identity and the Demon knows all Minion
    identities, with exact set matching."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    players = session.grimoire.players

    # Identify evil team members
    demons = [p for p in players if p.role and p.role.role_type == RoleType.DEMON]
    minions = [p for p in players if p.role and p.role.role_type == RoleType.MINION]

    # There should be exactly one Demon
    assert len(demons) == 1, f"Expected 1 Demon, got {len(demons)}"
    demon = demons[0]

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
