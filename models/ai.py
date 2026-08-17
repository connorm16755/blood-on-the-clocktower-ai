"""AI agent data models for personality, beliefs, and context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.actions import Message
    from models.game import Player, RoleDefinition


@dataclass
class Personality:
    """Distinct personality traits that influence AI agent behavior."""

    name: str
    traits: list[str]  # e.g., ["cautious", "analytical", "verbose"]
    communication_style: str  # e.g., "formal", "casual", "terse"
    risk_tolerance: float  # 0.0 to 1.0
    aggression: float  # 0.0 to 1.0 (how likely to nominate/accuse)


@dataclass
class BeliefState:
    """An AI agent's internal model of suspicions and knowledge."""

    suspicions: dict[str, float] = field(default_factory=dict)  # player_id -> suspicion level (-1.0 to 1.0)
    known_roles: dict[str, str] = field(default_factory=dict)  # player_id -> known role
    claims: dict[str, list[str]] = field(default_factory=dict)  # player_id -> list of claims
    voting_patterns: dict[str, list[bool]] = field(default_factory=dict)  # player_id -> vote history
    info_confidence: dict[int, float] = field(default_factory=dict)  # night_number -> confidence (0.0 to 1.0)


@dataclass
class Claim:
    """A public claim an AI agent has made."""

    content: str
    turn_made: int
    is_truthful: bool  # Internal tracking, not visible to others


@dataclass
class DiscussionContext:
    """Context provided to an AI agent when generating discussion messages."""

    messages: list[Message]
    living_players: list[Player]
    dead_players: list[Player]
    own_role: RoleDefinition
    own_info: list[str]  # Private information received
    beliefs: BeliefState
    day_number: int
    known_evil_team: list[str] = field(default_factory=list)  # Only populated for evil roles
