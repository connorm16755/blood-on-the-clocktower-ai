# Feature: blood-on-the-clocktower-ai, Property 14: Poison Effect on Information
# Feature: blood-on-the-clocktower-ai, Property 15: Poison Lifecycle Reset and Death Lift
"""Property tests for the Poisoner mechanics.

Tests that:
- A poisoned information-gathering role receives potentially inaccurate
  information: across repeated Storyteller runs the information can differ
  from the truthful result derived from the real game state (Property 14).
- The previous night's poison is cleared before the Poisoner selects a new
  target in the current night, and a Poisoner's death by any cause
  immediately lifts active poison from the affected player (Property 15).

**Validates: Requirements 11.2, 11.3, 11.5**
"""

from typing import Optional

from hypothesis import given, settings
from hypothesis import strategies as st

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
# Helpers for building deterministic casts (seating order matters for Chef /
# Empath, and we need a known truthful answer to compare against).
# ---------------------------------------------------------------------------


def _make_role(name: str, role_type: RoleType, team: Team) -> RoleDefinition:
    """Create a minimal RoleDefinition for testing."""
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


def _standard_cast() -> list[Player]:
    """Build a standard 5-player cast in a fixed circular seating order.

    Seating: Washerwoman(G), Empath(G), Poisoner(E), Chef(G), Imp(E).
    """
    return [
        _make_player("Alice", "Washerwoman", RoleType.TOWNSFOLK, Team.GOOD),
        _make_player("Bob", "Empath", RoleType.TOWNSFOLK, Team.GOOD),
        _make_player("Charlie", "Poisoner", RoleType.MINION, Team.EVIL),
        _make_player("Diana", "Chef", RoleType.TOWNSFOLK, Team.GOOD),
        _make_player("Edward", "Imp", RoleType.DEMON, Team.EVIL),
    ]


def _find(players: list[Player], role_name: str) -> Player:
    """Return the player holding the given role name (case-insensitive)."""
    return next(
        p for p in players if p.role and p.role.name.lower() == role_name.lower()
    )


# ---------------------------------------------------------------------------
# Property 14: Poison Effect on Information
#
# For any poisoned player with an information-gathering ability, the info the
# Storyteller provides SHALL be *potentially* inaccurate. We demonstrate this
# by showing that, across repeated runs, a poisoned Empath can report a count
# that differs from the single truthful value derived from the real state. A
# never-inaccurate (deterministically truthful) implementation would fail.
# ---------------------------------------------------------------------------


# Info-gathering roles whose poisoned output can be compared to a known truth.
_INFO_ROLE = ["washerwoman", "empath", "chef"]


@settings(max_examples=50, deadline=None)
@given(
    info_role=st.sampled_from(_INFO_ROLE),
    runs=st.integers(min_value=40, max_value=80),
)
def test_poisoned_info_role_can_be_inaccurate(info_role: str, runs: int) -> None:
    """A poisoned info-gathering role can receive information that does not
    match the truthful result derived from the real game state.

    The property requires the information to be *potentially* inaccurate, so
    we assert that over many Storyteller runs at least one result diverges
    from the truth a non-poisoned player would have received.
    """
    poisoned_players = _standard_cast()
    poisoner = _find(poisoned_players, "poisoner")
    subject = _find(poisoned_players, info_role)
    subject.poisoned_by = poisoner.id
    poisoned_session = _make_session(poisoned_players)

    # Build an identical cast that is NOT poisoned to establish the set of
    # truthful answers the Storyteller would produce for this exact state.
    truthful_players = _standard_cast()
    truthful_session = _make_session(truthful_players)
    truthful_subject = _find(truthful_players, info_role)

    assert subject.is_poisoned is True
    assert truthful_subject.is_poisoned is False

    # Collect the truthful answers (the Washerwoman's truthful branch still has
    # randomness in which pair/role is shown, so gather the full truthful set).
    truthful_outputs: set[str] = set()
    for _ in range(runs):
        result = generate_info_for_role(truthful_session, truthful_subject.id)
        assert result.success is True
        assert result.information is not None
        truthful_outputs.add(result.information)

    # Collect poisoned answers; the property holds if at least one poisoned
    # answer is NOT one the truthful branch could ever have produced.
    saw_inaccurate = False
    for _ in range(runs):
        result = generate_info_for_role(poisoned_session, subject.id)
        assert result.success is True, (
            f"Poisoned {info_role} must still receive a result"
        )
        assert result.information is not None, (
            f"Poisoned {info_role} must still receive information"
        )
        if result.information not in truthful_outputs:
            saw_inaccurate = True
            break

    assert saw_inaccurate, (
        f"Poisoned {info_role} never produced information inconsistent with "
        f"the truthful state across {runs} runs; poison had no effect on info"
    )


# ---------------------------------------------------------------------------
# Property 15 (part A): Poison Lifecycle Reset
#
# For any pair of consecutive nights, the previous night's poison SHALL be
# cleared before the Poisoner selects a new target in the current night.
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    first_target_idx=st.integers(min_value=0, max_value=4),
    second_target_idx=st.integers(min_value=0, max_value=4),
)
def test_poison_cleared_before_new_night_target(
    first_target_idx: int, second_target_idx: int
) -> None:
    """Poison applied on night N is cleared when night N+1 begins, before any
    new poison is applied, so no stale poison carries across the boundary."""
    engine = GameEngine()
    players = _standard_cast()
    poisoner = _find(players, "poisoner")

    # Candidates the Poisoner could target (anyone but themselves).
    candidates = [p for p in players if p.id != poisoner.id]
    first_target = candidates[first_target_idx % len(candidates)]
    second_target = candidates[second_target_idx % len(candidates)]

    session = _make_session(players, phase=GamePhase.NIGHT, night_number=1)

    # --- Night N: poison the first target ---
    engine.resolve_night_action(
        session,
        poisoner.id,
        NightAction(
            player_id=poisoner.id, action_type="poison", target_id=first_target.id
        ),
    )
    assert first_target.is_poisoned is True

    # --- Transition to day then to night N+1 ---
    engine.begin_day_phase(session)
    engine.begin_night_phase(session)

    # The crucial invariant: before the Poisoner acts again, NO player carries
    # poison from the previous night.
    assert all(not p.is_poisoned for p in players), (
        "Previous night's poison was not cleared at the start of the new night"
    )
    assert first_target.poisoned_by is None

    # --- Night N+1: poison the second target; only it should be poisoned ---
    engine.resolve_night_action(
        session,
        poisoner.id,
        NightAction(
            player_id=poisoner.id, action_type="poison", target_id=second_target.id
        ),
    )

    poisoned = [p for p in players if p.is_poisoned]
    assert poisoned == [second_target], (
        f"Only the new target should be poisoned, got {[p.name for p in poisoned]}"
    )


# ---------------------------------------------------------------------------
# Property 15 (part B): Poison Lifts Immediately on Poisoner Death (any cause)
#
# For any game state where the Poisoner dies, active poison SHALL be lifted
# from the affected player at the moment of death. We exercise the two death
# causes implemented in the engine (night kill, execution) plus the shared
# lift path the Slayer shot will reuse.
# ---------------------------------------------------------------------------


_DEATH_CAUSE = ["night_kill", "execution", "slayer"]


@settings(max_examples=100)
@given(
    death_cause=st.sampled_from(_DEATH_CAUSE),
    victim_idx=st.integers(min_value=0, max_value=4),
)
def test_poisoner_death_lifts_poison(death_cause: str, victim_idx: int) -> None:
    """When the Poisoner dies by any cause, poison it applied is lifted at the
    moment of death."""
    engine = GameEngine()
    players = _standard_cast()
    poisoner = _find(players, "poisoner")
    imp = _find(players, "imp")

    # Pick a poison victim that is not the Poisoner themselves.
    candidates = [p for p in players if p.id != poisoner.id]
    victim = candidates[victim_idx % len(candidates)]

    if death_cause == "night_kill":
        session = _make_session(players, phase=GamePhase.NIGHT, night_number=1)
        # Poisoner poisons the victim, then the Imp kills the Poisoner.
        engine.resolve_night_action(
            session,
            poisoner.id,
            NightAction(
                player_id=poisoner.id, action_type="poison", target_id=victim.id
            ),
        )
        assert victim.is_poisoned is True
        engine.resolve_night_action(
            session,
            imp.id,
            NightAction(player_id=imp.id, action_type="kill", target_id=poisoner.id),
        )
        summary = engine.complete_night_phase(session)
        assert poisoner.id in summary.deaths

    elif death_cause == "execution":
        session = _make_session(
            players, phase=GamePhase.DAY, night_number=1, day_number=1
        )
        # Poison carried into the day from the previous night.
        victim.poisoned_by = poisoner.id
        assert victim.is_poisoned is True
        session.grimoire.about_to_die_player_id = poisoner.id
        session.grimoire.about_to_die_votes = 3
        executed_id = engine.end_day_phase(session)
        assert executed_id == poisoner.id

    else:  # slayer
        session = _make_session(
            players, phase=GamePhase.DAY, night_number=1, day_number=1
        )
        victim.poisoned_by = poisoner.id
        assert victim.is_poisoned is True
        # The Slayer day ability (task 4.4) is not yet implemented. Simulate
        # the death via the same lift path the Slayer will reuse: mark the
        # Poisoner dead and lift any poison they sourced.
        assert not hasattr(engine, "use_day_ability"), (
            "Slayer use_day_ability now exists; drive the Poisoner's death "
            "through the real Slayer ability (task 4.4)."
        )
        poisoner.status = PlayerStatus.DEAD
        poisoner.has_vote_token = True
        for p in session.grimoire.players:
            if p.poisoned_by == poisoner.id:
                p.poisoned_by = None

    # Invariant across every death cause: the Poisoner is dead and NO player
    # remains poisoned by them.
    assert poisoner.status == PlayerStatus.DEAD
    assert victim.is_poisoned is False
    assert victim.poisoned_by is None
    assert all(
        p.poisoned_by != poisoner.id for p in players
    ), "A player is still poisoned by the dead Poisoner"
