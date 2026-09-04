"""Pulse / reconcile / harvest / tips without requiring a live Worker."""

from __future__ import annotations

from pathlib import Path

from azieltether.item import Item
from azieltether.lattice import bind_surfaces, mint_tip, verify_tip
from azieltether.protocol import MODE_PEER, pulse, reconcile
from azieltether.queues import harvest
from azieltether.store import Store


def test_pulse_offline_is_peer_mode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AZIELTETHER_OFFLINE", "1")
    st = Store(tmp_path / "home")
    st.chain().append("local work", node_id=st.node_id())
    rec = pulse(st, probe=True, harvest_siblings=False)
    assert rec["mode"] == MODE_PEER
    assert rec["vpn"] is False
    assert rec["mesh_on_public_boards"] is False
    assert rec["author"] == "Aziel Eliab"


def test_reconcile_merges_dual_chain(tmp_path: Path) -> None:
    st = Store(tmp_path / "home")
    chain = st.chain()
    first = chain.append("parent", node_id=st.node_id(), created_at="2026-09-04T00:00:00Z")
    left = Item.create(payload="L", prev_hash=first.hash, node_id=st.node_id(), created_at="2026-09-04T00:01:00Z")
    right = Item.create(payload="R", prev_hash=first.hash, node_id=st.node_id(), created_at="2026-09-04T00:02:00Z")
    rec = reconcile(st, incoming=[left.as_dict(), right.as_dict()], probe=False)
    assert rec["ok"] is True
    assert rec["merge"]["added"] == 2
    assert rec["dual_chain"]
    assert rec["mode"] == MODE_PEER


def test_harvest_sibling_queue(tmp_path: Path) -> None:
    from azieltether.canon import GENESIS_PREV_HASH, digest_mapping

    sib = tmp_path / "tether-queue.jsonl"
    body = {
        "created_at": "2026-09-04T00:00:00Z",
        "engine_version": "0.3.0",
        "prev_hash": GENESIS_PREV_HASH,
        "report_hash": "f" * 64,
        "scope": "az-clce",
    }
    body["hash"] = digest_mapping(body)
    sib.write_text(__import__("json").dumps(body, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    st = Store(tmp_path / "home")
    rec = harvest(st.chain(), extra=[sib])
    assert rec["added"] == 1
    assert st.chain().verify().ok


def test_lattice_tip_verifies() -> None:
    tip = mint_tip(surface="godlock", tip_hash="a" * 64, node_id="b" * 64)
    rec = verify_tip(tip.as_dict())
    assert rec["ok"] is True
    assert rec["surface"] == "godlock"


def test_bind_surfaces(tmp_path: Path) -> None:
    st = Store(tmp_path / "home")
    st.chain().append("tip work", node_id=st.node_id())
    bound = bind_surfaces(st.chain(), node_id=st.node_id())
    assert "godlock" in bound["surfaces"]
    assert "corpus" in bound["surfaces"]
    assert "worker" in bound["surfaces"]
    assert bound["mesh_on_public_boards"] is False
