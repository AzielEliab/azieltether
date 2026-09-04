"""When central is down, peers exchange batches."""

from __future__ import annotations

from azieltether.router import Router
from azieltether.store import Store
from azieltether.transport import MemoryTransport


def test_announce_gossips_when_central_down(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    central = MemoryTransport(name="central", up=False)
    tether = MemoryTransport(name="tether", up=False)
    peer = MemoryTransport(name="peer", up=True)
    router = Router(store, central=central, tether=tether, peers=[peer])
    result = router.announce()
    assert result["via"] == "peer"
    assert result["gossiped"] == 1
    assert peer.announced
    assert not central.announced


def test_push_falls_back_to_peers_and_backlog(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    central = MemoryTransport(name="central", up=False)
    tether = MemoryTransport(name="tether", up=False)
    peer = MemoryTransport(name="peer", up=True)
    router = Router(store, central=central, tether=tether, peers=[peer])
    batch = store.mint_batch("godlock", "receipt", {"note": "offline office"})
    result = router.push(batch)
    assert result["via"] == "peer"
    assert result["backlog"] is True
    assert peer.held[0]["hash"] == batch["hash"]
    assert central.held == []
    assert store.load_backlog()[0]["hash"] == batch["hash"]


def test_pull_from_peers_when_central_down(tmp_path):
    a = Store(tmp_path / "a")
    b = Store(tmp_path / "b")
    a.ensure_node()
    b.ensure_node()
    hub = MemoryTransport(name="peer-hub", up=True)
    down = MemoryTransport(name="central", up=False)
    sender = Router(a, central=down, tether=down, peers=[hub])
    receiver = Router(b, central=down, tether=down, peers=[hub])
    batch = a.mint_batch("aziel-corpus", "ingest_envelope", {"title": "public page"})
    sender.push(batch)
    pulled = receiver.pull(product="aziel-corpus")
    assert batch["hash"] in pulled["accepted"]
    assert b.load_batches("aziel-corpus")[0]["hash"] == batch["hash"]


def test_route_is_local_when_everyone_is_down(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    router = Router(
        store,
        central=MemoryTransport(name="central", up=False),
        tether=MemoryTransport(name="tether", up=False),
        peers=[MemoryTransport(name="peer", up=False)],
    )
    assert router.prefer_central() is False
    assert router.route_name() == "local"
    batch = store.mint_batch("godlock", "receipt", {"note": "solo"})
    result = router.push(batch)
    assert result["via"] == "local"
    assert result["backlog"] is True
