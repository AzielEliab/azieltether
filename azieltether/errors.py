"""AzielTether errors."""

from __future__ import annotations


class AzielTetherError(Exception):
    """Base error for AzielTether."""


class AppendOnlyError(AzielTetherError):
    """Raised on any attempt to edit, pop, replace, or delete a chained item."""


class ItemError(AzielTetherError):
    """Raised when an item field is invalid."""


class ChainError(AzielTetherError):
    """Raised for chain-level problems (missing genesis, broken link)."""


class ProtocolError(AzielTetherError):
    """Raised when prefer-central / peer-sync / reconcile cannot proceed."""
