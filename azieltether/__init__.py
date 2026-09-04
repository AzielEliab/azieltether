"""AzielTether: central × decentral node-mesh software tether.

Prefer the central Worker when it is up. When it is down, downloaded
nodes sync hash-chained work with each other when they hit the internet,
then reconcile back to central on restore. Dual-chain on same-hash
conflict. Hash lattice tips survive across GodLock, Aziel Digital
Library, and product Workers.

Author: Aziel Eliab.

THIS IS NOT: a VPN, MirageGrid, a kernel, a truth score, or a mesh on
godlock.uk. Public HTTPS boards stay mesh-free. The tether lives in the
downloaded software.
"""

from __future__ import annotations

from azieltether.chain import Chain, DualFork, VerifyResult, detect_dual_chain
from azieltether.errors import (
    AppendOnlyError,
    AzielTetherError,
    ChainError,
    ItemError,
    ProtocolError,
)
from azieltether.item import GENESIS_PREV_HASH, Item, digest_item
from azieltether.lattice import SURFACES, LatticeTip, tip_from_chain
from azieltether.protocol import MODE_PEER, MODE_PREFER, MODE_RECONCILE, pulse, reconcile

__version__ = "0.1.0"
__author__ = "Aziel Eliab"
__all__ = [
    "AppendOnlyError",
    "AzielTetherError",
    "Chain",
    "ChainError",
    "DualFork",
    "GENESIS_PREV_HASH",
    "Item",
    "ItemError",
    "LatticeTip",
    "MODE_PEER",
    "MODE_PREFER",
    "MODE_RECONCILE",
    "ProtocolError",
    "SURFACES",
    "VerifyResult",
    "detect_dual_chain",
    "digest_item",
    "pulse",
    "reconcile",
    "tip_from_chain",
    "__author__",
    "__version__",
]
