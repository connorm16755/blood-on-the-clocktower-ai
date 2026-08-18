"""Custom exceptions for the Game Engine module."""


class InvalidPlayerCountError(Exception):
    """Raised when the player count is outside the valid range (5-7)."""


class InvalidPhaseError(Exception):
    """Raised when an action is attempted during an invalid game phase."""
