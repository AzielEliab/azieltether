"""on_transfer fires on upload and download, including offline."""

from __future__ import annotations

from azieltether.hooks import clear_hooks, register, registered
from azieltether.router import Router
from azieltether.store import Store
from azieltether.transport import MemoryTransport


def test_hooks_fire_offline_upload_and_online_download(tmp_path):
    seen: list[dict] = []
    register("clce-test", lambda event: seen.append(event) or {"rescored": True})
    try:
        assert "clce-test" in registered()
        store = Store(tmp_path / "offline")
        store.ensure_node()
        down = MemoryTransport(name="central", up=False)
        router = Router(store, central=down, tether=down, peers=[])
        batch = store.mint_batch("godlock", "receipt", {"note": "offline-upload"})
        result = router.push(batch)
        assert result["via"] == "local"
        assert result["hooks"]
        assert any(h["hook"] == "structure" and h["ok"] for h in result["hooks"])
        assert any(h["hook"] == "clce-test" and h["ok"] for h in result["hooks"])
        assert seen[0]["direction"] == "upload"
        assert seen[0]["offline"] is True
        assert seen[0]["structure"]["ok"] is True

        hub = MemoryTransport(name="peer-hub", up=True)
        sender = Router(Store(tmp_path / "s"), central=down, tether=down, peers=[hub])
        sender.store.ensure_node()
        shipped = sender.store.mint_batch("aziel-corpus", "ingest_envelope", {"title": "pub"})
        sender.push(shipped)

        receiver_store = Store(tmp_path / "r")
        receiver_store.ensure_node()
        receiver = Router(receiver_store, central=down, tether=down, peers=[hub])
        seen.clear()
        pulled = receiver.pull(product="aziel-corpus")
        assert shipped["hash"] in pulled["accepted"]
        assert seen
        assert seen[0]["direction"] == "download"
        assert seen[0]["structure"]["ok"] is True
    finally:
        clear_hooks()


def test_structure_hook_sees_whole_chain(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    store.mint_batch("godlock", "receipt", {"n": 1})
    store.mint_batch("godlock", "receipt", {"n": 2})
    from azieltether.hooks import verify_structure

    report = verify_structure(store)
    assert report.ok is True
    assert "godlock" in report.tips
