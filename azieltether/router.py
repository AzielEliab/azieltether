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
)
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
        target = self._central_target()
        if target is not None:
            result = target.push_batch(verified)
            self.store.remove_backlog(verified["hash"])
            return {
                "ok": True,
                "via": target.name,
                "route": "central" if target is self.central else "tether",
                "hash": verified["hash"],
                "result": result,
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
                    accepted.append(verified["hash"])
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
        }

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
