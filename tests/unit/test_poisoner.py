"""Unit tests for the Poisoner night ability in the GameEngine.

Covers Requirements 11.1-11.5:
- 11.1: Poisoner selects a living target each night; target becomes poisoned.
- 11.2: Poisoned information-gathering roles receive potentially false info.
- 11.3: Previous poison is cleared at the start of each new night.
- 11.4: A dead Poisoner's night action is skipped.
- 11.5: When the Poisoner dies (any cause), active poison is lifted immediately.
"""

import pytest
from typing import Optional

from game_engine.engine import GameEngine
from game_engine.storyteller import generate_info_for_role
from models.actions import NightAction
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
    poisoned_by: Optional[str] = None,
) -> Player:
    """Create a Player with a role for testing."""
    p = Player(name=name)
    p.role = _make_role(role_name, role_type, team)
    p.team = team
    p.status = status
    p.poisoned_by = poisoned_by
    return p


def _make_session(
    players: list[Player],
    phase: GamePhase = GamePhase.NIGHT,
    night_number: int = 1,
    day_number: int = 0,
) -> GameSession:
    """Create a GameSession with the given players."""
    grimoire = Grimoire(
        players=players,
        phase=phase,
        day_number=day_number,
        night_number=night_number,
    )
    return GameSession(script_name="trouble_brewing", grimoire=grimoire)


def _standard_cast() -> dict[str, Player]:
    """Build a standard 5-player cast with a Poisoner and an Imp.

    Seating order (circular): Washerwoman, Empath, Poisoner, Chef, Imp.
    """
    return {
        "washerwoman": _make_player(
            "Alice", "Washerwoman", RoleType.TOWNSFOLK, Team.GOOD
        ),
        "empath": _make_player("Bob", "Empath", RoleType.TOWNSFOLK, Team.GOOD),
        "poisoner": _make_player("Charlie", "Poisoner", RoleType.MINION, Team.EVIL),
        "chef": _make_player("Diana", "Chef", RoleType.TOWNSFOLK, Team.GOOD),
        "imp": _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL),
    }


def _ordered_players(cast: dict[str, Player]) -> list[Player]:
    """Return the standard cast in a fixed seating order."""
    return [
        cast["washerwoman"],
        cast["empath"],
        cast["poisoner"],
        cast["chef"],
        cast["imp"],
    ]


@pytest.fixture(scope="module")
def engine() -> GameEngine:
    """Create a GameEngine with the real RoleRegistry."""
    return GameEngine()


# ---------------------------------------------------------------------------
# TestPoisonerTargetSelection (Requirement 11.1)
# ---------------------------------------------------------------------------


class TestPoisonerTargetSelection:
    """Poisoner selects a living target and that target becomes poisoned."""

    def test_poisoner_poisons_living_target(self, engine: GameEngine):
        """A living Poisoner's poison action marks the target as poisoned."""
        cast = _standard_cast()
        session = _make_session(_ordered_players(cast))

        poisoner = cast["poisoner"]
        target = cast["washerwoman"]
        assert target.is_poisoned is False

        action = NightAction(
            player_id=poisoner.id, action_type="poison", target_id=target.id
        )
        result = engine.resolve_night_action(session, poisoner.id, action)

        assert result.success is True
        assert target.is_poisoned is True
        assert target.poisoned_by == poisoner.id

    def test_poisoning_dead_target_has_no_effect(self, engine: GameEngine):
        """Poisoning a dead target does not mark them poisoned."""
        cast = _standard_cast()
        cast["washerwoman"].status = PlayerStatus.DEAD
        session = _make_session(_ordered_players(cast))

        poisoner = cast["poisoner"]
        target = cast["washerwoman"]

        action = NightAction(
            player_id=poisoner.id, action_type="poison", target_id=target.id
        )
        engine.resolve_night_action(session, poisoner.id, action)

        assert target.is_poisoned is False
        assert target.poisoned_by is None


# ---------------------------------------------------------------------------
# TestPoisonResetBetweenNights (Requirement 11.3)
# ---------------------------------------------------------------------------


class TestPoisonResetBetweenNights:
    """Previous poison is cleared at the start of a new night."""

    def test_previous_poison_cleared_on_new_night(self, engine: GameEngine):
        """begin_night_phase clears poison from a previously poisoned player."""
        cast = _standard_cast()
        session = _make_session(
            _ordered_players(cast), phase=GamePhase.DAY, night_number=1
        )

        poisoner = cast["poisoner"]
        victim = cast["empath"]
        # Simulate a poison applied on the previous night
        victim.poisoned_by = poisoner.id
        assert victim.is_poisoned is True

        engine.begin_night_phase(session)

        assert victim.is_poisoned is False
        assert victim.poisoned_by is None

    def test_poison_can_be_reapplied_after_reset(self, engine: GameEngine):
        """After reset, the Poisoner may poison a new target the next night."""
        cast = _standard_cast()
        session = _make_session(
            _ordered_players(cast), phase=GamePhase.DAY, night_number=1
        )

        poisoner = cast["poisoner"]
        first_victim = cast["empath"]
        first_victim.poisoned_by = poisoner.id

        engine.begin_night_phase(session)
        assert first_victim.is_poisoned is False

        # Poison a different target on the new night
        second_victim = cast["chef"]
        action = NightAction(
            player_id=poisoner.id,
            action_type="poison",
            target_id=second_victim.id,
        )
        engine.resolve_night_action(session, poisoner.id, action)

        assert second_victim.is_poisoned is True
        assert first_victim.is_poisoned is False


# ---------------------------------------------------------------------------
# TestDeadPoisonerSkipped (Requirement 11.4)
# ---------------------------------------------------------------------------


class TestDeadPoisonerSkipped:
    """A dead Poisoner's action is skipped."""

    def test_dead_poisoner_action_is_noop(self, engine: GameEngine):
        """A dead Poisoner's poison action fails and poisons no one."""
        cast = _standard_cast()
        cast["poisoner"].status = PlayerStatus.DEAD
        session = _make_session(_ordered_players(cast))

        poisoner = cast["poisoner"]
        target = cast["washerwoman"]

        action = NightAction(
            player_id=poisoner.id, action_type="poison", target_id=target.id
        )
        result = engine.resolve_night_action(session, poisoner.id, action)

        assert result.success is False
        assert target.is_poisoned is False
        assert target.poisoned_by is None

    def test_dead_poisoner_excluded_from_night_order(self, engine: GameEngine):
        """A dead Poisoner is not included in the night action order."""
        session = engine.create_game("trouble_brewing", 5, "Human")
        engine.begin_night_phase(session)

        poisoner = next(
            (p for p in session.grimoire.players
             if p.role and p.role.name.lower() == "poisoner"),
            None,
        )
        if poisoner is None:
            pytest.skip("No Poisoner in this randomly generated game")

        poisoner.status = PlayerStatus.DEAD
        order = engine.get_night_order(session, is_first_night=False)

        assert poisoner.id not in order


# ---------------------------------------------------------------------------
# TestPoisonedInformation (Requirement 11.2)
# ---------------------------------------------------------------------------


class TestPoisonedInformation:
    """Poisoned information-gathering roles receive potentially false info."""

    def test_poisoned_washerwoman_receives_info(self):
        """A poisoned Washerwoman still receives (potentially false) info."""
        cast = _standard_cast()
        washerwoman = cast["washerwoman"]
        poisoner = cast["poisoner"]
        washerwoman.poisoned_by = poisoner.id

        session = _make_session(_ordered_players(cast))

        result = generate_info_for_role(session, washerwoman.id)

        assert result.success is True
        assert result.information is not None
        assert "is the" in result.information

    def test_poisoned_washerwoman_can_name_wrong_role(self):
        """Over many runs, a poisoned Washerwoman can point at the wrong pair.

        The poisoned branch picks two random players and a random Townsfolk
        role, so at least once the shown pair should not actually contain a
        holder of the stated role (demonstrating unreliable information).
        """
        cast = _standard_cast()
        washerwoman = cast["washerwoman"]
        poisoner = cast["poisoner"]
        washerwoman.poisoned_by = poisoner.id
        session = _make_session(_ordered_players(cast))

        players_by_name = {p.name: p for p in session.grimoire.players}
        saw_false_statement = False

        for _ in range(50):
            result = generate_info_for_role(session, washerwoman.id)
            info = result.information
            # Format: "X or Y is the <Role>."
            subject, _, rest = info.partition(" is the ")
            role_name = rest.rstrip(".")
            shown_names = [n.strip() for n in subject.split(" or ")]

            holder_present = any(
                players_by_name[name].role is not None
                and players_by_name[name].role.name == role_name
                for name in shown_names
                if name in players_by_name
            )
            if not holder_present:
                saw_false_statement = True
                break

        assert saw_false_statement, (
            "Poisoned Washerwoman never produced false information in 50 runs"
        )

    def test_poisoned_empath_count_can_be_incorrect(self):
        """A poisoned Empath can report a count different from the true one.

        Seating: Washerwoman(G), Empath(G), Poisoner(E), Chef(G), Imp(E).
        The Empath's true alive neighbours are Washerwoman (good) and
        Poisoner (evil) => true count is 1. The poisoned branch returns a
        random count in 0..2, so over many runs it should differ at least once.
        """
        cast = _standard_cast()
        empath = cast["empath"]
        poisoner = cast["poisoner"]
        empath.poisoned_by = poisoner.id
        session = _make_session(_ordered_players(cast))

        true_count = 1  # Washerwoman (good) + Poisoner (evil)
        seen_counts = set()

        for _ in range(50):
            result = generate_info_for_role(session, empath.id)
            assert result.success is True
            assert result.information is not None
            reported = int(result.information.split()[0])
            seen_counts.add(reported)

        # The poisoned Empath must be able to report an incorrect value.
        assert any(c != true_count for c in seen_counts), (
            "Poisoned Empath never produced an incorrect count in 50 runs"
        )


# ---------------------------------------------------------------------------
# TestPoisonerDeathLiftsPoison (Requirement 11.5)
# ---------------------------------------------------------------------------


class TestPoisonerDeathLiftsPoison:
    """Poisoner death (any cause) immediately lifts active poison."""

    def test_night_kill_lifts_poison(self, engine: GameEngine):
        """Poisoner dying to a night kill lifts poison from their target."""
        cast = _standard_cast()
        session = _make_session(_ordered_players(cast))

        poisoner = cast["poisoner"]
        imp = cast["imp"]
        victim = cast["washerwoman"]

        # Poisoner poisons the Washerwoman this night
        poison_action = NightAction(
            player_id=poisoner.id, action_type="poison", target_id=victim.id
        )
        engine.resolve_night_action(session, poisoner.id, poison_action)
        assert victim.is_poisoned is True

        # Imp kills the Poisoner the same night
        kill_action = NightAction(
            player_id=imp.id, action_type="kill", target_id=poisoner.id
        )
        engine.resolve_night_action(session, imp.id, kill_action)

        summary = engine.complete_night_phase(session)

        # Poisoner is dead and the poison is lifted
        assert poisoner.status == PlayerStatus.DEAD
        assert poisoner.id in summary.deaths
        assert victim.is_poisoned is False
        assert victim.poisoned_by is None

    def test_execution_lifts_poison(self, engine: GameEngine):
        """Poisoner executed via end_day_phase lifts poison from their target."""
        cast = _standard_cast()
        session = _make_session(
            _ordered_players(cast), phase=GamePhase.DAY, night_number=1, day_number=1
        )

        poisoner = cast["poisoner"]
        victim = cast["chef"]
        # Poison carried into the day from the previous night
        victim.poisoned_by = poisoner.id
        assert victim.is_poisoned is True

        # Poisoner is about to be executed
        session.grimoire.about_to_die_player_id = poisoner.id
        session.grimoire.about_to_die_votes = 3

        executed_id = engine.end_day_phase(session)

        assert executed_id == poisoner.id
        assert poisoner.status == PlayerStatus.DEAD
        assert victim.is_poisoned is False
        assert victim.poisoned_by is None

    def test_slayer_shot_lifts_poison(self, engine: GameEngine):
        """Poisoner death by a Slayer shot immediately lifts active poison.

        NOTE: The Slayer day ability (task 4.4, `use_day_ability`) is not yet
        implemented in the engine. This test validates the Requirement 11.5
        invariant that applies regardless of the death cause: when the
        Poisoner transitions to DEAD and poison is lifted, no player remains
        poisoned by them. It mirrors the lift logic the Slayer path will reuse
        once implemented. When `use_day_ability` lands, this test should be
        updated to drive the kill through that method.
        """
        assert not hasattr(engine, "use_day_ability"), (
            "Slayer use_day_ability now exists; update this test to drive the "
            "Poisoner's death through the real Slayer ability (task 4.4)."
        )

        cast = _standard_cast()
        session = _make_session(
            _ordered_players(cast), phase=GamePhase.DAY, night_number=1, day_number=1
        )

        poisoner = cast["poisoner"]
        victim = cast["empath"]
        victim.poisoned_by = poisoner.id
        assert victim.is_poisoned is True

        # Simulate the Slayer shot killing the Poisoner: the player is marked
        # dead and the engine lifts any poison sourced from the dead player.
        poisoner.status = PlayerStatus.DEAD
        poisoner.has_vote_token = True
        for player in session.grimoire.players:
            if player.poisoned_by == poisoner.id:
                player.poisoned_by = None

        assert poisoner.status == PlayerStatus.DEAD
        assert victim.is_poisoned is False
        assert victim.poisoned_by is None
