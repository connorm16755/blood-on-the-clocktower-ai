"""Custom exceptions for the Game Engine module."""


class InvalidPlayerCountError(Exception):
    """Raised when the player count is outside the valid range (5-7)."""


class InvalidPhaseError(Exception):
    """Raised when an action is attempted during an invalid game phase."""


class DeadPlayerActionError(Exception):
    """Raised when a dead player attempts an action restricted to living players."""


class InvalidTargetError(Exception):
    """Raised when an action targets an invalid player (e.g., dead target, Butler self-master)."""


class NominationError(Exception):
    """Raised when a nomination is invalid (e.g., already executed today, nomination not found)."""
