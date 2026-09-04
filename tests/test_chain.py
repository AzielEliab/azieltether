"""Genesis, append, verify, dual-chain. Author: Aziel Eliab."""

from __future__ import annotations

from pathlib import Path

from azieltether.canon import GENESIS_PREV_HASH
from azieltether.chain import Chain, detect_dual_chain
from azieltether.errors import ChainError
from azieltether.item import Item


def test_genesis_append_verify(tmp_path: Path) -> None:
    path = tmp_path / "q.jsonl"
    chain = Chain.genesis(
        path,
        payload="parent work",
        node_id="n" * 64,
        created_at="2026-09-04T00:00:00Z",
    )
    assert len(chain) == 1
    assert chain[0].prev_hash == GENESIS_PREV_HASH
    assert chain[0].verify_hash()
    chain.append("child work", node_id="n" * 64, created_at="2026-09-04T00:01:00Z")
    result = chain.verify()
    assert result.ok
    assert result.items == 2
    assert chain[1].prev_hash == chain[0].hash


def test_genesis_refused_if_exists(tmp_path: Path) -> None:
    path = tmp_path / "q.jsonl"
    Chain.genesis(path, payload="a", node_id="n" * 64)
    try:
        Chain.genesis(path, payload="b", node_id="n" * 64)
        raise AssertionError("expected ChainError")
    except ChainError:
        pass


def test_dual_chain_keeps_both(tmp_path: Path) -> None:
    path = tmp_path / "q.jsonl"
    chain = Chain.genesis(path, payload="parent", node_id="n" * 64, created_at="2026-09-04T00:00:00Z")
    parent = chain[0]
    left = Item.create(payload="left", prev_hash=parent.hash, node_id="n" * 64, created_at="2026-09-04T00:01:00Z")
    right = Item.create(payload="right", prev_hash=parent.hash, node_id="n" * 64, created_at="2026-09-04T00:02:00Z")
    assert left.hash != right.hash
    chain.append_item(left)
    chain.append_item(right)
    forks = detect_dual_chain(chain.items)
    assert len(forks) == 1
    assert set(forks[0].child_hashes) == {left.hash, right.hash}
    result = chain.verify()
    assert result.ok
    assert result.dual_chain


def test_merge_skips_same_hash(tmp_path: Path) -> None:
    path = tmp_path / "q.jsonl"
    chain = Chain.genesis(path, payload="a", node_id="n" * 64)
    item = chain[0]
    merged = chain.merge([item.as_dict()])
    assert merged["added"] == 0
    assert merged["skipped"] == 1


def test_az_clce_shaped_item_verifies(tmp_path: Path) -> None:
    from azieltether.canon import canonical_json, digest_mapping

    body = {
        "created_at": "2026-09-04T00:00:00Z",
        "engine_version": "0.3.0",
        "prev_hash": GENESIS_PREV_HASH,
        "report_hash": "e" * 64,
        "scope": "az-clce",
    }
    body["hash"] = digest_mapping(body)
    assert digest_mapping(body) == body["hash"]
    item = Item.from_mapping(body)
    chain = Chain(tmp_path / "sib.jsonl")
    chain.append_item(item)
    assert chain.verify().ok
    assert canonical_json({"a": 1, "b": 2})
