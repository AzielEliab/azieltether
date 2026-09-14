"""REHEAL — own tip + trusted pull or phoenix-WAIT. Author: Aziel Eliab."""

from __future__ import annotations

from pathlib import Path

import pytest

from azieltether.errors import RehealError
from azieltether.item import Item
from azieltether.protocol import reheal
from azieltether.reheal import (
    ALLOWED_CHATTER,
    PHOENIX_WAIT,
    REHEAL_SPEC,
    chatter_allowed,
    decide,
    last_good_tip,
    refuse_vote_to_fix,
)
from azieltether.store import Store


def test_last_good_tip_stops_at_poison(tmp_path: Path) -> None:
    st = Store(tmp_path / "home")
    first = st.chain().append("good", node_id=st.node_id(), created_at="2026-09-04T00:00:00Z")
    assert st.chain().last_good_tip() == first.hash
    broken = {
        "created_at": "2026-09-04T00:01:00Z",
        "engine_version": "0.1.0",
        "hash": "0" * 64,
        "kind": "work",
        "node_id": st.node_id(),
        "payload": "poison",
        "prev_hash": first.hash,
        "report_hash": "1" * 64,
        "scope": "azieltether",
    }
    assert last_good_tip([first.as_dict(), broken]) == first.hash


def test_no_neighbor_vote_to_fix() -> None:
    rec = refuse_vote_to_fix(votes_for=12, neighbor_fix="adopt this")
    assert rec["ok"] is False
    assert rec["code"] == "REHEAL-VOTE-REFUSED"
    voted = decide(own_tip="a" * 64, votes_for=7)
    assert voted["ok"] is False
    assert voted["applied"] is False


def test_chatter_live_locked_isolated_tip_hash_only() -> None:
    assert chatter_allowed({"live": 1, "locked": 0, "isolated": 2, "tip_hash": "a" * 64})
    assert chatter_allowed({"tip-hash": "b" * 64})
    assert not chatter_allowed({"body": "nope"})
    assert not chatter_allowed({"vote": 3})
    assert set(ALLOWED_CHATTER) == {"live", "locked", "isolated", "tip_hash"}
    with pytest.raises(RehealError):
        decide(own_tip="a" * 64, chatter={"items": []})


def test_trusted_pull_or_phoenix_wait(tmp_path: Path) -> None:
    st = Store(tmp_path / "home")
    parent = st.chain().append("root", node_id=st.node_id(), created_at="2026-09-04T00:00:00Z")
    lock = st.seal_lockset()
    wait = reheal(st)
    assert wait["reheal"]["wait"] == PHOENIX_WAIT
    assert wait["own_tip"] == parent.hash
    assert wait["spec"] == REHEAL_SPEC
    child = Item.create(
        payload="trusted",
        prev_hash=parent.hash,
        node_id=st.node_id(),
        created_at="2026-09-04T00:01:00Z",
    )
    pulled = reheal(
        st,
        cite=parent.hash,
        lockset=str(lock["hash"]),
        incoming=[child.as_dict()],
    )
    assert pulled["reheal"]["code"] == "REHEAL-TRUSTED-PULL"
    assert pulled["merge"]["added"] == 1
    refused = reheal(st, votes_for=99, neighbor_fix="fix me")
    assert refused["ok"] is False
    assert refused["reheal"]["code"] == "REHEAL-VOTE-REFUSED"
