"""Data models for the Role Registry module."""

from dataclasses import dataclass


@dataclass
class Script:
    """A named collection of roles that defines a playable game configuration."""

    name: str
    description: str
    roles: dict[str, list[str]]  # role_type -> list of role names
    distribution: dict[int, dict[str, int]]  # player_count -> {role_type: count}
    night_order: dict[str, list[str]]  # "first_night" / "other_nights" -> ordered role names
