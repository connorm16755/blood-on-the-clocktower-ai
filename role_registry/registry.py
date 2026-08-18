"""Role Registry - Loads and provides access to role definitions and scripts."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

import yaml

from models.game import RoleDefinition, RoleType, Team
from role_registry.exceptions import RoleDataError, ScriptNotFoundError
from role_registry.models import Script

# Required fields for a valid role definition YAML file
_REQUIRED_ROLE_FIELDS = [
    "name",
    "role_type",
    "team",
    "ability_description",
    "setup_requirements",
    "information_provided",
    "game_rules",
]


class RoleRegistry:
    """Loads and provides access to role definitions and scripts."""

    def __init__(self, data_dir: Optional[str] = None):
        """Load all role definitions from YAML files in the data directory.

        Args:
            data_dir: Path to the data directory. If None, uses the project root's
                      'data' directory.

        Raises:
            RoleDataError: If any role definition file is malformed or missing
                          required fields.
        """
        if data_dir is None:
            project_root = Path(__file__).resolve().parent.parent
            self._data_dir = project_root / "data"
        else:
            self._data_dir = Path(data_dir)

        self._roles: dict[str, RoleDefinition] = {}
        self._load_all_roles()

    def _load_all_roles(self) -> None:
        """Load all role definition YAML files from the roles directory."""
        roles_dir = self._data_dir / "roles"
        if not roles_dir.exists():
            return

        for script_dir in roles_dir.iterdir():
            if not script_dir.is_dir():
                continue
            for role_file in script_dir.glob("*.yaml"):
                self._load_role_file(role_file)

    def _load_role_file(self, file_path: Path) -> None:
        """Load and validate a single role definition YAML file.

        Args:
            file_path: Path to the YAML file.

        Raises:
            RoleDataError: If the file is malformed or missing required fields.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise RoleDataError(
                f"Failed to parse role file '{file_path}': {e}"
            ) from e

        if not isinstance(data, dict):
            raise RoleDataError(
                f"Role file '{file_path}' does not contain a valid YAML mapping."
            )

        # Validate required fields
        missing_fields = [
            field for field in _REQUIRED_ROLE_FIELDS if field not in data
        ]
        if missing_fields:
            raise RoleDataError(
                f"Role file '{file_path}' is missing required fields: "
                f"{', '.join(missing_fields)}"
            )

        # Parse enum values
        try:
            role_type = RoleType(data["role_type"].lower())
        except (ValueError, AttributeError) as e:
            raise RoleDataError(
                f"Role file '{file_path}' has invalid role_type: '{data.get('role_type')}'"
            ) from e

        try:
            team = Team(data["team"].lower())
        except (ValueError, AttributeError) as e:
            raise RoleDataError(
                f"Role file '{file_path}' has invalid team: '{data.get('team')}'"
            ) from e

        role = RoleDefinition(
            name=data["name"],
            role_type=role_type,
            team=team,
            ability_description=data["ability_description"],
            first_night_order=data.get("first_night_order"),
            other_nights_order=data.get("other_nights_order"),
            setup_requirements=data["setup_requirements"],
            information_provided=data["information_provided"],
            game_rules=data["game_rules"],
        )

        # Store by lowercase name for case-insensitive lookup
        self._roles[role.name.lower()] = role

    def get_role(self, role_name: str) -> RoleDefinition:
        """Retrieve a role definition by name.

        Args:
            role_name: The name of the role (case-insensitive).

        Returns:
            The RoleDefinition for the specified role.

        Raises:
            RoleDataError: If the role is not found.
        """
        key = role_name.lower()
        if key not in self._roles:
            raise RoleDataError(f"Role '{role_name}' not found in registry.")
        return self._roles[key]

    def get_script(self, script_name: str) -> Script:
        """Load and return a Script object by name.

        Args:
            script_name: The name of the script file (without extension),
                         e.g. "trouble_brewing".

        Returns:
            A Script object with all script data.

        Raises:
            ScriptNotFoundError: If the script file is not found.
            RoleDataError: If the script file is malformed.
        """
        scripts_dir = self._data_dir / "scripts"
        script_file = scripts_dir / f"{script_name}.yaml"

        if not script_file.exists():
            raise ScriptNotFoundError(
                f"Script '{script_name}' not found at '{script_file}'."
            )

        try:
            with open(script_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise RoleDataError(
                f"Failed to parse script file '{script_file}': {e}"
            ) from e

        if not isinstance(data, dict):
            raise RoleDataError(
                f"Script file '{script_file}' does not contain a valid YAML mapping."
            )

        # Validate required script fields
        required_script_fields = ["name", "roles", "distribution"]
        missing = [f for f in required_script_fields if f not in data]
        if missing:
            raise RoleDataError(
                f"Script file '{script_file}' is missing required fields: "
                f"{', '.join(missing)}"
            )

        # Parse distribution - YAML loads int keys as ints
        distribution: dict[int, dict[str, int]] = {}
        for player_count, dist in data["distribution"].items():
            distribution[int(player_count)] = {
                str(k): int(v) for k, v in dist.items()
            }

        return Script(
            name=data["name"],
            description=data.get("description", ""),
            roles=data["roles"],
            distribution=distribution,
            night_order=data.get("night_order", {}),
        )

    def get_roles_for_player_count(
        self, script: Script, player_count: int
    ) -> dict[str, int]:
        """Determine the role distribution for a given player count.

        Args:
            script: The Script to use.
            player_count: Number of players in the game.

        Returns:
            A dict mapping role type names to counts,
            e.g. {"townsfolk": 3, "outsiders": 0, "minions": 1, "demons": 1}

        Raises:
            RoleDataError: If the player count is not supported by the script.
        """
        if player_count not in script.distribution:
            supported = sorted(script.distribution.keys())
            raise RoleDataError(
                f"Player count {player_count} is not supported by script "
                f"'{script.name}'. Supported counts: {supported}"
            )
        return script.distribution[player_count]

    def select_roles(
        self, script: Script, distribution: dict[str, int]
    ) -> list[RoleDefinition]:
        """Randomly select specific roles from the script matching the distribution.

        Args:
            script: The Script whose role lists to draw from.
            distribution: A dict mapping role type names to the number of each
                          to select, e.g. {"townsfolk": 3, "outsiders": 0,
                          "minions": 1, "demons": 1}

        Returns:
            A list of RoleDefinition objects matching the distribution.

        Raises:
            RoleDataError: If there aren't enough roles in the script to
                          fulfill the distribution.
        """
        selected: list[RoleDefinition] = []

        for role_type_name, count in distribution.items():
            if count == 0:
                continue

            available_names = script.roles.get(role_type_name, [])
            if len(available_names) < count:
                raise RoleDataError(
                    f"Script '{script.name}' has only {len(available_names)} "
                    f"{role_type_name} roles available, but {count} required."
                )

            chosen_names = random.sample(available_names, count)
            for name in chosen_names:
                selected.append(self.get_role(name))

        return selected
