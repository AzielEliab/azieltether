"""COLD-COPY SURVIVAL — real protocol. Author: Aziel Eliab."""

from __future__ import annotations

from pathlib import Path

import pytest

from azieltether.errors import AppendOnlyError, SurvivalError
from azieltether.store import Store
from azieltether.survival import (
    MIN_COLD_COPIES,
    SURVIVAL_SPEC,
    copy_count,
    creator_gone,
    erase_tip,
    multiply_cold_copies,
    poison_refused,
    refuse_delete_copy,
    refuse_live_body_sync,
    single_server_pull,
)
from azieltether.wires import WIRES_SPEC


def test_multiply_cold_copies(tmp_path: Path) -> None:
    st = Store(tmp_path / "home")
    item = st.chain().append("sealed", node_id=st.node_id())
    rec = multiply_cold_copies(item, st.copies_dir)
    assert rec["ok"] is True
    assert rec["count"] >= MIN_COLD_COPIES
    assert copy_count(st.copies_dir) >= MIN_COLD_COPIES
    again = multiply_cold_copies(item, st.copies_dir)
    assert again["count"] >= MIN_COLD_COPIES
    st.multiply_copies()
    assert copy_count(st.copies_dir) >= MIN_COLD_COPIES


def test_refuse_live_body_sync() -> None:
    live = refuse_live_body_sync({"items": [{"payload": "stream"}]}, plane="tick")
    assert live["ok"] is False
    assert live["code"] == "SURVIVAL-LIVE-BODY-REFUSED"
    cold = refuse_live_body_sync({"cite": "a" * 64, "lockset": "b" * 64}, plane="payload")
    assert cold["ok"] is True


def test_poison_hash_absolute() -> None:
    assert poison_refused(digest_ok=False, votes_for=999)["ok"] is False
    assert poison_refused(digest_ok=True)["ok"] is True
    with pytest.raises(SurvivalError):
        multiply_cold_copies({"hash": "0" * 64, "payload": "bad"}, "/tmp/nope")


def test_tip_expensive_to_erase() -> None:
    with pytest.raises(AppendOnlyError):
        erase_tip()
    with pytest.raises(AppendOnlyError):
        erase_tip(operator=True)
    tomb = erase_tip(operator=True, cite="a" * 64, lockset="b" * 64, dwell_ready=True)
    assert tomb["erased"] is False
    assert tomb["tombstone"] is True
    with pytest.raises(AppendOnlyError):
        refuse_delete_copy("/tmp/copies/0/queue.jsonl")


def test_single_server_pull_cannot_kill() -> None:
    local = ["a" * 64, "b" * 64]
    rec = single_server_pull(local, [])
    assert rec["unkillable"] is True
    assert rec["dropped"] == []
    assert rec["local"] == local


def test_data_outlives_creators(tmp_path: Path) -> None:
    st = Store(tmp_path / "home")
    item = st.chain().append("remain", node_id=st.node_id())
    gone = creator_gone([item.as_dict()], creator_alive=False)
    assert gone["usable"] is True
    assert gone["outlives_creators"] is True
    assert SURVIVAL_SPEC.startswith("COLD-COPY")
    assert WIRES_SPEC.startswith("SPLIT")
