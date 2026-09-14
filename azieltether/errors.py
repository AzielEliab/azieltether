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


class WiresError(ProtocolError):
    """SPLIT THE WIRES refused a tick, cite, socket, or apply."""


class SurvivalError(ProtocolError):
    """COLD-COPY SURVIVAL refused live sync, poison, or a free tip erase."""


class RehealError(ProtocolError):
    """REHEAL refused a neighbor vote-to-fix or illegal chatter."""


class ShelfError(ProtocolError):
    """COLD-SHELF-TETHER refused mismatch, rewrite, lie, DOI invent, attest, or a MOCK slot."""
