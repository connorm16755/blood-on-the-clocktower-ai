"""Unit tests for the Storyteller information distribution module."""

import pytest

from game_engine.storyteller import (
    generate_info_for_role,
    _count_evil_pairs,
    _count_evil_neighbours,
)
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


def _make_role(name: str, role_type: RoleType, team: Team) -> RoleDefinition:
    """Helper to create a minimal RoleDefinition."""
    return RoleDefinition(
        name=name,
        role_type=role_type,
        team=team,
        ability_description="test",
        first_night_order=None,
        other_nights_order=None,
        setup_requirements={},
        information_provided="test",
        game_rules=[],
    )


def _make_player(
    name: str,
    role_name: str,
    role_type: RoleType,
    team: Team,
    is_poisoned: bool = False,
    status: PlayerStatus = PlayerStatus.ALIVE,
) -> Player:
    """Helper to create a Player with a role."""
    p = Player(name=name)
    p.role = _make_role(role_name, role_type, team)
    p.team = team
    p.is_poisoned = is_poisoned
    p.status = status
    return p


def _make_session(players: list[Player]) -> GameSession:
    """Helper to create a GameSession with given players."""
    grimoire = Grimoire(
        players=players,
        phase=GamePhase.NIGHT,
        day_number=0,
        night_number=1,
    )
    return GameSession(script_name="trouble_brewing", grimoire=grimoire)


class TestWasherwomanInfo:
    """Tests for Washerwoman first-night information."""

    def test_washerwoman_gets_correct_info(self):
        """Washerwoman should learn one of two players is a specific Townsfolk."""
        washerwoman = _make_player(
            "Alice", "Washerwoman", RoleType.TOWNSFOLK, Team.GOOD
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Diana", "Imp", RoleType.DEMON, Team.EVIL)
        empath = _make_player("Edward", "Empath", RoleType.TOWNSFOLK, Team.GOOD)

        session = _make_session(
            [washerwoman, chef, poisoner, imp, empath]
        )

        result = generate_info_for_role(session, washerwoman.id)

        assert result.success is True
        assert result.information is not None
        # Should mention a Townsfolk role name
        assert any(
            role in result.information
            for role in ["Chef", "Empath"]
        )
        # Should mention "or" (showing two players)
        assert " or " in result.information
        # Should end with "is the <Role>."
        assert "is the" in result.information

    def test_washerwoman_shows_correct_townsfolk(self):
        """One of the two shown players must actually be the stated role."""
        washerwoman = _make_player(
            "Alice", "Washerwoman", RoleType.TOWNSFOLK, Team.GOOD
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Diana", "Imp", RoleType.DEMON, Team.EVIL)
        empath = _make_player("Edward", "Empath", RoleType.TOWNSFOLK, Team.GOOD)

        session = _make_session(
            [washerwoman, chef, poisoner, imp, empath]
        )

        # Run multiple times to verify correctness
        for _ in range(20):
            result = generate_info_for_role(session, washerwoman.id)
            info = result.information
            # Extract role from "X or Y is the <Role>."
            role_name = info.split("is the ")[1].rstrip(".")
            # Find the player with that role
            role_player = None
            for p in [chef, empath]:
                if p.role.name == role_name:
                    role_player = p
                    break
            assert role_player is not None, f"Role {role_name} not found"
            # That player's name must appear in the info
            assert role_player.name in info

    def test_washerwoman_poisoned_gives_potentially_false_info(self):
        """Poisoned Washerwoman may give incorrect information."""
        washerwoman = _make_player(
            "Alice", "Washerwoman", RoleType.TOWNSFOLK, Team.GOOD,
            is_poisoned=True,
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Diana", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session([washerwoman, chef, poisoner, imp])

        result = generate_info_for_role(session, washerwoman.id)

        assert result.success is True
        assert result.information is not None
        # Still formatted like normal info (has "or" and "is the")
        assert "is the" in result.information


class TestLibrarianInfo:
    """Tests for Librarian first-night information."""

    def test_librarian_no_outsiders(self):
        """Librarian should learn there are no Outsiders if none in play."""
        librarian = _make_player(
            "Alice", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Diana", "Imp", RoleType.DEMON, Team.EVIL)
        empath = _make_player("Edward", "Empath", RoleType.TOWNSFOLK, Team.GOOD)

        session = _make_session(
            [librarian, chef, poisoner, imp, empath]
        )

        result = generate_info_for_role(session, librarian.id)

        assert result.success is True
        assert result.information == "There are no Outsiders in play."

    def test_librarian_with_outsider(self):
        """Librarian should learn one of two players is an Outsider role."""
        librarian = _make_player(
            "Alice", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )
        butler = _make_player("Bob", "Butler", RoleType.OUTSIDER, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Diana", "Imp", RoleType.DEMON, Team.EVIL)
        chef = _make_player("Edward", "Chef", RoleType.TOWNSFOLK, Team.GOOD)

        session = _make_session(
            [librarian, butler, poisoner, imp, chef]
        )

        result = generate_info_for_role(session, librarian.id)

        assert result.success is True
        assert result.information is not None
        assert "Butler" in result.information
        assert "is the" in result.information
        # Butler's name must appear (they are the correct player)
        assert "Bob" in result.information

    def test_librarian_poisoned(self):
        """Poisoned Librarian may give false information."""
        librarian = _make_player(
            "Alice", "Librarian", RoleType.TOWNSFOLK, Team.GOOD,
            is_poisoned=True,
        )
        butler = _make_player("Bob", "Butler", RoleType.OUTSIDER, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Diana", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session([librarian, butler, poisoner, imp])

        result = generate_info_for_role(session, librarian.id)

        assert result.success is True
        assert result.information is not None


class TestInvestigatorInfo:
    """Tests for Investigator first-night information."""

    def test_investigator_gets_evil_info(self):
        """Investigator should learn one of two players is a Minion/Demon."""
        investigator = _make_player(
            "Alice", "Investigator", RoleType.TOWNSFOLK, Team.GOOD
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Diana", "Imp", RoleType.DEMON, Team.EVIL)
        empath = _make_player("Edward", "Empath", RoleType.TOWNSFOLK, Team.GOOD)

        session = _make_session(
            [investigator, chef, poisoner, imp, empath]
        )

        result = generate_info_for_role(session, investigator.id)

        assert result.success is True
        assert result.information is not None
        # Should mention an evil role
        assert any(
            role in result.information for role in ["Poisoner", "Imp"]
        )
        assert "is the" in result.information

    def test_investigator_shows_correct_evil_player(self):
        """One of the two shown players must actually be the stated evil role."""
        investigator = _make_player(
            "Alice", "Investigator", RoleType.TOWNSFOLK, Team.GOOD
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Diana", "Imp", RoleType.DEMON, Team.EVIL)
        empath = _make_player("Edward", "Empath", RoleType.TOWNSFOLK, Team.GOOD)

        session = _make_session(
            [investigator, chef, poisoner, imp, empath]
        )

        for _ in range(20):
            result = generate_info_for_role(session, investigator.id)
            info = result.information
            role_name = info.split("is the ")[1].rstrip(".")
            # The evil player with that role name must appear in the info
            evil_player = None
            for p in [poisoner, imp]:
                if p.role.name == role_name:
                    evil_player = p
                    break
            assert evil_player is not None
            assert evil_player.name in info

    def test_investigator_poisoned(self):
        """Poisoned Investigator may give false information."""
        investigator = _make_player(
            "Alice", "Investigator", RoleType.TOWNSFOLK, Team.GOOD,
            is_poisoned=True,
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Diana", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session([investigator, chef, poisoner, imp])

        result = generate_info_for_role(session, investigator.id)

        assert result.success is True
        assert result.information is not None
        assert "is the" in result.information


class TestChefInfo:
    """Tests for Chef first-night information."""

    def test_chef_no_evil_pairs(self):
        """Chef should get 0 when no evil players sit next to each other."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Bob", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        librarian = _make_player(
            "Diana", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        # Seating: Chef(G), Empath(G), Poisoner(E), Librarian(G), Imp(E)
        # Pairs: Chef-Empath(GG), Empath-Poisoner(GE), Poisoner-Librarian(EG),
        #        Librarian-Imp(GE), Imp-Chef(EG) = 0 evil pairs
        session = _make_session([chef, empath, poisoner, librarian, imp])

        result = generate_info_for_role(session, chef.id)

        assert result.success is True
        assert result.information == (
            "There are 0 pairs of evil players sitting next to each other."
        )

    def test_chef_one_evil_pair(self):
        """Chef should get 1 when one pair of evil players sit together."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Bob", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Charlie", "Imp", RoleType.DEMON, Team.EVIL)
        empath = _make_player("Diana", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        librarian = _make_player(
            "Edward", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )

        # Seating: Chef(G), Poisoner(E), Imp(E), Empath(G), Librarian(G)
        # Pairs: Chef-Poisoner(GE), Poisoner-Imp(EE!), Imp-Empath(EG),
        #        Empath-Librarian(GG), Librarian-Chef(GG) = 1 evil pair
        session = _make_session([chef, poisoner, imp, empath, librarian])

        result = generate_info_for_role(session, chef.id)

        assert result.success is True
        assert result.information == (
            "There are 1 pairs of evil players sitting next to each other."
        )

    def test_chef_wrapping_evil_pair(self):
        """Chef should count wrapping pairs (last and first player)."""
        poisoner = _make_player(
            "Alice", "Poisoner", RoleType.MINION, Team.EVIL
        )
        chef = _make_player("Bob", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Charlie", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        librarian = _make_player(
            "Diana", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        # Seating: Poisoner(E), Chef(G), Empath(G), Librarian(G), Imp(E)
        # Pairs: Poisoner-Chef(EG), Chef-Empath(GG), Empath-Librarian(GG),
        #        Librarian-Imp(GE), Imp-Poisoner(EE!) = 1 evil pair (wrapping)
        session = _make_session([poisoner, chef, empath, librarian, imp])

        result = generate_info_for_role(session, chef.id)

        assert result.success is True
        assert result.information == (
            "There are 1 pairs of evil players sitting next to each other."
        )

    def test_chef_poisoned(self):
        """Poisoned Chef gets a random count (0-2)."""
        chef = _make_player(
            "Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD,
            is_poisoned=True,
        )
        poisoner = _make_player(
            "Bob", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Charlie", "Imp", RoleType.DEMON, Team.EVIL)
        empath = _make_player("Diana", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        librarian = _make_player(
            "Edward", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )

        session = _make_session([chef, poisoner, imp, empath, librarian])

        result = generate_info_for_role(session, chef.id)

        assert result.success is True
        assert result.information is not None
        assert "pairs of evil players sitting next to each other" in result.information


class TestEmpathInfo:
    """Tests for Empath night information."""

    def test_empath_no_evil_neighbours(self):
        """Empath should get 0 when both neighbours are good."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Bob", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        librarian = _make_player(
            "Charlie", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )
        poisoner = _make_player(
            "Diana", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        # Seating: Chef(G), Empath(G), Librarian(G), Poisoner(E), Imp(E)
        # Empath's neighbours: Chef (left) and Librarian (right) - both good
        session = _make_session([chef, empath, librarian, poisoner, imp])

        result = generate_info_for_role(session, empath.id)

        assert result.success is True
        assert result.information == "0 of your neighbours are evil."

    def test_empath_one_evil_neighbour(self):
        """Empath should get 1 when one neighbour is evil."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player("Bob", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Charlie", "Poisoner", RoleType.MINION, Team.EVIL
        )
        librarian = _make_player(
            "Diana", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        # Seating: Chef(G), Empath(G), Poisoner(E), Librarian(G), Imp(E)
        # Empath's neighbours: Chef (left, good) and Poisoner (right, evil)
        session = _make_session([chef, empath, poisoner, librarian, imp])

        result = generate_info_for_role(session, empath.id)

        assert result.success is True
        assert result.information == "1 of your neighbours are evil."

    def test_empath_two_evil_neighbours(self):
        """Empath should get 2 when both neighbours are evil."""
        poisoner = _make_player(
            "Alice", "Poisoner", RoleType.MINION, Team.EVIL
        )
        empath = _make_player("Bob", "Empath", RoleType.TOWNSFOLK, Team.GOOD)
        imp = _make_player("Charlie", "Imp", RoleType.DEMON, Team.EVIL)
        chef = _make_player("Diana", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        librarian = _make_player(
            "Edward", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )

        # Seating: Poisoner(E), Empath(G), Imp(E), Chef(G), Librarian(G)
        # Empath's neighbours: Poisoner (left, evil) and Imp (right, evil)
        session = _make_session([poisoner, empath, imp, chef, librarian])

        result = generate_info_for_role(session, empath.id)

        assert result.success is True
        assert result.information == "2 of your neighbours are evil."

    def test_empath_skips_dead_neighbours(self):
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
        # Empath's alive neighbours: Chef (left, skipping dead) and Imp (right, skipping dead)
        session = _make_session([chef, dead_good, empath, dead_evil, imp])

        result = generate_info_for_role(session, empath.id)

        assert result.success is True
        # Left neighbour: Chef (good), Right neighbour: Imp (evil) = 1
        assert result.information == "1 of your neighbours are evil."

    def test_empath_poisoned(self):
        """Poisoned Empath gets a random count (0-2)."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        empath = _make_player(
            "Bob", "Empath", RoleType.TOWNSFOLK, Team.GOOD,
            is_poisoned=True,
        )
        librarian = _make_player(
            "Charlie", "Librarian", RoleType.TOWNSFOLK, Team.GOOD
        )
        poisoner = _make_player(
            "Diana", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session([chef, empath, librarian, poisoner, imp])

        result = generate_info_for_role(session, empath.id)

        assert result.success is True
        assert result.information is not None
        assert "of your neighbours are evil" in result.information


class TestGenerateInfoEdgeCases:
    """Tests for edge cases in generate_info_for_role."""

    def test_unknown_player_id_returns_failure(self):
        """Should return failure for unknown player_id."""
        chef = _make_player("Alice", "Chef", RoleType.TOWNSFOLK, Team.GOOD)
        session = _make_session([chef])

        result = generate_info_for_role(session, "nonexistent-id")

        assert result.success is False

    def test_non_info_role_returns_success_no_info(self):
        """Non-info roles (like Slayer) return success with no information."""
        slayer = _make_player("Alice", "Slayer", RoleType.TOWNSFOLK, Team.GOOD)
        poisoner = _make_player(
            "Bob", "Poisoner", RoleType.MINION, Team.EVIL
        )
        imp = _make_player("Charlie", "Imp", RoleType.DEMON, Team.EVIL)

        session = _make_session([slayer, poisoner, imp])

        result = generate_info_for_role(session, slayer.id)

        assert result.success is True
        assert result.information is None


class TestCountEvilPairs:
    """Direct tests for the evil pair counting logic."""

    def test_empty_grimoire(self):
        """No players means no pairs."""
        grimoire = Grimoire(
            players=[], phase=GamePhase.NIGHT, day_number=0, night_number=1
        )
        assert _count_evil_pairs(grimoire) == 0

    def test_all_evil_adjacent(self):
        """All evil players adjacent: count consecutive pairs."""
        p1 = _make_player("A", "Poisoner", RoleType.MINION, Team.EVIL)
        p2 = _make_player("B", "Imp", RoleType.DEMON, Team.EVIL)
        p3 = _make_player("C", "Chef", RoleType.TOWNSFOLK, Team.GOOD)

        # Seating: E, E, G -> pairs: (E,E)=1, (E,G)=0, (G,E)=0 -> 1
        grimoire = Grimoire(
            players=[p1, p2, p3],
            phase=GamePhase.NIGHT,
            day_number=0,
            night_number=1,
        )
        assert _count_evil_pairs(grimoire) == 1
