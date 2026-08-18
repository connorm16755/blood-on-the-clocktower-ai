# Feature: blood-on-the-clocktower-ai, Property 12: Role Definition Completeness
"""Property test: Role Definition Completeness.

For every loaded role definition, all required fields are present with correct
types: name, role_type, team, ability_description, night action order
(first_night_order and other_nights_order), setup_requirements,
information_provided, and game_rules.

**Validates: Requirements 7.2, 7.3**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from models.game import RoleDefinition, RoleType, Team
from role_registry.registry import RoleRegistry

# All role names available in the Trouble Brewing script
_TROUBLE_BREWING_ROLES = [
    "washerwoman",
    "librarian",
    "investigator",
    "chef",
    "empath",
    "slayer",
    "butler",
    "poisoner",
    "imp",
]


@settings(max_examples=100)
@given(role_name=st.sampled_from(_TROUBLE_BREWING_ROLES))
def test_role_definition_completeness(role_name: str) -> None:
    """Every loaded role definition contains all required fields with correct types."""
    registry = RoleRegistry()
    role = registry.get_role(role_name)

    # Assert: role is a RoleDefinition instance
    assert isinstance(role, RoleDefinition), (
        f"Expected RoleDefinition but got {type(role)} for role '{role_name}'"
    )

    # Assert: name is a non-empty string
    assert isinstance(role.name, str), (
        f"Role '{role_name}' name should be str, got {type(role.name)}"
    )
    assert len(role.name) > 0, (
        f"Role '{role_name}' has an empty name"
    )

    # Assert: role_type is a valid RoleType enum
    assert isinstance(role.role_type, RoleType), (
        f"Role '{role_name}' role_type should be RoleType, got {type(role.role_type)}"
    )

    # Assert: team is a valid Team enum
    assert isinstance(role.team, Team), (
        f"Role '{role_name}' team should be Team, got {type(role.team)}"
    )

    # Assert: ability_description is a non-empty string
    assert isinstance(role.ability_description, str), (
        f"Role '{role_name}' ability_description should be str, "
        f"got {type(role.ability_description)}"
    )
    assert len(role.ability_description) > 0, (
        f"Role '{role_name}' has an empty ability_description"
    )

    # Assert: night action order fields exist (can be None for roles without
    # night actions, but must be int or None)
    assert role.first_night_order is None or isinstance(role.first_night_order, int), (
        f"Role '{role_name}' first_night_order should be Optional[int], "
        f"got {type(role.first_night_order)}"
    )
    assert role.other_nights_order is None or isinstance(role.other_nights_order, int), (
        f"Role '{role_name}' other_nights_order should be Optional[int], "
        f"got {type(role.other_nights_order)}"
    )

    # Assert: setup_requirements is a dict
    assert isinstance(role.setup_requirements, dict), (
        f"Role '{role_name}' setup_requirements should be dict, "
        f"got {type(role.setup_requirements)}"
    )

    # Assert: information_provided is a non-empty string
    assert isinstance(role.information_provided, str), (
        f"Role '{role_name}' information_provided should be str, "
        f"got {type(role.information_provided)}"
    )
    assert len(role.information_provided) > 0, (
        f"Role '{role_name}' has an empty information_provided"
    )

    # Assert: game_rules is a list of strings
    assert isinstance(role.game_rules, list), (
        f"Role '{role_name}' game_rules should be list, got {type(role.game_rules)}"
    )
    for i, rule in enumerate(role.game_rules):
        assert isinstance(rule, str), (
            f"Role '{role_name}' game_rules[{i}] should be str, got {type(rule)}"
        )
