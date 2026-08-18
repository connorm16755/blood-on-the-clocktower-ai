"""Storyteller module - Automated game master for information distribution."""

from __future__ import annotations

import random
from typing import Optional

from models.actions import NightActionResult
from models.game import (
    GameSession,
    Grimoire,
    Player,
    RoleType,
    Team,
)


def generate_info_for_role(
    session: GameSession, player_id: str
) -> NightActionResult:
    """Produce the first-night information a role receives.

    Looks up the player by player_id in the session's grimoire, determines
    their role, and generates appropriate information. If the player is
    poisoned, potentially false information is provided instead.

    Args:
        session: The current game session.
        player_id: The ID of the player receiving information.

    Returns:
        A NightActionResult with the information string.
    """
    grimoire = session.grimoire
    player = _find_player(grimoire, player_id)

    if player is None or player.role is None:
        return NightActionResult(player_id=player_id, success=False)

    role_name = player.role.name.lower()

    if role_name == "washerwoman":
        info = _generate_washerwoman_info(grimoire, player)
    elif role_name == "librarian":
        info = _generate_librarian_info(grimoire, player)
    elif role_name == "investigator":
        info = _generate_investigator_info(grimoire, player)
    elif role_name == "chef":
        info = _generate_chef_info(grimoire, player)
    elif role_name == "empath":
        info = _generate_empath_info(grimoire, player)
    else:
        # Role does not receive first-night information
        return NightActionResult(player_id=player_id, success=True)

    return NightActionResult(
        player_id=player_id, success=True, information=info
    )


def _find_player(grimoire: Grimoire, player_id: str) -> Optional[Player]:
    """Find a player in the grimoire by their ID."""
    for player in grimoire.players:
        if player.id == player_id:
            return player
    return None


def _get_players_by_role_type(
    grimoire: Grimoire, role_type: RoleType, exclude_id: Optional[str] = None
) -> list[Player]:
    """Get all players with a specific role type, optionally excluding one."""
    return [
        p
        for p in grimoire.players
        if p.role is not None
        and p.role.role_type == role_type
        and p.id != exclude_id
    ]


def _get_all_role_names_by_type(
    grimoire: Grimoire, role_type: RoleType
) -> list[str]:
    """Get all distinct role names of a given type present in the game."""
    names = set()
    for p in grimoire.players:
        if p.role is not None and p.role.role_type == role_type:
            names.add(p.role.name)
    return list(names)


def _generate_washerwoman_info(grimoire: Grimoire, player: Player) -> str:
    """Generate Washerwoman first-night information.

    Truthful: Pick a Townsfolk player (not self), pick one random other player,
    report that one of them is the Townsfolk's role.

    Poisoned: Pick two random players and a random Townsfolk role name.
    """
    if player.is_poisoned:
        return _generate_poisoned_washerwoman_info(grimoire, player)

    # Find all Townsfolk other than self
    townsfolk = _get_players_by_role_type(
        grimoire, RoleType.TOWNSFOLK, exclude_id=player.id
    )

    if not townsfolk:
        # Edge case: no other Townsfolk (shouldn't normally happen)
        return "No Townsfolk information available."

    # Pick a random Townsfolk to reveal
    correct_player = random.choice(townsfolk)
    role_shown = correct_player.role.name

    # Pick a random other player (not self, not the correct player)
    other_candidates = [
        p
        for p in grimoire.players
        if p.id != player.id and p.id != correct_player.id
    ]

    if not other_candidates:
        # Edge case: only two players in game
        return (
            f"{correct_player.name} is the {role_shown}."
        )

    wrong_player = random.choice(other_candidates)

    # Randomly order the two shown players
    shown = [correct_player, wrong_player]
    random.shuffle(shown)

    return (
        f"{shown[0].name} or {shown[1].name} is the {role_shown}."
    )


def _generate_poisoned_washerwoman_info(
    grimoire: Grimoire, player: Player
) -> str:
    """Generate false Washerwoman information for a poisoned player."""
    # Pick two random players (not self)
    candidates = [p for p in grimoire.players if p.id != player.id]

    if len(candidates) < 2:
        # Not enough players for false info
        chosen = candidates[:1] if candidates else []
        if chosen:
            fake_role = _pick_random_role_name(grimoire, RoleType.TOWNSFOLK)
            return f"{chosen[0].name} is the {fake_role}."
        return "No information available."

    shown = random.sample(candidates, 2)
    fake_role = _pick_random_role_name(grimoire, RoleType.TOWNSFOLK)

    return f"{shown[0].name} or {shown[1].name} is the {fake_role}."


def _generate_librarian_info(grimoire: Grimoire, player: Player) -> str:
    """Generate Librarian first-night information.

    Truthful: Pick an Outsider player, pick one random other player,
    report that one of them is the Outsider's role. If no Outsiders,
    report that none are in play.

    Poisoned: Pick two random players and a random Outsider role name,
    or falsely report no Outsiders.
    """
    if player.is_poisoned:
        return _generate_poisoned_librarian_info(grimoire, player)

    # Find all Outsiders
    outsiders = _get_players_by_role_type(grimoire, RoleType.OUTSIDER)

    if not outsiders:
        return "There are no Outsiders in play."

    # Pick a random Outsider to reveal
    correct_player = random.choice(outsiders)
    role_shown = correct_player.role.name

    # Pick a random other player (not self, not the correct player)
    other_candidates = [
        p
        for p in grimoire.players
        if p.id != player.id and p.id != correct_player.id
    ]

    if not other_candidates:
        return f"{correct_player.name} is the {role_shown}."

    wrong_player = random.choice(other_candidates)

    # Randomly order the two shown players
    shown = [correct_player, wrong_player]
    random.shuffle(shown)

    return (
        f"{shown[0].name} or {shown[1].name} is the {role_shown}."
    )


def _generate_poisoned_librarian_info(
    grimoire: Grimoire, player: Player
) -> str:
    """Generate false Librarian information for a poisoned player."""
    # Poisoned Librarian might say no Outsiders when there are, or show wrong info
    if random.random() < 0.3:
        return "There are no Outsiders in play."

    candidates = [p for p in grimoire.players if p.id != player.id]

    if len(candidates) < 2:
        chosen = candidates[:1] if candidates else []
        if chosen:
            fake_role = _pick_random_role_name(grimoire, RoleType.OUTSIDER)
            return f"{chosen[0].name} is the {fake_role}."
        return "There are no Outsiders in play."

    shown = random.sample(candidates, 2)
    fake_role = _pick_random_role_name(grimoire, RoleType.OUTSIDER)

    return f"{shown[0].name} or {shown[1].name} is the {fake_role}."


def _generate_investigator_info(grimoire: Grimoire, player: Player) -> str:
    """Generate Investigator first-night information.

    Truthful: Pick a Minion or Demon player, pick one random other player,
    report that one of them is the evil player's role.

    Poisoned: Pick two random players and a random Minion role name.
    """
    if player.is_poisoned:
        return _generate_poisoned_investigator_info(grimoire, player)

    # Find all Minions and Demons
    minions = _get_players_by_role_type(grimoire, RoleType.MINION)
    demons = _get_players_by_role_type(grimoire, RoleType.DEMON)
    evil_players = minions + demons

    if not evil_players:
        return "No evil player information available."

    # Pick a random evil player to reveal
    correct_player = random.choice(evil_players)
    role_shown = correct_player.role.name

    # Pick a random other player (not self, not the correct player)
    other_candidates = [
        p
        for p in grimoire.players
        if p.id != player.id and p.id != correct_player.id
    ]

    if not other_candidates:
        return f"{correct_player.name} is the {role_shown}."

    wrong_player = random.choice(other_candidates)

    # Randomly order the two shown players
    shown = [correct_player, wrong_player]
    random.shuffle(shown)

    return (
        f"{shown[0].name} or {shown[1].name} is the {role_shown}."
    )


def _generate_poisoned_investigator_info(
    grimoire: Grimoire, player: Player
) -> str:
    """Generate false Investigator information for a poisoned player."""
    candidates = [p for p in grimoire.players if p.id != player.id]

    if len(candidates) < 2:
        chosen = candidates[:1] if candidates else []
        if chosen:
            fake_role = _pick_random_role_name(grimoire, RoleType.MINION)
            return f"{chosen[0].name} is the {fake_role}."
        return "No information available."

    shown = random.sample(candidates, 2)
    fake_role = _pick_random_role_name(grimoire, RoleType.MINION)

    return f"{shown[0].name} or {shown[1].name} is the {fake_role}."


def _generate_chef_info(grimoire: Grimoire, player: Player) -> str:
    """Generate Chef first-night information.

    Truthful: Count pairs of adjacent evil players in seating order (circular).

    Poisoned: Return a random count (0-2).
    """
    if player.is_poisoned:
        fake_count = random.randint(0, 2)
        return (
            f"There are {fake_count} pairs of evil players "
            f"sitting next to each other."
        )

    count = _count_evil_pairs(grimoire)
    return (
        f"There are {count} pairs of evil players "
        f"sitting next to each other."
    )


def _count_evil_pairs(grimoire: Grimoire) -> int:
    """Count adjacent evil player pairs in circular seating order."""
    players = grimoire.players
    n = len(players)
    if n < 2:
        return 0

    count = 0
    for i in range(n):
        current = players[i]
        next_player = players[(i + 1) % n]
        if (
            current.team == Team.EVIL
            and next_player.team == Team.EVIL
        ):
            count += 1

    return count


def _generate_empath_info(grimoire: Grimoire, player: Player) -> str:
    """Generate Empath night information.

    Truthful: Count how many of the two closest alive neighbors are evil.

    Poisoned: Return a random count (0-2).
    """
    if player.is_poisoned:
        fake_count = random.randint(0, 2)
        return f"{fake_count} of your neighbours are evil."

    count = _count_evil_neighbours(grimoire, player)
    return f"{count} of your neighbours are evil."


def _count_evil_neighbours(grimoire: Grimoire, player: Player) -> int:
    """Count evil alive neighbours for a player in circular seating order.

    Neighbours are the closest alive players on either side, skipping dead.
    """
    players = grimoire.players

    # Find the player's index in seating order
    player_idx = None
    for i, p in enumerate(players):
        if p.id == player.id:
            player_idx = i
            break

    if player_idx is None:
        return 0

    evil_count = 0

    # Find closest alive neighbour to the left (decreasing index, wrapping)
    left_neighbour = _find_alive_neighbour(players, player_idx, direction=-1)
    if left_neighbour and left_neighbour.team == Team.EVIL:
        evil_count += 1

    # Find closest alive neighbour to the right (increasing index, wrapping)
    right_neighbour = _find_alive_neighbour(players, player_idx, direction=1)
    if right_neighbour and right_neighbour.team == Team.EVIL:
        evil_count += 1

    return evil_count


def _find_alive_neighbour(
    players: list[Player], start_idx: int, direction: int
) -> Optional[Player]:
    """Find the closest alive player in a given direction from start_idx.

    Args:
        players: The list of players in seating order.
        start_idx: The index of the player we're searching from.
        direction: +1 for right, -1 for left.

    Returns:
        The closest alive Player in that direction, or None if none found.
    """
    n = len(players)
    for step in range(1, n):
        idx = (start_idx + direction * step) % n
        if players[idx].status.value == "alive":
            return players[idx]
    return None


def _pick_random_role_name(
    grimoire: Grimoire, role_type: RoleType
) -> str:
    """Pick a random role name of the given type from players in the game.

    Falls back to a generic name if no roles of that type exist.
    """
    names = _get_all_role_names_by_type(grimoire, role_type)
    if names:
        return random.choice(names)

    # Fallback names if no roles of that type in game
    fallbacks = {
        RoleType.TOWNSFOLK: "Washerwoman",
        RoleType.OUTSIDER: "Butler",
        RoleType.MINION: "Poisoner",
        RoleType.DEMON: "Imp",
    }
    return fallbacks.get(role_type, "Unknown")
