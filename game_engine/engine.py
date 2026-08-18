"""Game Engine - Core module for game state and rule enforcement."""

from __future__ import annotations

import random
from typing import Optional

from game_engine.exceptions import InvalidPlayerCountError
from models.game import (
    GamePhase,
    GameSession,
    Grimoire,
    Player,
    RoleType,
    Team,
)
from role_registry.registry import RoleRegistry

# AI agent name pool for generating unique player names
_AI_NAMES = [
    "Alice",
    "Bob",
    "Charlie",
    "Diana",
    "Edward",
    "Fiona",
    "George",
    "Hannah",
    "Ivan",
    "Julia",
    "Karl",
    "Lena",
    "Marcus",
    "Nina",
    "Oscar",
    "Petra",
]

# Valid player count range for the MVP
_MIN_PLAYERS = 5
_MAX_PLAYERS = 7


class GameEngine:
    """Core game engine responsible for managing game state and enforcing rules."""

    def __init__(self, registry: Optional[RoleRegistry] = None):
        """Initialize the game engine.

        Args:
            registry: A RoleRegistry instance. If None, creates a default one.
        """
        self._registry = registry or RoleRegistry()

    def create_game(
        self, script_name: str, player_count: int, human_player_name: str
    ) -> GameSession:
        """Initialize a new game session with role assignment.

        Creates players (1 human + AI agents), selects roles from the script,
        randomly assigns roles, distributes evil team knowledge, and returns
        a fully initialized GameSession.

        Args:
            script_name: Name of the script to use (e.g. "trouble_brewing").
            player_count: Total number of players (5-7 for MVP).
            human_player_name: Display name for the human player.

        Returns:
            A GameSession with all players, roles assigned, and evil knowledge distributed.

        Raises:
            InvalidPlayerCountError: If player_count is not between 5 and 7.
            ScriptNotFoundError: If the script cannot be found.
            RoleDataError: If role selection fails.
        """
        # 1. Validate player count
        if player_count < _MIN_PLAYERS or player_count > _MAX_PLAYERS:
            raise InvalidPlayerCountError(
                f"Player count must be between {_MIN_PLAYERS} and {_MAX_PLAYERS}, "
                f"got {player_count}."
            )

        # 2. Load script and select roles
        script = self._registry.get_script(script_name)
        distribution = self._registry.get_roles_for_player_count(script, player_count)
        roles = self._registry.select_roles(script, distribution)

        # 3. Create Player objects
        players = self._create_players(player_count, human_player_name)

        # 4. Randomly assign roles to players
        random.shuffle(roles)
        for player, role in zip(players, roles):
            player.role = role
            player.team = role.team

        # 5. Initialize the Grimoire
        grimoire = Grimoire(
            players=players,
            phase=GamePhase.SETUP,
            day_number=0,
            night_number=0,
        )

        # 6. Distribute evil team knowledge
        self._distribute_evil_knowledge(players)

        # 7. Create and return the GameSession
        session = GameSession(
            script_name=script_name,
            grimoire=grimoire,
        )

        return session

    def _create_players(
        self, player_count: int, human_player_name: str
    ) -> list[Player]:
        """Create Player objects for the human and AI agents.

        Args:
            player_count: Total number of players.
            human_player_name: Display name for the human player.

        Returns:
            A list of Player objects with the human player first.
        """
        # Create human player
        human = Player(name=human_player_name, is_human=True)

        # Create AI players with unique names
        ai_count = player_count - 1
        ai_names = random.sample(_AI_NAMES, ai_count)
        ai_players = [Player(name=name, is_human=False) for name in ai_names]

        # Combine: human + AI players
        players = [human] + ai_players
        return players

    def _distribute_evil_knowledge(self, players: list[Player]) -> None:
        """Distribute evil team knowledge to Minions and Demons.

        Minions learn the Demon's identity.
        Demons learn all Minion identities.

        Args:
            players: All players in the game with roles already assigned.
        """
        # Find evil team members
        demons = [p for p in players if p.role and p.role.role_type == RoleType.DEMON]
        minions = [p for p in players if p.role and p.role.role_type == RoleType.MINION]

        # Minions learn Demon identity
        demon_ids = [d.id for d in demons]
        for minion in minions:
            minion.evil_knowledge = {"demon_id": demon_ids[0] if demon_ids else None}

        # Demon learns Minion identities
        minion_ids = [m.id for m in minions]
        for demon in demons:
            demon.evil_knowledge = {"minion_ids": minion_ids}
