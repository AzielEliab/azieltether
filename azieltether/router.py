"""Prefer central. On failure, use peers. Reconcile when central returns."""

from __future__ import annotations

from typing import Any, Iterable

from azieltether.chain import ChainError, verify_batch
from azieltether.constants import (
    MOTTO,
    NOTE_NOT_MESH_WORKER,
    PRODUCT,
    SCOPES,
    VERSION,
    WORK_SCOPES,
)
from azieltether.hooks import on_transfer, transfer_event
from azieltether.store import Store
from azieltether.transport import MemoryTransport, Transport, TransportError


class Router:
    def __init__(
        self,
        store: Store,
        *,
        central: Transport | None = None,
        tether: Transport | None = None,
        peers: list[Transport] | None = None,
    ) -> None:
        self.store = store
        self.central = central
        self.tether = tether
        self.peers = list(peers or [])

    def prefer_central(self) -> bool:
        """True when a product-central or tether bootstrap host is healthy."""
        return self._central_target() is not None

    def route_name(self) -> str:
        if self._alive(self.central):
            return "central"
        if self._alive(self.tether):
            return "tether"
        if any(self._alive(peer) for peer in self.peers):
            return "peer"
        return "local"

    def announce(self) -> dict[str, Any]:
        node = self.store.public_node()
        target = self._central_target()
        if target is not None:
            result = target.announce({**node, "product": PRODUCT})
            self._remember_from(target)
            return {"ok": True, "via": target.name, "route": self.route_name(), "result": result}

        gossiped = []
        errors = []
        for peer in self.peers:
            if not self._alive(peer):
                continue
            try:
                gossiped.append(peer.announce({**node, "product": PRODUCT}))
                self.store.remember_peer({"node_id": getattr(peer, "name", "peer"), "via": peer.name})
            except (TransportError, ChainError) as exc:
                errors.append(str(exc))
        self.store.remember_peer(node)
        return {
            "ok": True,
            "via": "peer" if gossiped else "local",
            "route": self.route_name(),
            "gossiped": len(gossiped),
            "errors": errors,
            "note": "central down; announced via peer gossip or local store",
        }

    def push(self, batch: dict[str, Any]) -> dict[str, Any]:
        verified = verify_batch(batch)
        self.store.accept_batch(verified)
        conflicted = self.store.last_accept == "precedent"
        target = self._central_target()
        offline = target is None and not any(self._alive(peer) for peer in self.peers)
        via = "central" if target is self.central and target is not None else (
            "tether" if target is not None else ("peer" if any(self._alive(p) for p in self.peers) else "local")
        )
        hooks = on_transfer(
            transfer_event(
                direction="upload",
                batch=verified,
                via=via,
                store=self.store,
                offline=offline,
            )
        )
        if conflicted:
            return {
                "ok": True,
                "via": "precedent",
                "route": "precedent",
                "hash": verified["hash"],
                "conflict": True,
                "hooks": hooks,
                "note": "same-hash / fork conflict: chain A unchanged; chain B recorded precedent",
            }
        if target is not None:
            result = target.push_batch(verified)
            self.store.remove_backlog(verified["hash"])
            return {
                "ok": True,
                "via": target.name,
                "route": "central" if target is self.central else "tether",
                "hash": verified["hash"],
                "result": result,
                "hooks": hooks,
            }

        delivered = []
        errors = []
        for peer in self.peers:
            if not self._alive(peer):
                continue
            try:
                delivered.append(peer.push_batch(verified))
            except (TransportError, ChainError) as exc:
                errors.append(str(exc))
        self.store.enqueue_backlog(verified)
        return {
            "ok": bool(delivered) or True,
            "via": "peer" if delivered else "local",
            "route": "peer" if delivered else "local",
            "hash": verified["hash"],
            "delivered": len(delivered),
            "backlog": True,
            "errors": errors,
            "hooks": hooks,
            "note": "central down; batch stored locally and offered to peers",
        }

    def pull(self, *, since: str = "", product: str = "*") -> dict[str, Any]:
        accepted: list[str] = []
        errors: list[str] = []
        sources: list[Transport] = []
        target = self._central_target()
        if target is not None:
            sources.append(target)
        else:
            sources.extend(peer for peer in self.peers if self._alive(peer))
        for source in sources:
            try:
                batches = source.pull_batches(since=since, product=product)
            except TransportError as exc:
                errors.append(str(exc))
                continue
            for raw in batches:
                try:
                    verified = self.store.accept_batch(raw)
                    hooks = on_transfer(
                        transfer_event(
                            direction="download",
                            batch=verified,
                            via=source.name,
                            store=self.store,
                            offline=False,
                        )
                    )
                    if self.store.last_accept == "precedent":
                        errors.append(f"precedent recorded for {verified.get('hash')}")
                        continue
                    accepted.append(verified["hash"])
                    _ = hooks
                except ChainError as exc:
                    errors.append(str(exc))
        self._remember_from(target)
        return {
            "ok": True,
            "via": self.route_name(),
            "accepted": accepted,
            "count": len(accepted),
            "errors": errors,
        }

    def reconcile(self) -> dict[str, Any]:
        target = self._central_target()
        if target is None:
            return {
                "ok": False,
                "via": self.route_name(),
                "reconciled": [],
                "remaining": len(self.store.load_backlog()),
                "note": "central still down; keep the local backlog",
            }
        reconciled = []
        errors = []
        for batch in list(self.store.load_backlog()):
            try:
                verified = verify_batch(batch)
                target.push_batch(verified)
                self.store.remove_backlog(verified["hash"])
                reconciled.append(verified["hash"])
                on_transfer(
                    transfer_event(
                        direction="upload",
                        batch=verified,
                        via=target.name,
                        store=self.store,
                        offline=False,
                    )
                )
            except (TransportError, ChainError) as exc:
                errors.append(str(exc))
        return {
            "ok": True,
            "via": target.name,
            "reconciled": reconciled,
            "count": len(reconciled),
            "remaining": len(self.store.load_backlog()),
            "errors": errors,
            "note": "local backlog pushed to central after restore",
        }

    def doctor(self, *, public_sites: dict[str, bool] | None = None) -> dict[str, Any]:
        status = self.store.status()
        central_up = self._alive(self.central)
        tether_up = self._alive(self.tether)
        peer_up = sum(1 for peer in self.peers if self._alive(peer))
        sites = public_sites if public_sites is not None else {}
        ok = status["chain_ok"]
        return {
            **status,
            "ok": ok,
            "product": PRODUCT,
            "version": VERSION,
            "motto": MOTTO,
            "route": self.route_name(),
            "prefer_central": self.prefer_central(),
            "central": {
                "product_ingest": central_up,
                "tether_bootstrap": tether_up,
                "public_sites": sites,
            },
            "live_peers": peer_up,
            "note": NOTE_NOT_MESH_WORKER,
            "scopes": list(SCOPES),
            "work_scopes": list(WORK_SCOPES),
            "lattice_anchors": status.get("lattice_anchors", 0),
            "precedent_length": status.get("precedent_length", 0),
            "conflicts": self.store.conflict_status().get("conflicts", {}),
        }

    def anchor(self, product: str | None = None) -> dict[str, Any]:
        from azieltether.lattice import mint_anchor, mint_survival_round

        posted = []
        if product:
            posted.append(mint_anchor(self.store, product))
        else:
            posted = mint_survival_round(self.store)
        results = [self.push(batch) for batch in posted]
        return {
            "ok": True,
            "count": len(results),
            "hashes": [item.get("hash") for item in results],
            "via": results[0]["via"] if results else "local",
            "note": "lattice anchors posted; any surviving product tip can rehydrate the others",
        }

    def conflict_status(self) -> dict[str, Any]:
        return self.store.conflict_status()

    def lattice_status(self) -> dict[str, Any]:
        from azieltether.lattice import rehydrate

        return rehydrate(self.store.load_batches("lattice"))

    def _central_target(self) -> Transport | None:
        if self._alive(self.central):
            return self.central
        if self._alive(self.tether):
            return self.tether
        return None

    def _alive(self, transport: Transport | None) -> bool:
        if transport is None:
            return False
        try:
            return bool(transport.health())
        except TransportError:
            return False

    def _remember_from(self, transport: Transport | None) -> None:
        if transport is None or not self._alive(transport):
            return
        try:
            self.store.merge_peers(transport.peers("*"))
        except TransportError:
            return


def memory_pair() -> tuple[MemoryTransport, MemoryTransport]:
    """Two in-process nodes for tests."""
    return MemoryTransport(name="central"), MemoryTransport(name="peer")


def first_alive(transports: Iterable[Transport]) -> Transport | None:
    for item in transports:
        try:
            if item.health():
                return item
        except TransportError:
            continue
    return None
