"""Custom exceptions for the Role Registry module."""


class RoleDataError(Exception):
    """Raised when a role definition file is malformed or missing required fields."""


class ScriptNotFoundError(Exception):
    """Raised when a requested script cannot be found."""
