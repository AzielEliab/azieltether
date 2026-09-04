"""Hash-chain and Ed25519 verification."""

from __future__ import annotations

import pytest

from azieltether.chain import ChainError, create_batch, verify_batch, verify_chain
from azieltether.constants import GENESIS_PREV_HASH
from azieltether.crypto import generate_keypair, node_id_from_pubkey


def _node():
    private, public = generate_keypair()
    return private, public, node_id_from_pubkey(public)


def test_create_and_verify_genesis():
    private, public, node_id = _node()
    batch = create_batch(
        private_b64=private,
        public_b64=public,
        node_id=node_id,
        scope="godlock",
        kind="receipt",
        payload={"note": "first"},
    )
    assert batch["prev_hash"] == GENESIS_PREV_HASH
    assert batch["hash"] != GENESIS_PREV_HASH
    verified = verify_batch(batch)
    assert verified["hash"] == batch["hash"]


def test_chain_links_prev_hash():
    private, public, node_id = _node()
    first = create_batch(
        private_b64=private,
        public_b64=public,
        node_id=node_id,
        scope="aziel-runtime",
        kind="catalog_event",
        payload={"op": "list"},
    )
    second = create_batch(
        private_b64=private,
        public_b64=public,
        node_id=node_id,
        scope="aziel-runtime",
        kind="catalog_event",
        payload={"op": "get"},
        prev_hash=first["hash"],
    )
    chain = verify_chain([first, second])
    assert chain[1]["prev_hash"] == chain[0]["hash"]


def test_tampered_payload_fails():
    private, public, node_id = _node()
    batch = create_batch(
        private_b64=private,
        public_b64=public,
        node_id=node_id,
        scope="godlock",
        kind="receipt",
        payload={"note": "clean"},
    )
    batch["payload"] = {"note": "tampered"}
    with pytest.raises(ChainError, match="hash mismatch"):
        verify_batch(batch)


def test_bad_prev_hash_rejected():
    private, public, node_id = _node()
    first = create_batch(
        private_b64=private,
        public_b64=public,
        node_id=node_id,
        scope="godlock",
        kind="receipt",
        payload={"n": 1},
    )
    second = create_batch(
        private_b64=private,
        public_b64=public,
        node_id=node_id,
        scope="godlock",
        kind="receipt",
        payload={"n": 2},
        prev_hash=first["hash"],
    )
    with pytest.raises(ChainError, match="prev_hash"):
        verify_batch(second, expected_prev=GENESIS_PREV_HASH)


def test_corpus_operator_write_refused():
    private, public, node_id = _node()
    with pytest.raises(ChainError, match="operator"):
        create_batch(
            private_b64=private,
            public_b64=public,
            node_id=node_id,
            scope="aziel-corpus",
            kind="ingest_envelope",
            payload={"operator": True, "title": "secret library write"},
        )


def test_public_corpus_envelope_ok():
    private, public, node_id = _node()
    batch = create_batch(
        private_b64=private,
        public_b64=public,
        node_id=node_id,
        scope="aziel-corpus",
        kind="ingest_envelope",
        payload={"title": "public scan", "visibility": "public"},
    )
    verify_batch(batch)


def test_unknown_scope_rejected():
    private, public, node_id = _node()
    with pytest.raises(ChainError, match="unknown scope"):
        create_batch(
            private_b64=private,
            public_b64=public,
            node_id=node_id,
            scope="miragegrid",
            kind="receipt",
            payload={},
        )
