"""Same-hash / fork collision spawns chain B and never rewrites chain A."""

from __future__ import annotations

from azieltether.chain import create_batch
from azieltether.constants import GENESIS_PREV_HASH
from azieltether.crypto import generate_keypair, node_id_from_pubkey
from azieltether.store import Store


def test_fork_spawns_precedent_and_keeps_chain_a(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    first = store.mint_batch("godlock", "receipt", {"note": "A1"})
    child_a = store.mint_batch("godlock", "receipt", {"note": "child-A"})
    node = store.load_node()
    sibling = create_batch(
        private_b64=node["private"],
        public_b64=node["pubkey"],
        node_id=node["node_id"],
        scope="godlock",
        kind="receipt",
        payload={"note": "child-B-fork"},
        prev_hash=first["hash"],
    )
    store.accept_batch(sibling)
    assert store.last_accept == "precedent"
    assert store.tip_hash("godlock") == child_a["hash"]
    assert store.load_batches("godlock")[-1]["hash"] == child_a["hash"]
    assert len(store.load_batches("precedent")) == 1
    receipt = store.load_batches("precedent")[0]
    payload = receipt["payload"]
    assert payload["conflict_kind"] == "fork"
    assert child_a["hash"] in payload["parent_tips"]
    assert sibling["hash"] in payload["parent_tips"]
    assert payload["chain_a_tip"] == child_a["hash"]
    assert payload["tether_link"] == child_a["hash"]


def test_same_hash_different_body_spawns_precedent(tmp_path, monkeypatch):
    store = Store(tmp_path)
    store.ensure_node()
    batch = store.mint_batch("aziel-runtime", "catalog_event", {"op": "one"})
    other = create_batch(
        private_b64=store.load_node()["private"],
        public_b64=store.load_node()["pubkey"],
        node_id=store.load_node()["node_id"],
        scope="aziel-runtime",
        kind="catalog_event",
        payload={"op": "other-body"},
        prev_hash=GENESIS_PREV_HASH,
    )
    other["hash"] = batch["hash"]
    monkeypatch.setattr("azieltether.store.verify_batch", lambda incoming, **_k: dict(incoming))
    store.accept_batch(other)
    assert store.last_accept == "precedent"
    assert store.tip_hash("aziel-runtime") == batch["hash"]
    assert store.load_batches("aziel-runtime") == [batch]
    assert store.conflict_status()["precedent_length"] == 1
    assert store.conflict_status()["chain_a_rewritten"] is False


def test_identical_duplicate_is_not_a_conflict(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    batch = store.mint_batch("godlock", "receipt", {"note": "same"})
    again = store.accept_batch(batch)
    assert store.last_accept == "duplicate"
    assert again["hash"] == batch["hash"]
    assert store.conflict_status()["precedent_length"] == 0


def test_accidental_identity_on_lattice_tip(tmp_path):
    a = Store(tmp_path / "a")
    b = Store(tmp_path / "b")
    a.ensure_node()
    b.ensure_node()
    tip = "c" * 64
    from azieltether.lattice import mint_anchor

    a.mint_batch("godlock", "receipt", {"note": "x"})
    # Overwrite the godlock tip hash in the anchor payload by passing tip_hash.
    mint_anchor(a, "godlock", tip_hash=tip)
    other_priv, other_pub = generate_keypair()
    other_id = node_id_from_pubkey(other_pub)
    from azieltether.chain import create_batch
    from azieltether.lattice import anchor_payload

    payload = anchor_payload(
        product="godlock",
        tip_hash=tip,
        prev_anchor=GENESIS_PREV_HASH,
        node_id=other_id,
        cross_links={"godlock": tip},
    )
    foreign = create_batch(
        private_b64=other_priv,
        public_b64=other_pub,
        node_id=other_id,
        scope="lattice",
        kind="anchor",
        payload=payload,
        prev_hash=GENESIS_PREV_HASH,
    )
    a.accept_batch(foreign)
    assert a.last_accept == "precedent"
    kinds = a.conflict_status()["conflicts"]
    assert kinds.get("accidental_identity") == 1
