"""Dual immutable chain: chain A stays; chain B records precedent."""

from __future__ import annotations

from typing import Any, Mapping

from azieltether.constants import GENESIS_PREV_HASH, PRECEDENT_SCOPE, PRODUCT
from azieltether.crypto import canonical_json


def bodies_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    from azieltether.chain import signing_body

    return canonical_json(signing_body(left)) == canonical_json(signing_body(right))


def classify_conflict(
    existing: list[Mapping[str, Any]],
    incoming: Mapping[str, Any],
) -> str | None:
    """Return a conflict kind, or None if the batch belongs on chain A."""
    digest = incoming.get("hash")
    for item in existing:
        if item.get("hash") == digest:
            if bodies_equal(item, incoming):
                return None  # true duplicate — idempotent sync, not a merge-as-nothing
            return "same_hash_collision"
    if not existing:
        return None
    tip = existing[-1]
    prev = incoming.get("prev_hash")
    known = {item.get("hash") for item in existing}
    parent_of_tip = tip.get("prev_hash")
    if prev == tip.get("hash"):
        return None
    if prev in known or prev == parent_of_tip or prev == GENESIS_PREV_HASH:
        return "fork"
    return "unlinked"


def lattice_identity_conflict(
    existing_anchors: list[Mapping[str, Any]],
    incoming: Mapping[str, Any],
) -> bool:
    """Two node_ids claiming the same product tip_hash — accidental identity."""
    if incoming.get("scope") != "lattice":
        return False
    payload = incoming.get("payload") or {}
    product = payload.get("product")
    tip = payload.get("tip_hash")
    node_id = incoming.get("node_id") or payload.get("node_id")
    if not product or not tip:
        return False
    for item in existing_anchors:
        other = item.get("payload") or {}
        if other.get("product") == product and other.get("tip_hash") == tip:
            other_node = item.get("node_id") or other.get("node_id")
            if other_node and node_id and other_node != node_id:
                return True
    return False


def precedent_payload(
    *,
    kind: str,
    scope_a: str,
    existing: Mapping[str, Any] | None,
    incoming: Mapping[str, Any],
    observed_by: list[Mapping[str, Any]],
    chain_a_tip: str | None,
) -> dict[str, Any]:
    parent_tips = []
    if existing and existing.get("hash"):
        parent_tips.append(existing["hash"])
    if incoming.get("hash") and incoming.get("hash") not in parent_tips:
        parent_tips.append(incoming["hash"])
    return {
        "conflict_kind": kind,
        "scope_a": scope_a,
        "parent_tips": parent_tips,
        "shared_prev": incoming.get("prev_hash"),
        "existing_hash": (existing or {}).get("hash"),
        "incoming_hash": incoming.get("hash"),
        "incoming_node_id": incoming.get("node_id"),
        "existing_node_id": (existing or {}).get("node_id"),
        "observed_by": [dict(item) for item in observed_by],
        "chain_a_tip": chain_a_tip,
        "tether_link": chain_a_tip,
        "product": PRODUCT,
        "note": (
            "Chain B / precedent chain. Append-only. Chain A was not rewritten. "
            "This receipt sets precedent for conflict resolution going forward."
        ),
    }


def conflict_status(store: Any) -> dict[str, Any]:
    receipts = store.load_batches(PRECEDENT_SCOPE)
    kinds: dict[str, int] = {}
    for item in receipts:
        kind = str((item.get("payload") or {}).get("conflict_kind") or "unknown")
        kinds[kind] = kinds.get(kind, 0) + 1
    return {
        "ok": True,
        "product": PRODUCT,
        "chain_a_rewritten": False,
        "precedent_length": len(receipts),
        "conflicts": kinds,
        "receipts": [
            {
                "hash": item.get("hash"),
                "kind": (item.get("payload") or {}).get("conflict_kind"),
                "scope_a": (item.get("payload") or {}).get("scope_a"),
                "parent_tips": (item.get("payload") or {}).get("parent_tips"),
                "chain_a_tip": (item.get("payload") or {}).get("chain_a_tip"),
                "observed_by": (item.get("payload") or {}).get("observed_by"),
            }
            for item in receipts
        ],
        "note": (
            "If two online users converge on the same hash-chain tip, AzielTether "
            "does not silently merge. Chain B records both parent tips and sets "
            "precedent. Chain A stays append-only as it was."
        ),
    }
