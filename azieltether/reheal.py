"""REHEAL — heal from own last good tip; never a neighbor vote-to-fix.

A node reheals from its own last verified tip, then either a verified
trusted pull (cite + lockset, hash-absolute) or phoenix-WAIT. Neighbors
cannot vote a fix. Allowed chatter is live / locked / isolated /
tip-hash only (SPLIT THE WIRES tick plane).

Author: Aziel Eliab only.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from azieltether.canon import GENESIS_PREV_HASH, require_hex64
from azieltether.errors import RehealError
from azieltether.survival import item_digest_ok
from azieltether.wires import WIRES_SPEC, cite_ok, hash_holds, phoenix_allowed

REHEAL_SPEC = "REHEAL-1.0"
REHEAL_AUTHOR = "Aziel Eliab"
NEIGHBOR_VOTE_TO_FIX = False
ALLOWED_CHATTER = ("live", "locked", "isolated", "tip_hash")
PHOENIX_WAIT = "phoenix-WAIT"

LAW = (
    "REHEAL. Heal from your own last good tip plus a verified trusted "
    "pull, or phoenix-WAIT. No neighbor vote-to-fix. Allowed chatter is "
    "live / locked / isolated / tip-hash only. Author: Aziel Eliab only."
)

def last_good_tip(items: Sequence[Mapping[str, Any]]) -> str | None:
    """Longest verified prefix tip. Stop at the first broken hash."""
    known: set[str] = set()
    last: str | None = None
    for raw in items:
        data = raw if isinstance(raw, Mapping) else {}
        digest = str(data.get("hash") or "")
        prev = str(data.get("prev_hash") or "")
        if not digest or not item_digest_ok(data):
            break
        if prev != GENESIS_PREV_HASH and prev not in known:
            break
        known.add(digest)
        last = digest
    return last


def chatter_allowed(body: Mapping[str, Any] | None) -> bool:
    if not isinstance(body, Mapping):
        return True
    for key in body:
        name = "tip_hash" if str(key) in {"tip_hash", "tip-hash"} else str(key)
        if name not in ALLOWED_CHATTER:
            return False
    return True


def filter_chatter(body: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(body, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, value in body.items():
        name = "tip_hash" if str(key) in {"tip_hash", "tip-hash"} else str(key)
        if name in ALLOWED_CHATTER:
            out[name] = value
    return out


def refuse_vote_to_fix(votes_for: int = 0, neighbor_fix: Any = None) -> dict[str, Any]:
    """Neighbors cannot vote a broken or missing tip back to health."""
    if NEIGHBOR_VOTE_TO_FIX:
        return {"ok": True, "code": "REHEAL-VOTE-OK", "author": REHEAL_AUTHOR}
    if votes_for or neighbor_fix:
        return {
            "ok": False,
            "code": "REHEAL-VOTE-REFUSED",
            "applied": False,
            "wait": PHOENIX_WAIT,
            "note": "No neighbor vote-to-fix. Heal from own tip + trusted pull or phoenix-WAIT.",
            "author": REHEAL_AUTHOR,
        }
    return {"ok": True, "code": "REHEAL-NO-VOTE", "author": REHEAL_AUTHOR}


def trusted_pull_ok(
    *,
    own_tip: str | None,
    cite: str | None,
    lockset: str | None,
    digest_ok: bool,
    votes_for: int = 0,
) -> bool:
    if not own_tip or not cite_ok(cite, lockset):
        return False
    try:
        if require_hex64("cite", cite) != require_hex64("own_tip", own_tip):
            return False
    except ValueError:
        return False
    return hash_holds(digest_ok=digest_ok, votes_for=votes_for)


def decide(
    *,
    own_tip: str | None,
    cite: str | None = None,
    lockset: str | None = None,
    digest_ok: bool = False,
    votes_for: int = 0,
    neighbor_fix: Any = None,
    actor_node_id: str = "",
    failed_node_id: str = "",
    chatter: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Own last good tip + trusted pull, else phoenix-WAIT."""
    if chatter is not None and not chatter_allowed(chatter):
        raise RehealError("allowed chatter is live/locked/isolated/tip-hash only")
    vote = refuse_vote_to_fix(votes_for, neighbor_fix)
    if not vote.get("ok"):
        return vote
    if trusted_pull_ok(
        own_tip=own_tip,
        cite=cite,
        lockset=lockset,
        digest_ok=digest_ok,
        votes_for=0,
    ):
        return {
            "ok": True,
            "code": "REHEAL-TRUSTED-PULL",
            "applied": True,
            "own_tip": own_tip,
            "cite": cite,
            "wait": False,
            "author": REHEAL_AUTHOR,
        }
    local_phoenix = phoenix_allowed(
        failed_node_id=failed_node_id or actor_node_id,
        actor_node_id=actor_node_id,
    )
    return {
        "ok": True,
        "code": "REHEAL-PHOENIX-WAIT" if (own_tip or local_phoenix) else "REHEAL-WAIT",
        "applied": False,
        "own_tip": own_tip,
        "wait": PHOENIX_WAIT,
        "phoenix_local": local_phoenix,
        "note": "Stay on own last good tip. phoenix-WAIT. No neighbor vote-to-fix.",
        "author": REHEAL_AUTHOR,
    }


def law_card() -> dict[str, Any]:
    return {
        "ok": True,
        "spec": REHEAL_SPEC,
        "wires_spec": WIRES_SPEC,
        "product": "azieltether",
        "author": REHEAL_AUTHOR,
        "identity": REHEAL_AUTHOR,
        "neighbor_vote_to_fix": NEIGHBOR_VOTE_TO_FIX,
        "allowed_chatter": list(ALLOWED_CHATTER),
        "phoenix": PHOENIX_WAIT,
        "law": LAW,
    }
