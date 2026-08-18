# Feature: blood-on-the-clocktower-ai, Property 3: Information Isolation
"""Property test: Information Isolation.

For any player in the game, their visible information SHALL contain only their
own role, their own team alignment, information legitimately received through
their ability or evil-team knowledge, and public game events. No player SHALL
have access to another player's private role assignment through the information
system.

**Validates: Requirements 1.5, 2.2, 7.6**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from game_engine.engine import GameEngine
from models.game import Player, RoleType


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_player_only_knows_own_role(player_count: int) -> None:
    """Each player's role attribute is their own — no player holds a reference
    to another player's RoleDefinition."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    players = session.grimoire.players

    # For each player, verify the only role they "possess" is their own
    for player in players:
        assert player.role is not None, f"Player {player.name} has no role assigned"
        # The player's role should belong to them — cross-check that no other
        # player's role object is the same instance (identity check)
        for other in players:
            if other.id == player.id:
                continue
            assert player.role is not other.role, (
                f"Player {player.name} shares a role instance with {other.name}"
            )


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_good_players_have_no_evil_knowledge(player_count: int) -> None:
    """Good team players (Townsfolk/Outsider) have empty evil_knowledge and
    therefore cannot know any other player's private role."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    players = session.grimoire.players

    good_players = [
        p for p in players
        if p.role and p.role.role_type in (RoleType.TOWNSFOLK, RoleType.OUTSIDER)
    ]

    for player in good_players:
        assert player.evil_knowledge == {}, (
            f"Good player {player.name} ({player.role.name}) has non-empty "
            f"evil_knowledge: {player.evil_knowledge}"
        )


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_evil_knowledge_contains_ids_not_roles(player_count: int) -> None:
    """Evil players' evil_knowledge contains only player IDs (strings), never
    role definitions or role names of other team members.
    In games with <7 players, evil_knowledge should be empty."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    players = session.grimoire.players

    evil_players = [
        p for p in players
        if p.role and p.role.role_type in (RoleType.MINION, RoleType.DEMON)
    ]

    for player in evil_players:
        # In <7 player games, evil players get no knowledge
        if player_count < 7:
            assert player.evil_knowledge == {}, (
                f"Evil player {player.name} should have empty evil_knowledge "
                f"in {player_count}-player game"
            )
            continue

        if player.role.role_type == RoleType.MINION:
            # Minions know the demon's ID only
            assert "demon_id" in player.evil_knowledge, (
                f"Minion {player.name} missing 'demon_id' in evil_knowledge"
            )
            demon_id = player.evil_knowledge["demon_id"]
            # Verify it's a string ID, not a RoleDefinition or role name
            assert isinstance(demon_id, str), (
                f"Minion {player.name}'s demon_id is not a string: {type(demon_id)}"
            )
            # Verify it doesn't contain role information
            assert "role" not in player.evil_knowledge, (
                f"Minion {player.name} has 'role' key in evil_knowledge — "
                f"information leak detected"
            )
            assert "role_name" not in player.evil_knowledge, (
                f"Minion {player.name} has 'role_name' key in evil_knowledge — "
                f"information leak detected"
            )

        elif player.role.role_type == RoleType.DEMON:
            # Demons know minion IDs and bluffs
            assert "minion_ids" in player.evil_knowledge, (
                f"Demon {player.name} missing 'minion_ids' in evil_knowledge"
            )
            minion_ids = player.evil_knowledge["minion_ids"]
            assert isinstance(minion_ids, list), (
                f"Demon {player.name}'s minion_ids is not a list: {type(minion_ids)}"
            )
            # Each entry should be a string ID, not a role or role name
            for mid in minion_ids:
                assert isinstance(mid, str), (
                    f"Demon {player.name} has non-string in minion_ids: {type(mid)}"
                )
            # Bluffs are role names (strings) but are not player role reveals
            if "bluffs" in player.evil_knowledge:
                bluffs = player.evil_knowledge["bluffs"]
                assert isinstance(bluffs, list), (
                    f"Demon {player.name}'s bluffs is not a list: {type(bluffs)}"
                )
                for bluff in bluffs:
                    assert isinstance(bluff, str), (
                        f"Demon {player.name} has non-string bluff: {type(bluff)}"
                    )
            # Verify no role information leaked
            assert "role" not in player.evil_knowledge, (
                f"Demon {player.name} has 'role' key in evil_knowledge — "
                f"information leak detected"
            )
            assert "role_names" not in player.evil_knowledge, (
                f"Demon {player.name} has 'role_names' key in evil_knowledge — "
                f"information leak detected"
            )


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_grimoire_not_accessible_from_player(player_count: int) -> None:
    """The Grimoire (which contains all player roles) is not exposed through
    any player-level attribute. Players should have no back-reference to the
    full game state."""
    engine = GameEngine()
    session = engine.create_game("trouble_brewing", player_count, "TestHuman")

    players = session.grimoire.players

    for player in players:
        # Player should have no attribute that references the grimoire or
        # the full list of players with their roles
        assert not hasattr(player, "grimoire"), (
            f"Player {player.name} has a 'grimoire' attribute — "
            f"information isolation violated"
        )
        assert not hasattr(player, "all_players"), (
            f"Player {player.name} has an 'all_players' attribute — "
            f"information isolation violated"
        )
        assert not hasattr(player, "game_state"), (
            f"Player {player.name} has a 'game_state' attribute — "
            f"information isolation violated"
        )
        assert not hasattr(player, "session"), (
            f"Player {player.name} has a 'session' attribute — "
            f"information isolation violated"
        )
