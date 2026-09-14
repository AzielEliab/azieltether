"""SPLIT THE WIRES — real protocol. Author: Aziel Eliab."""

from __future__ import annotations

from pathlib import Path

import pytest

from azieltether.errors import WiresError
from azieltether.item import Item
from azieltether.protocol import accept_peer, accept_tick_plane, serve_payload
from azieltether.store import Store
from azieltether.wires import (
    GATE_DWELL_S,
    GATE_SOCKET,
    TICK_FRAME_BYTES,
    TICK_MAX_MS,
    TICK_MIN_MS,
    TICK_SOCKET,
    WIRES_SPEC,
    apply_update,
    assert_distinct_sockets,
    detect_equivocation,
    dwell_ready,
    emit_last,
    encode_tick,
    equivocation_verdict,
    hash_holds,
    on_heartbeat_loss,
    parse_tick_frame,
    partition_rejoin,
    phoenix_allowed,
    pull_request,
    refuse_push_fanout,
    refuse_unsend,
    tick_frame,
    tick_interval_ok,
)


def test_tick_interval_and_distinct_sockets() -> None:
    assert tick_interval_ok(TICK_MIN_MS)
    assert tick_interval_ok(TICK_MAX_MS)
    assert not tick_interval_ok(499)
    assert not tick_interval_ok(1001)
    assert_distinct_sockets(TICK_SOCKET, GATE_SOCKET)
    with pytest.raises(WiresError):
        assert_distinct_sockets("tick", "tick")


def test_tick_frame_fixed_size_no_body() -> None:
    raw = tick_frame("a" * 64, "b" * 64)
    assert len(raw) == TICK_FRAME_BYTES
    parsed = parse_tick_frame(raw)
    assert parsed["node_id"] == "a" * 64
    assert parsed["tip_hash"] == "b" * 64
    env = encode_tick(node_id="c" * 64, tip_hash="d" * 64)
    assert env["spec"] == WIRES_SPEC
    assert env["plane"] == "tick"
    assert "payload" not in env
    assert "items" not in env


def test_push_fanout_refused() -> None:
    rec = refuse_push_fanout({"items": [{"hash": "a" * 64}]})
    assert rec["ok"] is False
    assert rec["code"] == "WIRES-PUSH-REFUSED"


def test_cite_and_777s_dwell_clock_desync_not_yes() -> None:
    assert dwell_ready(cited_at=0, now=777, dwell_s=GATE_DWELL_S)
    assert not dwell_ready(cited_at=10, now=9, dwell_s=GATE_DWELL_S)
    early = apply_update(cite="a" * 64, lockset="b" * 64, cited_at=0, now=776)
    assert early["ok"] is False
    assert early["code"] == "WIRES-DWELL"
    missing = apply_update(cite=None, lockset=None, cited_at=0, now=777)
    assert missing["ok"] is False
    ready = apply_update(cite="a" * 64, lockset="b" * 64, cited_at=0, now=777)
    assert ready["ok"] is True
    amb = apply_update(
        cite="a" * 64,
        lockset="b" * 64,
        cited_at=0,
        now=777,
        tip_hashes=["c" * 64, "d" * 64],
    )
    assert amb["isolate"] is True


def test_equivocation_ends_peer() -> None:
    ticks = [
        {"node_id": "n" * 64, "prev_hash": "p" * 64, "tip_hash": "1" * 64},
        {"node_id": "n" * 64, "prev_hash": "p" * 64, "tip_hash": "2" * 64},
    ]
    forks = detect_equivocation(ticks)
    assert len(forks) == 1
    verdict = equivocation_verdict(ticks)
    assert verdict["ok"] is False
    assert "n" * 64 in verdict["isolate"]


def test_quorum_cannot_outvote_broken_hash() -> None:
    assert hash_holds(digest_ok=True, votes_for=0)
    assert not hash_holds(digest_ok=False, votes_for=10_000)


def test_emit_phoenix_unsend_partition_heartbeat() -> None:
    emit_last(verified=True, item={"hash": "a" * 64})
    with pytest.raises(WiresError):
        emit_last(verified=False)
    assert phoenix_allowed(failed_node_id="x", actor_node_id="x")
    assert not phoenix_allowed(failed_node_id="x", actor_node_id="y")
    with pytest.raises(WiresError):
        refuse_unsend(verified=False)
    with pytest.raises(WiresError):
        refuse_unsend(verified=True)
    splice = partition_rejoin(cite=None, lockset=None, operator=False)
    assert splice["ok"] is False
    assert splice["code"] == "WIRES-NO-AUTO-SPLICE"
    rejoin = partition_rejoin(cite="a" * 64, lockset="b" * 64, operator=True)
    assert rejoin["ok"] is True
    hb = on_heartbeat_loss()
    assert hb["poison"] is False
    assert hb["apply_last_packet"] is False


def test_accept_peer_refuses_live_push(tmp_path: Path) -> None:
    st = Store(tmp_path / "home")
    st.chain().append("desk", node_id=st.node_id())
    rec = accept_peer(st, {"items": [{"payload": "live"}]})
    assert rec["ok"] is False
    assert rec["items"] == []


def test_tick_and_payload_doors(tmp_path: Path) -> None:
    st = Store(tmp_path / "home")
    item = st.chain().append("work", node_id=st.node_id())
    lock = st.seal_lockset()
    tick = accept_tick_plane(
        st,
        encode_tick(node_id=st.node_id(), tip_hash=item.hash),
    )
    assert tick["ok"] is True
    assert tick["items"] == []
    assert tick["socket"] == TICK_SOCKET
    pull = pull_request(cite=item.hash, lockset=str(lock["hash"]), want=[item.hash])
    served = serve_payload(st, pull)
    assert served["ok"] is True
    assert served["socket"] == GATE_SOCKET
    assert served["push_fanout"] is False
    assert served["items"][0]["hash"] == item.hash


def test_peer_merge_no_auto_splice(tmp_path: Path) -> None:
    st = Store(tmp_path / "home")
    parent = st.chain().append("p", node_id=st.node_id(), created_at="2026-09-04T00:00:00Z")
    left = Item.create(payload="L", prev_hash=parent.hash, node_id="z" * 64, created_at="2026-09-04T00:01:00Z")
    right = Item.create(payload="R", prev_hash=parent.hash, node_id="y" * 64, created_at="2026-09-04T00:02:00Z")
    st.chain().append_item(left)
    rec = st.chain().merge([right.as_dict()], operator=False)
    assert rec["added"] == 0
    assert rec["isolate"] is True
    rec2 = st.chain().merge([right.as_dict()], operator=True)
    assert rec2["added"] == 1
