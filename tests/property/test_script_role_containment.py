# Feature: blood-on-the-clocktower-ai, Property 13: Script Role Containment
"""Property test: Script Role Containment.

For any valid script and player count (5-7), every role selected by
select_roles is a member of the script's defined role list.

**Validates: Requirements 7.4**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from models.game import RoleType
from role_registry.registry import RoleRegistry

# Mapping from RoleType enum values back to script dict keys
_ROLE_TYPE_TO_SCRIPT_KEY: dict[RoleType, str] = {
    RoleType.TOWNSFOLK: "townsfolk",
    RoleType.OUTSIDER: "outsiders",
    RoleType.MINION: "minions",
    RoleType.DEMON: "demons",
}


@settings(max_examples=100)
@given(player_count=st.sampled_from([5, 6, 7]))
def test_script_role_containment(player_count: int) -> None:
    """Every role assigned in a game must be a member of the script's role list."""
    registry = RoleRegistry()
    script = registry.get_script("trouble_brewing")

    # Get distribution and select roles
    distribution = registry.get_roles_for_player_count(script, player_count)
    selected_roles = registry.select_roles(script, distribution)

    # Assert: every selected role's name appears in the script's role list
    # for the corresponding role type
    for role in selected_roles:
        script_key = _ROLE_TYPE_TO_SCRIPT_KEY[role.role_type]
        script_role_names = script.roles.get(script_key, [])
        assert role.name in script_role_names, (
            f"Role '{role.name}' (type={role.role_type.value}) is not in "
            f"script's '{script_key}' list: {script_role_names}"
        )
