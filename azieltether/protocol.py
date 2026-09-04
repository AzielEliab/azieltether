"""Prefer-central / peer-sync-when-down / reconcile-on-restore.

The tether lives in the downloaded software. godlock.uk stays mesh-free.

Author: Aziel Eliab.
"""

from __future__ import annotations

import os
from typing import Any

from azieltether.chain import Chain, detect_dual_chain
from azieltether.client import (
    ingest_item,
    peer_exchange,
    post_tip,
    probe_health,
)
from azieltether.item import Item
from azieltether.lattice import bind_surfaces
from azieltether.queues import harvest
from azieltether.store import Store

MODE_PREFER = "prefer-central"
MODE_PEER = "peer-sync-when-down"
MODE_RECONCILE = "reconcile-on-restore"
OFFLINE_ENV = "AZIELTETHER_OFFLINE"

LIMITATION = (
    "THIS IS: a central×decentral node-mesh software tether. Prefer the "
    "Worker when up. Peer-sync hash-chained work when down. Reconcile on "
    "restore. Dual-chain on same-hash conflict. Lattice tips survive "
    "across GodLock, Aziel Digital Library, and product Workers. "
    "THIS IS NOT: a VPN, MirageGrid, a kernel, a truth score, a backdoor, "
    "or a mesh on godlock.uk. Public HTTPS boards stay mesh-free. The "
    "tether lives in the downloaded software. Author Aziel Eliab."
)


def offline_forced() -> bool:
    return os.environ.get(OFFLINE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _unpublished(chain: Chain, acked: set[str]) -> list[dict[str, Any]]:
    return [item.as_dict() for item in chain.items if item.hash not in acked]


def pulse(
    store: Store | None = None,
    *,
    probe: bool = True,
    harvest_siblings: bool = True,
    host: str | None = None,
) -> dict[str, Any]:
    """Prefer central when healthy; otherwise peer-sync when peers exist."""
    st = store or Store()
    node_id = st.node_id()
    if harvest_siblings:
        harvest(st.chain())
    chain = st.chain()
    state = st.state()
    acked = set(state.get("acked_hashes") or [])
    health: dict[str, Any]
    if not probe or offline_forced():
        health = {
            "ok": False,
            "prefer_central": False,
            "reason": "offline_forced" if offline_forced() else "not_probed",
        }
    else:
        health = probe_health(host)
    unpublished = _unpublished(chain, acked)
    ingested: list[dict[str, Any]] = []
    peer_results: list[dict[str, Any]] = []
    mode = MODE_PEER
    if health.get("prefer_central"):
        mode = MODE_PREFER
        for item in unpublished:
            rec = ingest_item(item, host=host)
            ingested.append({"hash": item.get("hash"), "ok": bool(rec.get("ok") or rec.get("accepted"))})
            if rec.get("ok") or rec.get("accepted"):
                acked.add(str(item.get("hash")))
    else:
        for peer in st.peers():
            rec = peer_exchange(
                peer,
                items=unpublished or [i.as_dict() for i in chain.items],
                node_id=node_id,
                tip_hashes=chain.tip_hashes(),
            )
            peer_results.append(rec)
            incoming = rec.get("items") or rec.get("missing") or []
            if isinstance(incoming, list) and incoming:
                chain.merge(incoming)
    chain = st.chain()
    tips = bind_surfaces(chain, node_id=node_id)
    st.write_tips(tips)
    state.update(
        {
            "mode": mode,
            "last_central_ok": bool(health.get("prefer_central")),
            "acked_hashes": sorted(acked),
            "limitation": LIMITATION,
        }
    )
    st.write_state(state)
    forks = detect_dual_chain(chain.items)
    return {
        "ok": True,
        "product": "azieltether",
        "author": "Aziel Eliab",
        "version": "0.1.0",
        "mode": mode,
        "node_id": node_id,
        "central": health,
        "unpublished": len(unpublished),
        "ingested": ingested,
        "peers": peer_results,
        "items": len(chain),
        "tip_hashes": chain.tip_hashes(),
        "dual_chain": [
            {"prev_hash": f.prev_hash, "child_hashes": list(f.child_hashes)} for f in forks
        ],
        "tips": tips,
        "limitation": LIMITATION,
        "vpn": False,
        "miragegrid": False,
        "mesh_on_public_boards": False,
    }


def reconcile(
    store: Store | None = None,
    *,
    incoming: list[dict[str, Any]] | None = None,
    host: str | None = None,
    probe: bool = True,
) -> dict[str, Any]:
    """Merge incoming items, keep dual-chain forks, push to central if up."""
    st = store or Store()
    node_id = st.node_id()
    chain = st.chain()
    merged = chain.merge(incoming or [])
    chain = st.chain()
    health = probe_health(host) if probe and not offline_forced() else {
        "ok": False,
        "prefer_central": False,
        "reason": "not_probed",
    }
    pushed: list[dict[str, Any]] = []
    state = st.state()
    acked = set(state.get("acked_hashes") or [])
    if health.get("prefer_central"):
        for item in chain.items:
            if item.hash in acked:
                continue
            rec = ingest_item(item.as_dict(), host=host)
            pushed.append({"hash": item.hash, "ok": bool(rec.get("ok") or rec.get("accepted"))})
            if rec.get("ok") or rec.get("accepted"):
                acked.add(item.hash)
        tip = bind_surfaces(chain, node_id=node_id)
        post_tip(tip["surfaces"].get("worker") or {}, host=host)
    else:
        tip = bind_surfaces(chain, node_id=node_id)
    st.write_tips(tip)
    state.update(
        {
            "mode": MODE_RECONCILE if health.get("prefer_central") else MODE_PEER,
            "last_central_ok": bool(health.get("prefer_central")),
            "acked_hashes": sorted(acked),
            "limitation": LIMITATION,
        }
    )
    st.write_state(state)
    return {
        "ok": True,
        "product": "azieltether",
        "author": "Aziel Eliab",
        "version": "0.1.0",
        "mode": state["mode"],
        "node_id": node_id,
        "central": health,
        "merge": merged,
        "pushed": pushed,
        "tip_hashes": chain.tip_hashes(),
        "dual_chain": merged.get("dual_chain") or [],
        "tips": tip,
        "limitation": LIMITATION,
        "vpn": False,
        "miragegrid": False,
        "mesh_on_public_boards": False,
    }


def dual_chain_report(store: Store | None = None) -> dict[str, Any]:
    st = store or Store()
    chain = st.chain()
    forks = detect_dual_chain(chain.items)
    return {
        "ok": True,
        "product": "azieltether",
        "author": "Aziel Eliab",
        "items": len(chain),
        "forks": [
            {"prev_hash": f.prev_hash, "child_hashes": list(f.child_hashes)} for f in forks
        ],
        "winner": None,
        "note": "Dual-chain keeps both children of the same prev_hash. No winner.",
        "limitation": LIMITATION,
    }


def accept_peer(store: Store, body: dict[str, Any]) -> dict[str, Any]:
    """Peer handshake: merge offered items, return items the peer may lack."""
    chain = store.chain()
    offered = body.get("items") if isinstance(body, dict) else None
    incoming = offered if isinstance(offered, list) else []
    merged = chain.merge(incoming)
    known = chain.hashes()
    their_tips = body.get("tip_hashes") if isinstance(body, dict) else []
    missing_here = [h for h in (their_tips or []) if h not in known]
    # Offer our items they did not send (by hash).
    offered_hashes = set()
    for raw in incoming:
        if isinstance(raw, dict) and raw.get("hash"):
            offered_hashes.add(str(raw["hash"]))
    offer = [item.as_dict() for item in store.chain().items if item.hash not in offered_hashes]
    return {
        "ok": True,
        "product": "azieltether",
        "author": "Aziel Eliab",
        "node_id": store.node_id(),
        "merge": merged,
        "items": offer,
        "tip_hashes": store.chain().tip_hashes(),
        "missing_tips": missing_here,
        "limitation": LIMITATION,
        "vpn": False,
    }
