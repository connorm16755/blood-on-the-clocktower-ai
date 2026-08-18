"""Core game state data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional
import uuid

if TYPE_CHECKING:
    from models.actions import Message, Nomination


class GamePhase(Enum):
    """Phases of a Blood on the Clocktower game session."""

    SETUP = "setup"
    NIGHT = "night"
    DAY = "day"
    ENDED = "ended"


class Team(Enum):
    """The two opposing factions: Good and Evil."""

    GOOD = "good"
    EVIL = "evil"


class RoleType(Enum):
    """Character role categories that determine team alignment and abilities."""

    TOWNSFOLK = "townsfolk"
    OUTSIDER = "outsider"
    MINION = "minion"
    DEMON = "demon"


class PlayerStatus(Enum):
    """Whether a player is alive or dead."""

    ALIVE = "alive"
    DEAD = "dead"


@dataclass
class RoleDefinition:
    """Structured data record describing a character role."""

    name: str
    role_type: RoleType
    team: Team
    ability_description: str
    first_night_order: Optional[int]  # None if no first-night action
    other_nights_order: Optional[int]  # None if no recurring night action
    setup_requirements: dict  # e.g., {"modifies_distribution": false}
    information_provided: str  # Description of info the player receives
    game_rules: list[str]  # Special rules for this role


@dataclass
class Player:
    """A player in the game (human or AI)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    role: Optional[RoleDefinition] = None
    team: Optional[Team] = None
    status: PlayerStatus = PlayerStatus.ALIVE
    is_human: bool = False
    is_poisoned: bool = False
    used_ability: bool = False  # For one-shot abilities like Slayer
    evil_knowledge: dict = field(default_factory=dict)  # Evil team info: {"demon_id": ...} or {"minion_ids": [...]}


@dataclass
class Grimoire:
    """Complete game state visible only to the Storyteller."""

    players: list[Player]
    phase: GamePhase
    day_number: int
    night_number: int
    nominations_today: list[Nomination] = field(default_factory=list)
    execution_today: bool = False
    messages: list[Message] = field(default_factory=list)
    night_deaths: list[str] = field(default_factory=list)  # player_ids


@dataclass
class GameSession:
    """A single game instance with its complete state."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    script_name: str = ""
    grimoire: Grimoire = field(default_factory=lambda: Grimoire([], GamePhase.SETUP, 0, 0))
    result: Optional[GameResult] = None


@dataclass
class GameResult:
    """Outcome of a completed game."""

    winning_team: Team
    reason: str  # "demon_executed" or "two_players_remain"
    role_reveals: dict[str, str]  # player_id -> role_name
