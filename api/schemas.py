"""API request/response schemas for the Blood on the Clocktower AI game."""

from typing import Optional

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    """Request body for creating a new game session."""

    script_name: str = "trouble_brewing"
    player_count: int = Field(..., ge=5, le=7)
    human_player_name: str


class CreateGameResponse(BaseModel):
    """Response body after creating a new game session."""

    game_id: str
    human_player_id: str
    human_role: str
    human_team: str
    players: list[dict]  # [{id, name, is_human}]


class PlayerActionRequest(BaseModel):
    """Request body for submitting a player action."""

    player_id: str
    action_type: str  # "message", "vote", "nominate", "night_choice", "day_ability"
    content: Optional[str] = None  # For messages
    target_id: Optional[str] = None  # For nominations, night choices, day abilities
    vote: Optional[bool] = None  # For voting


class GameStateResponse(BaseModel):
    """Response body for retrieving current game state."""

    game_id: str
    phase: str
    day_number: int
    players: list[dict]  # [{id, name, status, is_human}]
    human_player: dict  # {id, name, role, team, status, info_received}
    messages: list[dict]
    active_nomination: Optional[dict] = None
    result: Optional[dict] = None


class GameEvent(BaseModel):
    """Model for a real-time game event pushed via SSE."""

    event_type: str  # "phase_change", "message", "nomination", "vote", "death", "game_end"
    data: dict
    timestamp: float


class ScriptSummary(BaseModel):
    """Summary of a script for listing available scripts."""

    name: str
    description: str


class ScriptDetail(BaseModel):
    """Detailed view of a script including its roles grouped by type."""

    name: str
    description: str
    roles: dict[str, list[str]]  # {"townsfolk": [...], "outsiders": [...], "minions": [...], "demons": [...]}
