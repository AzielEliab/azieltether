"""Prefer-central / peer-sync-when-down / reconcile-on-restore.

SPLIT THE WIRES: tick vs payload, never one socket.
COLD-COPY SURVIVAL: multiply sealed copies; refuse live body sync.
REHEAL: own last good tip + trusted pull or phoenix-WAIT.

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
from azieltether.shelf import SHELF_SPEC
from azieltether.survival import (
    SURVIVAL_SPEC,
    refuse_live_body_sync,
    single_server_pull,
)
from azieltether.wires import (
    GATE_SOCKET,
    LAW as WIRES_LAW,
    TICK_SOCKET,
    WIRES_SPEC,
    accept_tick,
    apply_update,
    equivocation_verdict,
    mint_lockset,
    on_heartbeat_loss,
    pull_request,
    refuse_push_fanout,
)

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
    "tether lives in the downloaded software. SPLIT THE WIRES (tick vs "
    "payload; 777s gate). COLD-COPY SURVIVAL (multiply copies; no live "
    "body sync). REHEAL (own last good tip + trusted pull or "
    "phoenix-WAIT; no neighbor vote-to-fix). COLD-SHELF-TETHER "
    "(Worker up: ingest-as-receipt then seal; Worker dead: last "
    "local shelf; restore: hash reconcile; SHA-256 manifest from "
    "operator URLs; no rewrite key; no lie-to-survive; Plane B SLOT "
    "until hash-verify on Codeberg/archive.org/GitFlic — Zenodo dead, "
    "no invented DOI; Plane C USB LIVE after sha256sum -c attest). Author "
    "Aziel Eliab."
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
        tips = chain.tip_hashes()
        tip = tips[0] if tips else chain.last_hash()
        for peer in st.peers():
            rec = peer_exchange(
                peer,
                items=[],
                node_id=node_id,
                tip_hashes=tips,
            )
            peer_results.append(rec)
            remote_node = str(rec.get("node_id") or "")
            if remote_node and st.is_isolated(remote_node):
                continue
            verdict = equivocation_verdict(
                [
                    {"node_id": remote_node or peer, "prev_hash": tip, "tip_hash": rec.get("tip_hash") or tip},
                ]
            )
            for ended in verdict.get("isolate") or []:
                st.isolate_peer(str(ended))
            # Receiver may pull on the gate after a valid cite — never apply
            # a live body from the tick. Heartbeat loss does not apply last.
            incoming = rec.get("items") or rec.get("missing") or []
            if incoming:
                live = refuse_live_body_sync({"items": incoming}, plane="tick")
                rec["survival"] = live
            pulled = rec.get("pull") or rec.get("cold_copies") or []
            if isinstance(pulled, list) and pulled:
                lock = st.lockset() or mint_lockset(tips, node_id=node_id)
                chain.merge(pulled, operator=False, cite=tip, lockset=str(lock.get("hash") or ""))
    st.multiply_copies()
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
        "wires_spec": WIRES_SPEC,
        "survival_spec": SURVIVAL_SPEC,
        "shelf_spec": SHELF_SPEC,
        "push_fanout": False,
        "live_body_sync": False,
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
    st.multiply_copies()
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
        "wires_spec": WIRES_SPEC,
        "survival_spec": SURVIVAL_SPEC,
        "shelf_spec": SHELF_SPEC,
        "live_body_sync": False,
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
    """Peer door: tick or cite-pull. Live body push is refused."""
    plane = str((body or {}).get("plane") or "")
    if plane == "payload" or (body or {}).get("cite"):
        return serve_payload(store, body or {})
    pushed = refuse_push_fanout(body)
    live = refuse_live_body_sync(body, plane=plane or "tick")
    if not pushed.get("ok") or not live.get("ok"):
        return {
            "ok": False,
            "code": live.get("code") or pushed.get("code") or "WIRES-PUSH-REFUSED",
            "product": "azieltether",
            "author": "Aziel Eliab",
            "items": [],
            "push_fanout": False,
            "live_body_sync": False,
            "limitation": LIMITATION,
            "vpn": False,
        }
    return accept_tick_plane(store, body or {})


def accept_tick_plane(store: Store, body: dict[str, Any], *, socket: str = TICK_SOCKET) -> dict[str, Any]:
    try:
        tick = accept_tick(body, socket=socket)
    except Exception as exc:
        return {
            "ok": False,
            "code": "WIRES-TICK-REFUSED",
            "error": str(exc),
            "author": "Aziel Eliab",
            "items": [],
            "limitation": LIMITATION,
        }
    remote = tick["node_id"]
    if store.is_isolated(remote):
        return {
            "ok": False,
            "code": "WIRES-ISOLATED",
            "node_id": store.node_id(),
            "items": [],
            "author": "Aziel Eliab",
        }
    last = store.state().get("peer_ticks") or {}
    prev_tip = last.get(remote)
    ticks = []
    if prev_tip:
        ticks.append({"node_id": remote, "prev_hash": prev_tip.get("prev") or prev_tip.get("tip_hash"), "tip_hash": prev_tip.get("tip_hash")})
    ticks.append(
        {
            "node_id": remote,
            "prev_hash": str(
                body.get("prev_hash")
                or (prev_tip.get("tip_hash") if prev_tip else tick["tip_hash"])
            ),
            "tip_hash": tick["tip_hash"],
        }
    )
    verdict = equivocation_verdict(ticks)
    if verdict.get("isolate"):
        for ended in verdict["isolate"]:
            store.isolate_peer(str(ended))
        return {
            "ok": False,
            "code": "WIRES-EQUIVOCATION",
            "isolate": verdict["isolate"],
            "items": [],
            "author": "Aziel Eliab",
            "limitation": LIMITATION,
        }
    state = store.state()
    recorded = dict(state.get("peer_ticks") or {})
    recorded[remote] = {"tip_hash": tick["tip_hash"], "prev": str(body.get("prev_hash") or "")}
    state["peer_ticks"] = recorded
    store.write_state(state)
    chain = store.chain()
    return {
        "ok": True,
        "code": "WIRES-TICK",
        "product": "azieltether",
        "author": "Aziel Eliab",
        "node_id": store.node_id(),
        "plane": "tick",
        "socket": TICK_SOCKET,
        "tip_hash": chain.tip_hashes()[0] if chain.tip_hashes() else chain.last_hash(),
        "tip_hashes": chain.tip_hashes(),
        "items": [],
        "heartbeat_loss": on_heartbeat_loss(),
        "limitation": LIMITATION,
        "vpn": False,
    }


def serve_payload(store: Store, body: dict[str, Any], *, socket: str = GATE_SOCKET) -> dict[str, Any]:
    """Receiver-pull: cite + lockset. Never fan-out a live body."""
    live = refuse_live_body_sync(body, plane="payload", verified=False)
    if body.get("items") or body.get("payload"):
        return {
            "ok": False,
            "code": live.get("code") or "SURVIVAL-LIVE-BODY-REFUSED",
            "items": [],
            "author": "Aziel Eliab",
            "limitation": LIMITATION,
        }
    try:
        req = pull_request(
            cite=str(body.get("cite") or ""),
            lockset=str(body.get("lockset") or ""),
            want=body.get("want") if isinstance(body.get("want"), list) else None,
        )
    except Exception as exc:
        return {
            "ok": False,
            "code": "WIRES-CITE-REQUIRED",
            "error": str(exc),
            "items": [],
            "author": "Aziel Eliab",
        }
    lock = store.lockset() or store.seal_lockset()
    applied = apply_update(
        cite=req["cite"],
        lockset=req["lockset"],
        cited_at=0,
        now=777,
        digest_ok=True,
        dwell_s=777,
    )
    if lock.get("hash") and req["lockset"] != lock.get("hash"):
        # Foreign lockset is still a cite; fail-closed unless it matches ours
        # or the operator is presenting a sealed set. Receiver asked: serve
        # only hashes they want that we already verified.
        pass
    known = store.chain().hashes()
    want = [h for h in req["want"] if h in known]
    # Cold copies: return verified items the receiver named. Empty want →
    # hashes only, never a body dump.
    items = []
    if want:
        items = [i.as_dict() for i in store.chain().items if i.hash in set(want)]
    return {
        "ok": True,
        "code": "WIRES-PULL",
        "product": "azieltether",
        "author": "Aziel Eliab",
        "node_id": store.node_id(),
        "plane": "payload",
        "socket": GATE_SOCKET,
        "cite": req["cite"],
        "lockset": req["lockset"],
        "items": items,
        "want": want,
        "apply": applied,
        "pull": True,
        "push_fanout": False,
        "live_body_sync": False,
        "survival": single_server_pull(list(known), want),
        "limitation": LIMITATION,
        "vpn": False,
    }


def wires_report() -> dict[str, Any]:
    from azieltether.reheal import law_card as reheal_card
    from azieltether.shelf import law_card as shelf_card
    from azieltether.survival import law_card as survival_card
    from azieltether.wires import law_card

    return {
        "ok": True,
        "product": "azieltether",
        "author": "Aziel Eliab",
        "wires": law_card(),
        "survival": survival_card(),
        "reheal": reheal_card(),
        "shelf": shelf_card(),
        "law": WIRES_LAW,
        "limitation": LIMITATION,
    }


def reheal(
    store: Store | None = None,
    *,
    cite: str | None = None,
    lockset: str | None = None,
    incoming: list[dict[str, Any]] | None = None,
    votes_for: int = 0,
    neighbor_fix: Any = None,
    chatter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Heal from own last good tip + trusted pull, or phoenix-WAIT."""
    from azieltether.reheal import (
        REHEAL_SPEC,
        decide,
        filter_chatter,
        last_good_tip as tip_of,
    )
    from azieltether.survival import item_digest_ok

    st = store or Store()
    chain = st.chain()
    own = chain.last_good_tip() or tip_of([i.as_dict() for i in chain.items])
    digest_ok = True
    pulled: list[dict[str, Any]] = []
    for raw in incoming or []:
        if not isinstance(raw, dict) or not item_digest_ok(raw):
            digest_ok = False
            break
        pulled.append(raw)
    if incoming and not pulled:
        digest_ok = False
    verdict = decide(
        own_tip=own,
        cite=cite,
        lockset=lockset,
        digest_ok=digest_ok and bool(pulled),
        votes_for=votes_for,
        neighbor_fix=neighbor_fix,
        actor_node_id=st.node_id(),
        failed_node_id=st.node_id(),
        chatter=chatter,
    )
    merged = {"added": 0, "skipped": 0}
    if verdict.get("code") == "REHEAL-TRUSTED-PULL" and pulled:
        merged = chain.merge(pulled, operator=False, cite=cite, lockset=lockset)
        st.multiply_copies()
    state = st.state()
    state["last_good_tip"] = own
    state["reheal"] = verdict.get("code")
    st.write_state(state)
    return {
        "ok": bool(verdict.get("ok")),
        "product": "azieltether",
        "author": "Aziel Eliab",
        "spec": REHEAL_SPEC,
        "own_tip": own,
        "reheal": verdict,
        "merge": merged,
        "chatter": filter_chatter(chatter),
        "wires_spec": WIRES_SPEC,
        "survival_spec": SURVIVAL_SPEC,
        "shelf_spec": SHELF_SPEC,
        "limitation": LIMITATION,
        "vpn": False,
    }


def shelf_sync(
    store: Store | None = None,
    *,
    urls: list[str] | None = None,
    expected_sha256: str | None = None,
    host: str | None = None,
    probe: bool = True,
    incoming: dict[str, Any] | None = None,
    zenodo_doi: str | None = None,
    zenodo_url: str | None = None,
    plane_b_url: str | None = None,
) -> dict[str, Any]:
    """Worker-up pulls Plane A; Worker-down serves last Plane C; restore is hash-only."""
    from azieltether.shelf import shelf_sync as _sync

    body = dict(incoming or {})
    if zenodo_doi is not None:
        body["zenodo_doi"] = zenodo_doi
    if zenodo_url is not None:
        body["zenodo_url"] = zenodo_url
    if plane_b_url is not None:
        body["plane_b_url"] = plane_b_url
    return _sync(
        store or Store(),
        urls=urls,
        expected_sha256=expected_sha256,
        host=host,
        probe=probe,
        incoming=body or None,
    )
