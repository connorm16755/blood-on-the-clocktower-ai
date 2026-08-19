"""Game Engine - Core module for game state and rule enforcement."""

from __future__ import annotations

import math
import random
import time
from typing import Optional

from game_engine.exceptions import (
    DeadPlayerActionError,
    InvalidPhaseError,
    InvalidPlayerCountError,
    InvalidTargetError,
    NominationError,
    NominationLimitError,
)

from models.actions import Message, NightAction, NightActionResult, Nomination, NightSummary
from models.game import (
    GamePhase,
    GameSession,
    Grimoire,
    Player,
    PlayerStatus,
    RoleType,
)
from role_registry.registry import RoleRegistry
from role_registry.models import Script

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
        self._pending_night_kills: list[str] = []

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

        # 6. Distribute evil team knowledge (conditional on player count)
        self._distribute_evil_knowledge(players, player_count, script)

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

    def _distribute_evil_knowledge(
        self, players: list[Player], player_count: int, script: Script
    ) -> None:
        """Distribute evil team knowledge to Minions and Demons.

        In games with 7+ players:
        - Minions learn the Demon's identity.
        - Demons learn all Minion identities and receive 3 Demon Bluffs
          (not-in-play good characters from the script).

        In games with fewer than 7 players:
        - No evil team knowledge is distributed.

        Args:
            players: All players in the game with roles already assigned.
            player_count: Total number of players in the game.
            script: The Script object for looking up available good roles.
        """
        # In smaller games, evil team members don't learn each other's identities
        if player_count < 7:
            return

        # Find evil team members
        demons = [p for p in players if p.role and p.role.role_type == RoleType.DEMON]
        minions = [p for p in players if p.role and p.role.role_type == RoleType.MINION]

        # Minions learn Demon identity
        demon_ids = [d.id for d in demons]
        for minion in minions:
            minion.evil_knowledge = {"demon_id": demon_ids[0] if demon_ids else None}

        # Compute Demon Bluffs: 3 not-in-play good characters from the script
        # Get all good role names from the script (townsfolk + outsiders)
        good_role_names = list(script.roles.get("townsfolk", []))
        good_role_names += list(script.roles.get("outsiders", []))

        # Determine which roles are assigned to players in this game
        assigned_role_names = {
            p.role.name for p in players if p.role is not None
        }

        # Filter to not-in-play good characters
        not_in_play_good = [
            name for name in good_role_names if name not in assigned_role_names
        ]

        # Select 3 random bluffs (or fewer if not enough available)
        bluff_count = min(3, len(not_in_play_good))
        bluffs = random.sample(not_in_play_good, bluff_count)

        # Demon learns Minion identities + bluffs
        minion_ids = [m.id for m in minions]
        for demon in demons:
            demon.evil_knowledge = {"minion_ids": minion_ids, "bluffs": bluffs}

    def begin_night_phase(self, session: GameSession) -> None:
        """Transition the game to night phase and prepare for night actions.

        Transitions the grimoire phase to NIGHT, increments night_number,
        clears previous night deaths, and clears poison from all players.

        Args:
            session: The current game session.

        Raises:
            InvalidPhaseError: If the game is in the ENDED phase.
        """
        grimoire = session.grimoire

        if grimoire.phase == GamePhase.ENDED:
            raise InvalidPhaseError(
                "Cannot begin night phase: game has ended."
            )

        # Transition to night
        grimoire.phase = GamePhase.NIGHT
        grimoire.night_number += 1

        # Clear previous night deaths
        grimoire.night_deaths = []

        # Clear poison from all players (poison resets each night)
        for player in grimoire.players:
            player.is_poisoned = False

        # Clear pending kills from previous night
        self._pending_night_kills = []

    def get_night_order(
        self, session: GameSession, is_first_night: bool
    ) -> list[str]:
        """Return ordered list of player_ids who act this night.

        Gets the script's night_order for first_night or other_nights,
        maps role names to living players, and returns their player_ids
        in the defined order.

        Args:
            session: The current game session.
            is_first_night: True for first night order, False for other nights.

        Returns:
            Ordered list of player_ids for living players who act this night.
        """
        script = self._registry.get_script(session.script_name)

        order_key = "first_night" if is_first_night else "other_nights"
        night_order = script.night_order.get(order_key, [])

        # Build a mapping from role name (lowercase) to living player
        role_to_player: dict[str, Player] = {}
        for player in session.grimoire.players:
            if player.status == PlayerStatus.ALIVE and player.role:
                role_to_player[player.role.name.lower()] = player

        # Map role names in order to player_ids, skipping dead players
        ordered_player_ids: list[str] = []
        for role_name in night_order:
            player = role_to_player.get(role_name.lower())
            if player is not None:
                ordered_player_ids.append(player.id)

        return ordered_player_ids

    def resolve_night_action(
        self, session: GameSession, player_id: str, action: NightAction
    ) -> NightActionResult:
        """Process a single night action and update game state.

        If the acting player is dead, the action is a no-op.
        For "kill" actions (Demon): adds the target to pending deaths.
        For "poison" actions (Poisoner): sets target's is_poisoned flag.
        For "choose_master" actions (Butler): stores the butler's master choice.

        Args:
            session: The current game session.
            player_id: The player performing the action.
            action: The NightAction to resolve.

        Returns:
            NightActionResult indicating success or failure.
        """
        grimoire = session.grimoire

        # Find the acting player
        acting_player = self._find_player(grimoire, player_id)
        if acting_player is None:
            return NightActionResult(player_id=player_id, success=False)

        # Dead players' actions are no-ops
        if acting_player.status == PlayerStatus.DEAD:
            return NightActionResult(player_id=player_id, success=False)

        action_type = action.action_type

        if action_type == "kill":
            # Demon kill: add target to pending deaths (resolved at end of night)
            if action.target_id:
                target = self._find_player(grimoire, action.target_id)
                if target and target.status == PlayerStatus.ALIVE:
                    self._pending_night_kills.append(action.target_id)
            return NightActionResult(player_id=player_id, success=True)

        elif action_type == "poison":
            # Poisoner: set target's is_poisoned flag
            if action.target_id:
                target = self._find_player(grimoire, action.target_id)
                if target and target.status == PlayerStatus.ALIVE:
                    target.is_poisoned = True
            return NightActionResult(player_id=player_id, success=True)

        elif action_type == "choose_master":
            # Butler: store master choice on the grimoire
            if action.target_id:
                grimoire.butler_master_id = action.target_id
            return NightActionResult(player_id=player_id, success=True)

        # Unknown action type - still return success for extensibility
        return NightActionResult(player_id=player_id, success=True)

    def complete_night_phase(self, session: GameSession) -> NightSummary:
        """Finalize all night actions, apply deaths, and produce a NightSummary.

        Applies pending night kills by setting target players' status to DEAD,
        stores the dead player ids in grimoire.night_deaths, and returns
        a NightSummary with the list of deaths and night number.

        Args:
            session: The current game session.

        Returns:
            NightSummary with deaths list and night_number.
        """
        grimoire = session.grimoire
        deaths: list[str] = []

        # Apply pending kills
        for target_id in self._pending_night_kills:
            target = self._find_player(grimoire, target_id)
            if target and target.status == PlayerStatus.ALIVE:
                target.status = PlayerStatus.DEAD
                target.has_vote_token = True
                deaths.append(target_id)

        # Store deaths in grimoire
        grimoire.night_deaths = deaths

        # Clear pending kills
        self._pending_night_kills = []

        return NightSummary(deaths=deaths, night_number=grimoire.night_number)

    def begin_day_phase(self, session: GameSession) -> None:
        """Transition the game to day phase and reset daily state.

        Transitions the grimoire phase to DAY, increments day_number,
        resets nominations_today, nominators_today, nominees_today,
        about_to_die tracking, and sets execution_today to False.

        Args:
            session: The current game session.

        Raises:
            InvalidPhaseError: If the game is in the ENDED phase.
        """
        grimoire = session.grimoire

        if grimoire.phase == GamePhase.ENDED:
            raise InvalidPhaseError(
                "Cannot begin day phase: game has ended."
            )

        # Transition to day
        grimoire.phase = GamePhase.DAY
        grimoire.day_number += 1

        # Reset daily state
        grimoire.nominations_today = []
        grimoire.execution_today = False
        grimoire.nominators_today = []
        grimoire.nominees_today = []
        grimoire.about_to_die_player_id = None
        grimoire.about_to_die_votes = 0

    def send_message(
        self, session: GameSession, player_id: str, content: str
    ) -> Message:
        """Send a message during day phase discussion.

        Both alive and dead players may send messages during the day phase.

        Args:
            session: The current game session.
            player_id: The ID of the player sending the message.
            content: The message content.

        Returns:
            The created Message object.

        Raises:
            InvalidPhaseError: If the game is not in DAY phase.
        """
        grimoire = session.grimoire

        if grimoire.phase != GamePhase.DAY:
            raise InvalidPhaseError(
                "Messages can only be sent during the day phase."
            )

        player = self._find_player(grimoire, player_id)
        sender_name = player.name if player else ""

        message = Message(
            sender_id=player_id,
            sender_name=sender_name,
            content=content,
            timestamp=time.time(),
            phase=f"day_{grimoire.day_number}",
        )
        grimoire.messages.append(message)

        return message

    def nominate(
        self, session: GameSession, nominator_id: str, target_id: str
    ) -> Nomination:
        """Process a nomination for execution.

        Validates that the game is in the DAY phase, the nominator is alive,
        the nominator hasn't already nominated today, the target is alive,
        and the target hasn't already been nominated today.

        Args:
            session: The current game session.
            nominator_id: The ID of the player making the nomination.
            target_id: The ID of the player being nominated.

        Returns:
            The created Nomination object.

        Raises:
            InvalidPhaseError: If the game is not in DAY phase.
            DeadPlayerActionError: If the nominator is dead.
            NominationLimitError: If the nominator already nominated today
                or the target was already nominated today.
            InvalidTargetError: If the target is dead.
        """
        grimoire = session.grimoire

        # Validate phase
        if grimoire.phase != GamePhase.DAY:
            raise InvalidPhaseError(
                "Nominations can only be made during the day phase."
            )

        # Validate nominator is alive
        nominator = self._find_player(grimoire, nominator_id)
        if nominator is None:
            raise DeadPlayerActionError(
                f"Nominator with id '{nominator_id}' not found."
            )
        if nominator.status != PlayerStatus.ALIVE:
            raise DeadPlayerActionError(
                "Dead players cannot nominate."
            )

        # Validate nominator hasn't already nominated today
        if nominator_id in grimoire.nominators_today:
            raise NominationLimitError(
                "This player has already nominated today."
            )

        # Validate target is alive
        target = self._find_player(grimoire, target_id)
        if target is None:
            raise InvalidTargetError(
                f"Target with id '{target_id}' not found."
            )
        if target.status != PlayerStatus.ALIVE:
            raise InvalidTargetError(
                "Cannot nominate a dead player."
            )

        # Validate target hasn't already been nominated today
        if target_id in grimoire.nominees_today:
            raise NominationLimitError(
                "This player has already been nominated today."
            )

        # Track nominator and nominee for per-day limits
        grimoire.nominators_today.append(nominator_id)
        grimoire.nominees_today.append(target_id)

        # Create and register the nomination
        nomination = Nomination(
            nominator_id=nominator_id,
            target_id=target_id,
        )
        grimoire.nominations_today.append(nomination)

        return nomination

    def cast_vote(
        self, session: GameSession, voter_id: str, nomination_id: str, vote: bool
    ) -> None:
        """Record a player's vote on an active nomination.

        Finds the nomination by ID, validates the voter, and enforces:
        - Dead players must have a vote token to vote; their token is spent
          after casting (regardless of True or False).
        - Butler voting restriction: Butler can only vote True if their
          master has already voted True on this nomination.

        Args:
            session: The current game session.
            voter_id: The ID of the player casting the vote.
            nomination_id: The ID of the nomination being voted on.
            vote: True for voting in favor, False for voting against.

        Raises:
            NominationError: If the nomination is not found.
            DeadPlayerActionError: If the voter is dead and has no vote token.
            InvalidTargetError: If the Butler attempts to vote True without
                their master voting True first.
        """
        grimoire = session.grimoire

        # Find the nomination
        nomination = None
        for nom in grimoire.nominations_today:
            if nom.id == nomination_id:
                nomination = nom
                break

        if nomination is None:
            raise NominationError(
                f"Nomination with id '{nomination_id}' not found."
            )

        # Find the voter
        voter = self._find_player(grimoire, voter_id)
        if voter is None:
            raise NominationError(
                f"Voter with id '{voter_id}' not found."
            )

        # Dead player vote token logic
        if voter.status == PlayerStatus.DEAD:
            if not voter.has_vote_token:
                raise DeadPlayerActionError(
                    "No vote token available."
                )
            # Spend the token (regardless of vote direction)
            voter.has_vote_token = False

        # Enforce Butler voting restriction
        if vote and voter.role and voter.role.name.lower() == "butler":
            master_id = grimoire.butler_master_id
            if master_id is None or master_id not in nomination.votes_for:
                raise InvalidTargetError(
                    "The Butler can only vote in favor if their master has also voted in favor."
                )

        # Record the vote
        if vote:
            nomination.votes_for.append(voter_id)
        else:
            nomination.votes_against.append(voter_id)

    def resolve_nomination(
        self, session: GameSession, nomination_id: str
    ) -> bool:
        """Tally votes and update about_to_die tracking.

        Counts votes in favor against the threshold of ceil(alive_count / 2).
        If votes meet threshold and exceed current about_to_die_votes, the
        nominee becomes the new about_to_die player. If tied, about_to_die
        is cleared. Does NOT execute immediately.

        Args:
            session: The current game session.
            nomination_id: The ID of the nomination to resolve.

        Returns:
            True if the votes met the execution threshold, False otherwise.

        Raises:
            NominationError: If the nomination is not found.
        """
        grimoire = session.grimoire

        # Find the nomination
        nomination = None
        for nom in grimoire.nominations_today:
            if nom.id == nomination_id:
                nomination = nom
                break

        if nomination is None:
            raise NominationError(
                f"Nomination with id '{nomination_id}' not found."
            )

        # Count living players
        living_players = [
            p for p in grimoire.players if p.status == PlayerStatus.ALIVE
        ]
        living_count = len(living_players)

        # Threshold: votes >= ceil(living_count / 2)
        votes_for_count = len(nomination.votes_for)
        threshold = math.ceil(living_count / 2)
        meets_threshold = votes_for_count >= threshold

        if meets_threshold:
            nomination.succeeded = True
            if votes_for_count > grimoire.about_to_die_votes:
                # New highest vote count — this nominee becomes about_to_die
                grimoire.about_to_die_player_id = nomination.target_id
                grimoire.about_to_die_votes = votes_for_count
            elif (
                votes_for_count == grimoire.about_to_die_votes
                and grimoire.about_to_die_player_id is not None
            ):
                # Tie with current about_to_die — clear (no execution)
                grimoire.about_to_die_player_id = None
                grimoire.about_to_die_votes = 0

        nomination.resolved = True
        return meets_threshold

    def end_day_phase(self, session: GameSession) -> Optional[str]:
        """Execute the about_to_die player at end of day.

        If about_to_die_player_id is set, executes that player (marks DEAD,
        grants Vote_Token). Returns the executed player_id or None.

        If the executed player is the Poisoner, immediately lifts active poison.

        Args:
            session: The current game session.

        Returns:
            The executed player_id or None if no execution occurred.
        """
        grimoire = session.grimoire

        executed_id = grimoire.about_to_die_player_id
        if executed_id is None:
            return None

        target = self._find_player(grimoire, executed_id)
        if target and target.status == PlayerStatus.ALIVE:
            target.status = PlayerStatus.DEAD
            target.has_vote_token = True
            grimoire.execution_today = True

            # If the executed player is the Poisoner, lift active poison
            if target.role and target.role.name.lower() == "poisoner":
                for player in grimoire.players:
                    player.is_poisoned = False

        return executed_id

    def _find_player(
        self, grimoire: Grimoire, player_id: str
    ) -> Optional[Player]:
        """Find a player in the grimoire by their ID.

        Args:
            grimoire: The game grimoire containing all players.
            player_id: The ID of the player to find.

        Returns:
            The Player if found, None otherwise.
        """
        for player in grimoire.players:
            if player.id == player_id:
                return player
        return None
