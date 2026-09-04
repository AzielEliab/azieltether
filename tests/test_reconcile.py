"""When central returns, local backlog is pushed up."""

from __future__ import annotations

from azieltether.router import Router
from azieltether.store import Store
from azieltether.transport import MemoryTransport


def test_reconcile_waits_while_central_is_down(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    central = MemoryTransport(name="central", up=False)
    router = Router(store, central=central, tether=MemoryTransport(name="tether", up=False), peers=[])
    batch = store.mint_batch("godlock", "receipt", {"note": "hold"})
    router.push(batch)
    result = router.reconcile()
    assert result["ok"] is False
    assert result["remaining"] == 1
    assert central.held == []


def test_reconcile_pushes_backlog_when_central_returns(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    central = MemoryTransport(name="central", up=False)
    router = Router(store, central=central, tether=MemoryTransport(name="tether", up=False), peers=[])
    one = store.mint_batch("godlock", "receipt", {"note": "one"})
    two = store.mint_batch("godlock", "receipt", {"note": "two"})
    router.push(one)
    router.push(two)
    assert len(store.load_backlog()) == 2

    central.up = True
    result = router.reconcile()
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["remaining"] == 0
    assert {item["hash"] for item in central.held} == {one["hash"], two["hash"]}


def test_reconcile_uses_tether_bootstrap_if_that_is_the_central(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    tether = MemoryTransport(name="tether", up=False)
    router = Router(store, central=None, tether=tether, peers=[])
    batch = store.mint_batch("aziel-runtime", "catalog_event", {"op": "add"})
    router.push(batch)
    tether.up = True
    result = router.reconcile()
    assert result["via"] == "tether"
    assert tether.held[0]["hash"] == batch["hash"]
    assert store.load_backlog() == []


def test_author_constant():
    from azieltether import AUTHOR, PRODUCT, VERSION

    assert AUTHOR == "Aziel Eliab"
    assert PRODUCT == "azieltether"
    assert VERSION == "0.1.0"
