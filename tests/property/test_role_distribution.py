# Feature: blood-on-the-clocktower-ai, Property 1: Role Distribution Correctness
"""Property test: Role Distribution Correctness.

For any valid script and player count (5-7), selected roles match the
distribution table exactly with no duplicates and one role per player.

**Validates: Requirements 1.2, 1.3, 7.4**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from models.game import RoleType
from role_registry.registry import RoleRegistry

# Mapping from distribution key names (plural, as used in YAML) to RoleType enum values
_DIST_KEY_TO_ROLE_TYPE: dict[str, RoleType] = {
    "townsfolk": RoleType.TOWNSFOLK,
    "outsiders": RoleType.OUTSIDER,
    "minions": RoleType.MINION,
    "demons": RoleType.DEMON,
}


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_role_distribution_correctness(player_count: int) -> None:
    """For any valid player count, selected roles match the distribution table
    exactly with no duplicates and one role per player."""
    registry = RoleRegistry()
    script = registry.get_script("trouble_brewing")

    # Get expected distribution for this player count
    distribution = registry.get_roles_for_player_count(script, player_count)

    # Select roles using the distribution
    selected_roles = registry.select_roles(script, distribution)

    # Assert: total roles == player_count (one role per player)
    assert len(selected_roles) == player_count, (
        f"Expected {player_count} roles but got {len(selected_roles)}"
    )

    # Assert: no duplicate role names
    role_names = [role.name for role in selected_roles]
    assert len(role_names) == len(set(role_names)), (
        f"Duplicate roles found: {role_names}"
    )

    # Assert: role type counts match the distribution table exactly
    type_counts: dict[RoleType, int] = {}
    for role in selected_roles:
        type_counts[role.role_type] = type_counts.get(role.role_type, 0) + 1

    for dist_key, expected_count in distribution.items():
        if expected_count == 0:
            continue
        role_type = _DIST_KEY_TO_ROLE_TYPE[dist_key]
        actual_count = type_counts.get(role_type, 0)
        assert actual_count == expected_count, (
            f"For player_count={player_count}, expected {expected_count} "
            f"{dist_key} ({role_type.value}) but got {actual_count}"
        )
