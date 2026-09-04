"""When central is healthy, traffic goes there — not to peers."""

from __future__ import annotations

from azieltether.router import Router
from azieltether.store import Store
from azieltether.transport import MemoryTransport


def _router(tmp_path, *, central_up=True, tether_up=True, peer_up=True):
    store = Store(tmp_path)
    store.ensure_node()
    central = MemoryTransport(name="central", up=central_up)
    tether = MemoryTransport(name="tether", up=tether_up)
    peer = MemoryTransport(name="peer", up=peer_up)
    return Router(store, central=central, tether=tether, peers=[peer]), central, tether, peer


def test_prefer_central_true_when_central_up(tmp_path):
    router, central, tether, peer = _router(tmp_path)
    assert router.prefer_central() is True
    assert router.route_name() == "central"
    result = router.announce()
    assert result["via"] == "central"
    assert central.announced
    assert not peer.announced


def test_push_goes_to_central_not_peers(tmp_path):
    router, central, _tether, peer = _router(tmp_path)
    batch = router.store.mint_batch("godlock", "receipt", {"note": "prefer-central"})
    result = router.push(batch)
    assert result["via"] == "central"
    assert result["route"] == "central"
    assert central.held[0]["hash"] == batch["hash"]
    assert peer.held == []
    assert router.store.load_backlog() == []


def test_tether_bootstrap_is_central_when_product_ingest_down(tmp_path):
    router, central, tether, peer = _router(tmp_path, central_up=False, tether_up=True)
    assert router.prefer_central() is True
    assert router.route_name() == "tether"
    batch = router.store.mint_batch("aziel-runtime", "catalog_event", {"op": "index"})
    result = router.push(batch)
    assert result["via"] == "tether"
    assert tether.held
    assert peer.held == []
