"""Unit tests for the Night Phase execution in the GameEngine."""

import pytest

from game_engine.engine import GameEngine
from game_engine.storyteller import generate_info_for_role
from models.actions import NightAction, NightSummary
from models.game import (
    GamePhase,
    GameSession,
    Grimoire,
    Player,
    PlayerStatus,
    RoleDefinition,
    RoleType,
    Team,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_role(
    name: str,
    role_type: RoleType,
    team: Team,
    first_night_order: int | None = None,
    other_nights_order: int | None = None,
) -> RoleDefinition:
    """Create a minimal RoleDefinition for testing."""
    return RoleDefinition(
        name=name,
        role_type=role_type,
        team=team,
        ability_description="test",
        first_night_order=first_night_order,
        other_nights_order=other_nights_order,
        setup_requirements={},
        information_provided="test",
        game_rules=[],
    )


def _make_player(
    name: str,
    role_name: str,
    role_type: RoleType,
    team: Team,
    status: PlayerStatus = PlayerStatus.ALIVE,
    is_poisoned: bool = False,
) -> Player:
    """Create a Player with a role for testing."""
    p = Player(name=name)
    p.role = _make_role(role_name, role_type, team)
    p.team = team
    p.status = status
    p.is_poisoned = is_poisoned
    return p


def _make_session(
    players: list[Player],
    phase: GamePhase = GamePhase.SETUP,
    night_number: int = 0,
) -> GameSession:
    """Create a GameSession with given players."""
    grimoire = Grimoire(
        players=players,
        phase=phase,
        day_number=0,
        night_number=night_number,
    )
    return GameSession(script_name="trouble_brewing", grimoire=grimoire)


@pytest.fixture(scope="module")
def engine() -> GameEngine:
    """Create a GameEngine with the real RoleRegistry."""
    return GameEngine()


# ---------------------------------------------------------------------------
# TestBeginNightPhase
# ---------------------------------------------------------------------------


class TestBeginNightPhase:
    """Tests for begin_night_phase transitioning game phase to NIGHT."""

    def test_transitions_phase_to_night(self, engine: GameEngine):
        """begin_night_phase should set grimoire.phase to NIGHT."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        # Game starts in SETUP
        assert session.grimoire.phase == GamePhase.SETUP

        engine.begin_night_phase(session)

        assert session.grimoire.phase == GamePhase.NIGHT

    def test_increments_night_number(self, engine: GameEngine):
        """begin_night_phase should increment the night_number each call."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        assert session.grimoire.night_number == 0

        engine.begin_night_phase(session)
        assert session.grimoire.night_number == 1

        # Transition to DAY then back to NIGHT to simulate normal flow
        session.grimoire.phase = GamePhase.DAY
        engine.begin_night_phase(session)
        assert session.grimoire.night_number == 2

    def test_clears_night_deaths(self, engine: GameEngine):
        """begin_night_phase should clear previous night_deaths."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        session.grimoire.night_deaths = ["some-player-id"]

        engine.begin_night_phase(session)

        assert session.grimoire.night_deaths == []

    def test_clears_poison_flags(self, engine: GameEngine):
        """begin_night_phase should clear is_poisoned from all players."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        # Poison a player before the night begins
        session.grimoire.players[0].is_poisoned = True

        engine.begin_night_phase(session)

        for player in session.grimoire.players:
            assert player.is_poisoned is False

    def test_clears_pending_kills(self, engine: GameEngine):
        """begin_night_phase should clear pending kills from previous night."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        # Simulate a pending kill from a previous incomplete night
        engine._pending_night_kills = ["some-id"]

        engine.begin_night_phase(session)

        assert engine._pending_night_kills == []


# ---------------------------------------------------------------------------
# TestGetNightOrder
# ---------------------------------------------------------------------------


class TestGetNightOrder:
    """Tests for get_night_order returning correct role ordering."""

    def test_first_night_order_returns_correct_roles(self, engine: GameEngine):
        """First night order should follow the script's first_night list."""
        # Create a game with all the roles that have first-night actions
        session = engine.create_game("trouble_brewing", 7, "Human")
        engine.begin_night_phase(session)

        order = engine.get_night_order(session, is_first_night=True)

        # All returned IDs should be valid player IDs
        player_ids = {p.id for p in session.grimoire.players}
        for pid in order:
            assert pid in player_ids

        # The order should respect the script's first_night order:
        # Poisoner, Washerwoman, Librarian, Investigator, Chef, Empath, Butler
        # Only players whose roles appear in the order should be included
        role_names_in_order = []
        for pid in order:
            player = next(p for p in session.grimoire.players if p.id == pid)
            role_names_in_order.append(player.role.name.lower())

        # Verify ordering matches the script's first_night list
        script_first_night = [
            "poisoner", "washerwoman", "librarian", "investigator",
            "chef", "empath", "butler",
        ]
        # Filter to only the roles present in the game
        expected_order = [
            r for r in script_first_night if r in role_names_in_order
        ]
        assert role_names_in_order == expected_order

    def test_other_nights_order_returns_correct_roles(self, engine: GameEngine):
        """Other nights order should follow the script's other_nights list."""
        session = engine.create_game("trouble_brewing", 7, "Human")
        engine.begin_night_phase(session)

        order = engine.get_night_order(session, is_first_night=False)

        player_ids = {p.id for p in session.grimoire.players}
        for pid in order:
            assert pid in player_ids

        role_names_in_order = []
        for pid in order:
            player = next(p for p in session.grimoire.players if p.id == pid)
            role_names_in_order.append(player.role.name.lower())

        # Script other_nights: Poisoner, Imp, Empath, Butler
        script_other_nights = ["poisoner", "imp", "empath", "butler"]
        expected_order = [
            r for r in script_other_nights if r in role_names_in_order
        ]
        assert role_names_in_order == expected_order

    def test_skips_dead_players(self, engine: GameEngine):
        """get_night_order should not include dead players."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        # Find the Poisoner and kill them
        poisoner = next(
            (p for p in session.grimoire.players
             if p.role.name.lower() == "poisoner"),
            None,
        )
        if poisoner:
            poisoner.status = PlayerStatus.DEAD

        order = engine.get_night_order(session, is_first_night=True)

        # Dead poisoner should not be in the order
        if poisoner:
            assert poisoner.id not in order

    def test_only_living_players_in_order(self, engine: GameEngine):
        """All returned player IDs should correspond to living players."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        # Kill a couple of players
        session.grimoire.players[0].status = PlayerStatus.DEAD
        session.grimoire.players[1].status = PlayerStatus.DEAD

        order = engine.get_night_order(session, is_first_night=True)

        alive_ids = {
            p.id for p in session.grimoire.players
            if p.status == PlayerStatus.ALIVE
        }
        for pid in order:
            assert pid in alive_ids


# ---------------------------------------------------------------------------
# TestDemonKill
# ---------------------------------------------------------------------------


class TestDemonKill:
    """Tests for Demon kill via resolve_night_action."""

    def test_demon_kill_marks_target_dead(self, engine: GameEngine):
        """Demon kill action should mark target as DEAD after complete_night_phase."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        # Find the Imp and a non-Imp target
        imp = next(
            p for p in session.grimoire.players
            if p.role.role_type == RoleType.DEMON
        )
        target = next(
            p for p in session.grimoire.players
            if p.id != imp.id and p.status == PlayerStatus.ALIVE
        )

        kill_action = NightAction(
            player_id=imp.id, action_type="kill", target_id=target.id
        )
        result = engine.resolve_night_action(session, imp.id, kill_action)
        assert result.success is True

        # Complete the night to apply pending kills
        summary = engine.complete_night_phase(session)

        assert target.status == PlayerStatus.DEAD
        assert target.id in summary.deaths

    def test_targeting_dead_player_has_no_effect(self, engine: GameEngine):
        """Targeting a dead player should have no effect."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        # Find the Imp and a target, kill the target first
        imp = next(
            p for p in session.grimoire.players
            if p.role.role_type == RoleType.DEMON
        )
        target = next(
            p for p in session.grimoire.players
            if p.id != imp.id
        )
        target.status = PlayerStatus.DEAD

        kill_action = NightAction(
            player_id=imp.id, action_type="kill", target_id=target.id
        )
        result = engine.resolve_night_action(session, imp.id, kill_action)
        assert result.success is True

        summary = engine.complete_night_phase(session)

        # No deaths should occur since target was already dead
        assert target.id not in summary.deaths
        assert summary.deaths == []

    def test_demon_kill_grants_vote_token(self, engine: GameEngine):
        """Demon kill should grant the dead target a Vote_Token (has_vote_token = True)."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        imp = next(
            p for p in session.grimoire.players
            if p.role.role_type == RoleType.DEMON
        )
        target = next(
            p for p in session.grimoire.players
            if p.id != imp.id and p.status == PlayerStatus.ALIVE
        )

        # Target should not have a vote token before death
        assert target.has_vote_token is False

        kill_action = NightAction(
            player_id=imp.id, action_type="kill", target_id=target.id
        )
        engine.resolve_night_action(session, imp.id, kill_action)
        engine.complete_night_phase(session)

        # After death, target should have a vote token
        assert target.status == PlayerStatus.DEAD
        assert target.has_vote_token is True

    def test_dead_demon_action_is_noop(self, engine: GameEngine):
        """A dead Demon's kill action should have no effect."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        imp = next(
            p for p in session.grimoire.players
            if p.role.role_type == RoleType.DEMON
        )
        target = next(
            p for p in session.grimoire.players
            if p.id != imp.id and p.status == PlayerStatus.ALIVE
        )

        # Kill the Imp first
        imp.status = PlayerStatus.DEAD

        kill_action = NightAction(
            player_id=imp.id, action_type="kill", target_id=target.id
        )
        result = engine.resolve_night_action(session, imp.id, kill_action)
        assert result.success is False

        summary = engine.complete_night_phase(session)
        assert target.status == PlayerStatus.ALIVE
        assert summary.deaths == []


# ---------------------------------------------------------------------------
# TestCompleteNightPhase
# ---------------------------------------------------------------------------


class TestCompleteNightPhase:
    """Tests for complete_night_phase returning NightSummary."""

    def test_returns_night_summary_with_deaths(self, engine: GameEngine):
        """complete_night_phase should return a NightSummary with dead player IDs."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        imp = next(
            p for p in session.grimoire.players
            if p.role.role_type == RoleType.DEMON
        )
        target = next(
            p for p in session.grimoire.players
            if p.id != imp.id and p.status == PlayerStatus.ALIVE
        )

        kill_action = NightAction(
            player_id=imp.id, action_type="kill", target_id=target.id
        )
        engine.resolve_night_action(session, imp.id, kill_action)
        summary = engine.complete_night_phase(session)

        assert isinstance(summary, NightSummary)
        assert target.id in summary.deaths
        assert summary.night_number == session.grimoire.night_number

    def test_night_summary_contains_only_player_ids(self, engine: GameEngine):
        """NightSummary deaths should contain only player IDs, no cause info."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        imp = next(
            p for p in session.grimoire.players
            if p.role.role_type == RoleType.DEMON
        )
        target = next(
            p for p in session.grimoire.players
            if p.id != imp.id and p.status == PlayerStatus.ALIVE
        )

        kill_action = NightAction(
            player_id=imp.id, action_type="kill", target_id=target.id
        )
        engine.resolve_night_action(session, imp.id, kill_action)
        summary = engine.complete_night_phase(session)

        # The deaths list should only contain string IDs
        for death_id in summary.deaths:
            assert isinstance(death_id, str)
            assert death_id == target.id

    def test_no_deaths_returns_empty_list(self, engine: GameEngine):
        """complete_night_phase with no kills returns an empty deaths list."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        # Don't perform any kill actions
        summary = engine.complete_night_phase(session)

        assert summary.deaths == []
        assert summary.night_number == 1

    def test_deaths_stored_in_grimoire(self, engine: GameEngine):
        """Night deaths should be stored in grimoire.night_deaths."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        imp = next(
            p for p in session.grimoire.players
            if p.role.role_type == RoleType.DEMON
        )
        target = next(
            p for p in session.grimoire.players
            if p.id != imp.id and p.status == PlayerStatus.ALIVE
        )

        kill_action = NightAction(
            player_id=imp.id, action_type="kill", target_id=target.id
        )
        engine.resolve_night_action(session, imp.id, kill_action)
        engine.complete_night_phase(session)

        assert target.id in session.grimoire.night_deaths


# ---------------------------------------------------------------------------
# TestWasherwomanFirstNightInfo
# ---------------------------------------------------------------------------


class TestWasherwomanFirstNightInfo:
    """Tests for Washerwoman receiving correct first-night info."""

    def test_washerwoman_receives_two_players_one_townsfolk(self):
        """Washerwoman should learn 'X or Y is the <Townsfolk role>'."""
        washerwoman = _make_player(
            "Alice", "Washerwoman", RoleType.TOWNSFOLK, Team.GOOD
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Charlie", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player("Diana", "Poisoner", RoleType.MINION, Team.EVIL)
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session(
            [washerwoman, chef, empath, poisoner, imp],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        result = generate_info_for_role(session, washerwoman.id)

        assert result.success is True
        assert result.information is not None
        # Format: "X or Y is the <Role>."
        assert " or " in result.information
        assert "is the" in result.information
        # Role mentioned should be a Townsfolk (Chef or Empath)
        assert any(
            role in result.information for role in ["Chef", "Empath"]
        )

    def test_washerwoman_one_shown_is_correct_role(self):
        """One of the two shown players must actually hold the stated role."""
        washerwoman = _make_player(
            "Alice", "Washerwoman", RoleType.TOWNSFOLK, Team.GOOD
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Charlie", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player("Diana", "Poisoner", RoleType.MINION, Team.EVIL)
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session(
            [washerwoman, chef, empath, poisoner, imp],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        # Run multiple times due to randomness
        for _ in range(20):
            result = generate_info_for_role(session, washerwoman.id)
            info = result.information
            role_name = info.split("is the ")[1].rstrip(".")
            # The real holder of that role must appear in the info
            role_holder = next(
                (p for p in [chef, empath] if p.role.name == role_name), None
            )
            assert role_holder is not None
            assert role_holder.name in info


# ---------------------------------------------------------------------------
# TestLibrarianFirstNightInfo
# ---------------------------------------------------------------------------


class TestLibrarianFirstNightInfo:
    """Tests for Librarian receiving correct first-night info."""

    def test_librarian_with_outsider_in_play(self):
        """Librarian should learn about an Outsider if one exists."""
        librarian = _make_player(
            "Alice", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )
        butler = _make_player("Bob", "Butler", RoleType.OUTSIDER, Team.GOOD)
        chef = _make_player("Charlie", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player("Diana", "Poisoner", RoleType.MINION, Team.EVIL)
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session(
            [librarian, butler, chef, poisoner, imp],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        result = generate_info_for_role(session, librarian.id)

        assert result.success is True
        assert result.information is not None
        assert "Butler" in result.information
        assert "Bob" in result.information
        assert "is the" in result.information

    def test_librarian_no_outsiders(self):
        """Librarian should learn there are no Outsiders if none exist."""
        librarian = _make_player(
            "Alice", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Charlie", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player("Diana", "Poisoner", RoleType.MINION, Team.EVIL)
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session(
            [librarian, chef, empath, poisoner, imp],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        result = generate_info_for_role(session, librarian.id)

        assert result.success is True
        assert result.information == "There are no Outsiders in play."


# ---------------------------------------------------------------------------
# TestInvestigatorFirstNightInfo
# ---------------------------------------------------------------------------


class TestInvestigatorFirstNightInfo:
    """Tests for Investigator receiving correct first-night info."""

    def test_investigator_receives_evil_player_info(self):
        """Investigator should learn about a Minion or Demon."""
        investigator = _make_player(
            "Alice", "Investigator", RoleType.TOWNSFOLK, Team.GOOD
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Charlie", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player("Diana", "Poisoner", RoleType.MINION, Team.EVIL)
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session(
            [investigator, chef, empath, poisoner, imp],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        result = generate_info_for_role(session, investigator.id)

        assert result.success is True
        assert result.information is not None
        assert " or " in result.information
        assert "is the" in result.information
        assert any(
            role in result.information for role in ["Poisoner", "Imp"]
        )

    def test_investigator_one_shown_is_correct_evil(self):
        """One of the two shown players must hold the stated evil role."""
        investigator = _make_player(
            "Alice", "Investigator", RoleType.TOWNSFOLK, Team.GOOD
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Charlie", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player("Diana", "Poisoner", RoleType.MINION, Team.EVIL)
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session(
            [investigator, chef, empath, poisoner, imp],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        for _ in range(20):
            result = generate_info_for_role(session, investigator.id)
            info = result.information
            role_name = info.split("is the ")[1].rstrip(".")
            evil_holder = next(
                (p for p in [poisoner, imp] if p.role.name == role_name), None
            )
            assert evil_holder is not None
            assert evil_holder.name in info


# ---------------------------------------------------------------------------
# TestChefFirstNightInfo
# ---------------------------------------------------------------------------


class TestChefFirstNightInfo:
    """Tests for Chef receiving correct evil-neighbor count."""

    def test_chef_zero_evil_pairs(self):
        """Chef should get 0 when evil players are not adjacent."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Bob", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player("Charlie", "Poisoner", RoleType.MINION, Team.EVIL)
        librarian = _make_player("Diana", "Librarian", RoleType.TOWNSFOLK, Team.GOOD)
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        # Seating: Chef(G), Empath(G), Poisoner(E), Librarian(G), Imp(E)
        # No adjacent evil pair
        session = _make_session(
            [chef, empath, poisoner, librarian, imp],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        result = generate_info_for_role(session, chef.id)

        assert result.success is True
        assert result.information == (
            "There are 0 pairs of evil players sitting next to each other."
        )

    def test_chef_one_evil_pair(self):
        """Chef should get 1 when one pair of evil players sit together."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player("Bob", "Poisoner", RoleType.MINION, Team.EVIL)
        imp = _make_player("Charlie", "Imp", RoleType.DEMON, Team.EVIL)
        empath = _make_player("Diana", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        librarian = _make_player("Edward", "Librarian", RoleType.TOWNSFOLK, Team.GOOD)

        # Seating: Chef(G), Poisoner(E), Imp(E), Empath(G), Librarian(G)
        # Poisoner-Imp is 1 evil pair
        session = _make_session(
            [chef, poisoner, imp, empath, librarian],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        result = generate_info_for_role(session, chef.id)

        assert result.success is True
        assert result.information == (
            "There are 1 pairs of evil players sitting next to each other."
        )


# ---------------------------------------------------------------------------
# TestEmpathFirstNightInfo
# ---------------------------------------------------------------------------


class TestEmpathFirstNightInfo:
    """Tests for Empath receiving correct alive-evil-neighbor count."""

    def test_empath_zero_evil_neighbours(self):
        """Empath should get 0 when both alive neighbours are good."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Bob", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        librarian = _make_player("Charlie", "Librarian", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player("Diana", "Poisoner", RoleType.MINION, Team.EVIL)
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        # Seating: Chef(G), Empath(G), Librarian(G), Poisoner(E), Imp(E)
        # Empath's neighbors: Chef(left, good) and Librarian(right, good)
        session = _make_session(
            [chef, empath, librarian, poisoner, imp],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        result = generate_info_for_role(session, empath.id)

        assert result.success is True
        assert result.information == "0 of your neighbours are evil."

    def test_empath_one_evil_neighbour(self):
        """Empath should get 1 when one alive neighbour is evil."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Bob", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player("Charlie", "Poisoner", RoleType.MINION, Team.EVIL)
        librarian = _make_player("Diana", "Librarian", RoleType.TOWNSFOLK, Team.GOOD)
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        # Seating: Chef(G), Empath(G), Poisoner(E), Librarian(G), Imp(E)
        # Empath's neighbors: Chef(left, good) and Poisoner(right, evil) = 1
        session = _make_session(
            [chef, empath, poisoner, librarian, imp],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        result = generate_info_for_role(session, empath.id)

        assert result.success is True
        assert result.information == "1 of your neighbours are evil."

    def test_empath_skips_dead_players_for_neighbours(self):
        """Empath should skip dead players when finding neighbours."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        dead_good = _make_player(
            "Bob", "Librarian", RoleType.TOWNSFOLK, Team.GOOD,
            status=PlayerStatus.DEAD,
        )
        empath = _make_player("Charlie", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        dead_evil = _make_player(
            "Diana", "Poisoner", RoleType.MINION, Team.EVIL,
            status=PlayerStatus.DEAD,
        )
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        # Seating: Chef(G,alive), dead_good(G,dead), Empath(G,alive),
        #          dead_evil(E,dead), Imp(E,alive)
        # Empath's alive neighbours: Chef(left, good) and Imp(right, evil)
        session = _make_session(
            [chef, dead_good, empath, dead_evil, imp],
            phase=GamePhase.NIGHT,
            night_number=1,
        )

        result = generate_info_for_role(session, empath.id)

        assert result.success is True
        assert result.information == "1 of your neighbours are evil."
