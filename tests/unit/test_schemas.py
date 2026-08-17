"""Unit tests for API request/response schemas."""

import pytest
from pydantic import ValidationError

from api.schemas import (
    CreateGameRequest,
    CreateGameResponse,
    GameEvent,
    GameStateResponse,
    PlayerActionRequest,
    ScriptDetail,
    ScriptSummary,
)


class TestCreateGameRequest:
    """Tests for CreateGameRequest validation."""

    def test_valid_request_minimum_players(self):
        """Test that a request with 5 players is accepted with defaults."""
        req = CreateGameRequest(player_count=5, human_player_name="Alice")
        assert req.player_count == 5
        assert req.script_name == "trouble_brewing"
        assert req.human_player_name == "Alice"

    def test_valid_request_maximum_players(self):
        """Test that a request with 7 players is accepted."""
        req = CreateGameRequest(player_count=7, human_player_name="Bob")
        assert req.player_count == 7

    def test_valid_request_custom_script(self):
        """Test that a custom script name overrides the default."""
        req = CreateGameRequest(
            script_name="custom_script", player_count=6, human_player_name="Charlie"
        )
        assert req.script_name == "custom_script"

    def test_invalid_player_count_too_low(self):
        """Test that player_count below 5 raises a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CreateGameRequest(player_count=4, human_player_name="Alice")
        assert "greater than or equal to 5" in str(exc_info.value)

    def test_invalid_player_count_too_high(self):
        """Test that player_count above 7 raises a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CreateGameRequest(player_count=8, human_player_name="Alice")
        assert "less than or equal to 7" in str(exc_info.value)

    def test_missing_player_count(self):
        """Test that omitting player_count raises a ValidationError."""
        with pytest.raises(ValidationError):
            CreateGameRequest(human_player_name="Alice")

    def test_missing_human_player_name(self):
        """Test that omitting human_player_name raises a ValidationError."""
        with pytest.raises(ValidationError):
            CreateGameRequest(player_count=5)


class TestCreateGameResponse:
    """Tests for CreateGameResponse model."""

    def test_valid_response(self):
        """Test constructing a valid game creation response."""
        resp = CreateGameResponse(
            game_id="game-123",
            human_player_id="player-1",
            human_role="Washerwoman",
            human_team="good",
            players=[
                {"id": "player-1", "name": "Alice", "is_human": True},
                {"id": "player-2", "name": "Bot1", "is_human": False},
            ],
        )
        assert resp.game_id == "game-123"
        assert len(resp.players) == 2


class TestPlayerActionRequest:
    """Tests for PlayerActionRequest model."""

    def test_message_action(self):
        """Test a message action with content and no target or vote."""
        req = PlayerActionRequest(
            player_id="p1", action_type="message", content="I am the Washerwoman!"
        )
        assert req.content == "I am the Washerwoman!"
        assert req.target_id is None
        assert req.vote is None

    def test_vote_action(self):
        """Test a vote action with a boolean vote value."""
        req = PlayerActionRequest(player_id="p1", action_type="vote", vote=True)
        assert req.vote is True

    def test_nominate_action(self):
        """Test a nominate action with a target_id."""
        req = PlayerActionRequest(
            player_id="p1", action_type="nominate", target_id="p2"
        )
        assert req.target_id == "p2"


class TestGameStateResponse:
    """Tests for GameStateResponse model."""

    def test_valid_state_response(self):
        """Test constructing a valid game state response with optional fields as None."""
        resp = GameStateResponse(
            game_id="game-123",
            phase="day",
            day_number=1,
            players=[
                {"id": "p1", "name": "Alice", "status": "alive", "is_human": True}
            ],
            human_player={
                "id": "p1",
                "name": "Alice",
                "role": "Chef",
                "team": "good",
                "status": "alive",
                "info_received": [],
            },
            messages=[],
        )
        assert resp.phase == "day"
        assert resp.active_nomination is None
        assert resp.result is None


class TestGameEvent:
    """Tests for GameEvent model."""

    def test_valid_event(self):
        """Test constructing a valid SSE game event."""
        event = GameEvent(
            event_type="phase_change",
            data={"new_phase": "night", "day_number": 1},
            timestamp=1700000000.0,
        )
        assert event.event_type == "phase_change"
        assert event.timestamp == 1700000000.0


class TestScriptSummary:
    """Tests for ScriptSummary model."""

    def test_valid_summary(self):
        """Test constructing a valid script summary."""
        summary = ScriptSummary(
            name="Trouble Brewing",
            description="A straightforward Demon-hunt with misinformation tricks.",
        )
        assert summary.name == "Trouble Brewing"
        assert summary.description == "A straightforward Demon-hunt with misinformation tricks."


class TestScriptDetail:
    """Tests for ScriptDetail model."""

    def test_valid_detail(self):
        """Test constructing a valid script detail with roles grouped by type."""
        detail = ScriptDetail(
            name="Trouble Brewing",
            description="A straightforward Demon-hunt with misinformation tricks.",
            roles={
                "townsfolk": [
                    "Washerwoman", "Librarian", "Investigator",
                    "Chef", "Empath", "Slayer",
                ],
                "outsiders": ["Butler"],
                "minions": ["Poisoner"],
                "demons": ["Imp"],
            },
        )
        assert detail.name == "Trouble Brewing"
        assert len(detail.roles["townsfolk"]) == 6
        assert "Imp" in detail.roles["demons"]
