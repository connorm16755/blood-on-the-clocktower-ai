"""Action and event data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
import uuid

if TYPE_CHECKING:
    from models.ai import BeliefState
    from models.game import Player, RoleDefinition


@dataclass
class NightAction:
    """A night action submitted by a player."""

    player_id: str
    action_type: str  # "kill", "poison", "choose_master", "info_gather"
    target_id: Optional[str] = None


@dataclass
class NightActionResult:
    """Result of processing a night action."""

    player_id: str
    success: bool
    information: Optional[str] = None  # Info received (e.g., Washerwoman result)


@dataclass
class NightSummary:
    """Summary of events after a night phase completes."""

    deaths: list[str]  # player_ids who died
    night_number: int


@dataclass
class Message:
    """A message sent during day discussion."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    sender_name: str = ""
    content: str = ""
    timestamp: float = 0.0
    phase: str = ""  # "day_1", "day_2", etc.


@dataclass
class Nomination:
    """A nomination for execution during the day phase."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nominator_id: str = ""
    target_id: str = ""
    votes_for: list[str] = field(default_factory=list)
    votes_against: list[str] = field(default_factory=list)
    resolved: bool = False
    succeeded: bool = False


@dataclass
class VoteContext:
    """Context provided to a player when deciding how to vote."""

    nomination: Nomination
    discussion_history: list[Message]
    living_players: list[Player]
    own_role: RoleDefinition
    beliefs: BeliefState
