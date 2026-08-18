"""Unit tests for the RoleRegistry module."""

import os
import tempfile

import pytest

from models.game import RoleDefinition, RoleType, Team
from role_registry.exceptions import RoleDataError, ScriptNotFoundError
from role_registry.registry import RoleRegistry


@pytest.fixture(scope="module")
def registry() -> RoleRegistry:
    """Create a RoleRegistry loaded from the project's default data directory."""
    return RoleRegistry()


class TestGetRole:
    """Tests for RoleRegistry.get_role."""

    TROUBLE_BREWING_ROLES = [
        ("Washerwoman", RoleType.TOWNSFOLK, Team.GOOD),
        ("Librarian", RoleType.TOWNSFOLK, Team.GOOD),
        ("Investigator", RoleType.TOWNSFOLK, Team.GOOD),
        ("Chef", RoleType.TOWNSFOLK, Team.GOOD),
        ("Empath", RoleType.TOWNSFOLK, Team.GOOD),
        ("Slayer", RoleType.TOWNSFOLK, Team.GOOD),
        ("Butler", RoleType.OUTSIDER, Team.GOOD),
        ("Poisoner", RoleType.MINION, Team.EVIL),
        ("Imp", RoleType.DEMON, Team.EVIL),
    ]

    @pytest.mark.parametrize(
        "role_name,expected_type,expected_team", TROUBLE_BREWING_ROLES
    )
    def test_get_role_returns_correct_definition(
        self, registry: RoleRegistry, role_name: str, expected_type: RoleType, expected_team: Team
    ):
        """Test that get_role returns the correct RoleDefinition for each Trouble Brewing role."""
        role = registry.get_role(role_name)
        assert isinstance(role, RoleDefinition)
        assert role.name == role_name
        assert role.role_type == expected_type
        assert role.team == expected_team

    def test_get_role_is_case_insensitive(self, registry: RoleRegistry):
        """Test that get_role lookups are case-insensitive."""
        role_lower = registry.get_role("imp")
        role_upper = registry.get_role("IMP")
        role_mixed = registry.get_role("iMp")
        assert role_lower.name == "Imp"
        assert role_upper.name == "Imp"
        assert role_mixed.name == "Imp"

    def test_get_role_raises_for_unknown_role(self, registry: RoleRegistry):
        """Test that get_role raises RoleDataError for a role name not in the registry."""
        with pytest.raises(RoleDataError, match="not found"):
            registry.get_role("NonExistentRole")


class TestGetScript:
    """Tests for RoleRegistry.get_script."""

    def test_get_script_loads_trouble_brewing(self, registry: RoleRegistry):
        """Test that get_script loads Trouble Brewing with all 9 roles."""
        script = registry.get_script("trouble_brewing")
        assert script.name == "Trouble Brewing"

        # Count all roles across all categories
        all_role_names = []
        for role_list in script.roles.values():
            all_role_names.extend(role_list)
        assert len(all_role_names) == 9

    def test_get_script_has_correct_role_categories(self, registry: RoleRegistry):
        """Test that the script organizes roles into the correct categories."""
        script = registry.get_script("trouble_brewing")
        assert len(script.roles["townsfolk"]) == 6
        assert len(script.roles["outsiders"]) == 1
        assert len(script.roles["minions"]) == 1
        assert len(script.roles["demons"]) == 1

    def test_get_script_raises_for_unknown_script(self, registry: RoleRegistry):
        """Test that get_script raises ScriptNotFoundError for unknown scripts."""
        with pytest.raises(ScriptNotFoundError, match="not found"):
            registry.get_script("nonexistent_script")


class TestGetRolesForPlayerCount:
    """Tests for RoleRegistry.get_roles_for_player_count."""

    @pytest.mark.parametrize(
        "player_count,expected_distribution",
        [
            (5, {"townsfolk": 3, "outsiders": 0, "minions": 1, "demons": 1}),
            (6, {"townsfolk": 3, "outsiders": 1, "minions": 1, "demons": 1}),
            (7, {"townsfolk": 5, "outsiders": 0, "minions": 1, "demons": 1}),
        ],
    )
    def test_returns_correct_distribution(
        self, registry: RoleRegistry, player_count: int, expected_distribution: dict
    ):
        """Test that get_roles_for_player_count returns the correct distribution for 5, 6, and 7 players."""
        script = registry.get_script("trouble_brewing")
        distribution = registry.get_roles_for_player_count(script, player_count)
        assert distribution == expected_distribution

    def test_raises_for_unsupported_player_count(self, registry: RoleRegistry):
        """Test that get_roles_for_player_count raises RoleDataError for unsupported counts."""
        script = registry.get_script("trouble_brewing")
        with pytest.raises(RoleDataError, match="not supported"):
            registry.get_roles_for_player_count(script, 10)


class TestSelectRoles:
    """Tests for RoleRegistry.select_roles."""

    def test_select_roles_returns_correct_count_5_players(self, registry: RoleRegistry):
        """Test that select_roles returns the right number of each role type for 5 players."""
        script = registry.get_script("trouble_brewing")
        distribution = {"townsfolk": 3, "outsiders": 0, "minions": 1, "demons": 1}
        selected = registry.select_roles(script, distribution)

        assert len(selected) == 5
        townsfolk = [r for r in selected if r.role_type == RoleType.TOWNSFOLK]
        outsiders = [r for r in selected if r.role_type == RoleType.OUTSIDER]
        minions = [r for r in selected if r.role_type == RoleType.MINION]
        demons = [r for r in selected if r.role_type == RoleType.DEMON]

        assert len(townsfolk) == 3
        assert len(outsiders) == 0
        assert len(minions) == 1
        assert len(demons) == 1

    def test_select_roles_returns_correct_count_6_players(self, registry: RoleRegistry):
        """Test that select_roles returns the right number of each role type for 6 players."""
        script = registry.get_script("trouble_brewing")
        distribution = {"townsfolk": 3, "outsiders": 1, "minions": 1, "demons": 1}
        selected = registry.select_roles(script, distribution)

        assert len(selected) == 6
        townsfolk = [r for r in selected if r.role_type == RoleType.TOWNSFOLK]
        outsiders = [r for r in selected if r.role_type == RoleType.OUTSIDER]

        assert len(townsfolk) == 3
        assert len(outsiders) == 1

    def test_select_roles_returns_role_definitions(self, registry: RoleRegistry):
        """Test that all selected roles are valid RoleDefinition instances."""
        script = registry.get_script("trouble_brewing")
        distribution = {"townsfolk": 3, "outsiders": 0, "minions": 1, "demons": 1}
        selected = registry.select_roles(script, distribution)

        for role in selected:
            assert isinstance(role, RoleDefinition)
            assert role.name != ""
            assert role.ability_description != ""


class TestMalformedYAML:
    """Tests for handling malformed YAML role files."""

    def test_malformed_yaml_missing_required_fields(self):
        """Test that a YAML file missing required fields raises RoleDataError on load."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create the expected directory structure
            roles_dir = os.path.join(tmp_dir, "roles", "test_script")
            os.makedirs(roles_dir)

            # Write a malformed role file missing required fields
            malformed_role = os.path.join(roles_dir, "bad_role.yaml")
            with open(malformed_role, "w", encoding="utf-8") as f:
                f.write("name: BadRole\n")
                f.write("role_type: townsfolk\n")
                # Missing: team, ability_description, setup_requirements,
                #          information_provided, game_rules

            with pytest.raises(RoleDataError, match="missing required fields"):
                RoleRegistry(data_dir=tmp_dir)

    def test_invalid_yaml_syntax_raises_error(self):
        """Test that a file with invalid YAML syntax raises RoleDataError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            roles_dir = os.path.join(tmp_dir, "roles", "test_script")
            os.makedirs(roles_dir)

            bad_yaml = os.path.join(roles_dir, "broken.yaml")
            with open(bad_yaml, "w", encoding="utf-8") as f:
                f.write("name: [unclosed bracket\n")
                f.write("  invalid: yaml: content:\n")

            with pytest.raises(RoleDataError, match="Failed to parse"):
                RoleRegistry(data_dir=tmp_dir)
