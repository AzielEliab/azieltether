"""COLD-SHELF-TETHER — up→down→restore, rewrite refuse, no lie-to-survive.

Author: Aziel Eliab only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from azieltether.errors import AppendOnlyError
from azieltether.shelf import (
    CROSS_NETWORK_SPEC,
    NO_LIE_SPEC,
    PERSON_ID,
    PLANE_A_HUBS,
    SHELF_SPEC,
    SISTER_SPEC,
    classify_url,
    doi_is_live,
    plane_a_card,
    plane_b_status,
    plane_c_card,
    export_usb,
    fetch_manifest,
    import_usb,
    law_card,
    refuse_delete_shelf,
    refuse_fan,
    refuse_lie_to_survive,
    refuse_rewrite_key,
    refuse_slot,
    seal_shelf,
    serve_last_local,
    sha256_bytes,
    shelf_sync,
    verify_sha256,
)
from azieltether.store import Store


def _home(tmp_path: Path) -> Store:
    st = Store(tmp_path / "home")
    st.chain().append("desk closed", node_id=st.node_id(), created_at="2026-09-04T00:00:00Z")
    return st


def test_law_card_honest() -> None:
    card = law_card()
    assert card["spec"] == SHELF_SPEC
    assert card["sister_spec"] == SISTER_SPEC
    assert card["cross_network"] == CROSS_NETWORK_SPEC
    assert card["no_lie"] == NO_LIE_SPEC
    assert card["person_id"] == PERSON_ID
    assert card["durable_store"] is False
    assert card["worker_holds_chain"] is False
    assert card["ipfs"] is False
    assert card["multihome_dns"] is False
    assert card["az_generator"] is False
    assert card["planes"]["A"]["survives_cf_yank"] is False
    assert card["planes"]["C"]["survives_cf_yank"] is True
    assert card["slots"]["ipfs"]["live"] is False
    assert card["slots"]["ipfs"]["code"] == "SHELF-SLOT-IPFS"


def test_refuse_slots() -> None:
    assert refuse_slot("ipfs")["code"] == "SHELF-SLOT-IPFS"
    assert refuse_slot("cid")["code"] == "SHELF-SLOT-IPFS"
    assert refuse_slot("multihome_dns")["code"] == "SHELF-SLOT-MULTIHOME-DNS"
    assert refuse_slot("auto_publish")["code"] == "SHELF-SLOT-AUTO-PUBLISH"
    assert refuse_slot("anycast")["code"] == "SHELF-SLOT-ANYCAST"
    assert refuse_slot("az_generator")["code"] == "SHELF-SLOT-AZ-GENERATOR"
    assert refuse_slot("zenodo_doi")["code"] == "SHELF-SLOT-ZENODO-DOI"
    assert refuse_slot("forge")["code"] == "SHELF-SLOT-FORGE-PUBLISH"
    assert classify_url("ipfs://QmFakeNotReal") == "ipfs"
    assert classify_url("https://example.test/ipfs/QmFake") == "ipfs"
    assert fetch_manifest("ipfs://QmFakeNotReal")["code"] == "SHELF-SLOT-IPFS"
    assert fetch_manifest("anycast://tips.example")["code"] == "SHELF-SLOT-MULTIHOME-DNS"


def test_refuse_rewrite_key() -> None:
    rec = refuse_rewrite_key({"rewrite_key": "please-survive"})
    assert rec["ok"] is False
    assert rec["code"] == "SHELF-REWRITE-REFUSED"
    assert rec["law"] == NO_LIE_SPEC
    assert refuse_rewrite_key({})["ok"] is True


def test_refuse_lie_to_survive() -> None:
    down = refuse_lie_to_survive(worker_up_claimed=True, worker_actually_up=False)
    assert down["ok"] is False
    assert down["code"] == "SHELF-LIE-REFUSED"
    invent = refuse_lie_to_survive(invented_tips=["a" * 64], known_hashes=["b" * 64])
    assert invent["ok"] is False
    ipfs = refuse_lie_to_survive(claim_ipfs_live=True)
    assert ipfs["ok"] is False
    assert ipfs["code"] == "SHELF-LIE-REFUSED"
    dns = refuse_lie_to_survive(claim_multihome_dns=True)
    assert dns["ok"] is False
    rewrite = refuse_lie_to_survive(claim_rewrite_to_survive=True)
    assert rewrite["ok"] is False
    hold = refuse_lie_to_survive(claim_worker_holds_chain=True)
    assert hold["ok"] is False
    honest = refuse_lie_to_survive(worker_up_claimed=False, worker_actually_up=False)
    assert honest["ok"] is True
    assert refuse_fan({"fan": True, "items": [{}]})["code"] == "SHELF-NO-FAN"


def test_hash_mismatch_refused(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text('{"spec":"COLD-SHELF-TETHER-1.0","author":"Aziel Eliab"}\n', encoding="utf-8")
    bad = fetch_manifest(str(path), expected_sha256="0" * 64)
    assert bad["ok"] is False
    assert bad["code"] == "SHELF-HASH-MISMATCH"
    data = path.read_bytes()
    good = fetch_manifest(str(path), expected_sha256=sha256_bytes(data))
    assert good["ok"] is True
    assert verify_sha256(b"x", "0" * 64)["code"] == "SHELF-HASH-MISMATCH"


def test_up_down_restore_hash_continuity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    st = _home(tmp_path)
    first = st.chain()[0].hash

    def fake_health_up(_host=None, **_kw):
        return {"ok": True, "prefer_central": True, "http_status": 200}

    def fake_health_down(_host=None, **_kw):
        return {"ok": False, "prefer_central": False, "reason": "network"}

    def fake_ingest(item, *, host=None):
        return {"ok": True, "accepted": True, "hash": item.get("hash"), "stored": False}

    def fake_tip(tip, *, host=None):
        return {"ok": True, "tip": {"hash": tip.get("hash") or first}, "stored": False}

    def fake_card(_host=None, **_kw):
        return {"ok": True, "durable_store": False, "zero_retention": True, "spec": SHELF_SPEC}

    monkeypatch.setattr("azieltether.client.probe_health", fake_health_up)
    monkeypatch.setattr("azieltether.client.ingest_item", fake_ingest)
    monkeypatch.setattr("azieltether.client.post_tip", fake_tip)
    monkeypatch.setattr("azieltether.client.pull_shelf_card", fake_card)

    up = shelf_sync(st, probe=True)
    assert up["ok"] is True
    assert up["worker_up"] is True
    assert up["active_plane"] == "A"
    assert up["planes"]["A"]["same_tunnel"] is True
    assert up["planes"]["A"]["survives_cf_yank"] is False
    assert up["planes"]["C"]["survives_cf_yank"] is True
    assert up["mode"] == "prefer-central"
    assert first in up["tip_hashes"]
    sealed_hash = up["sha256"]
    assert sealed_hash
    assert up["rewrite_key"] is False
    assert up["durable_worker_store"] is False

    monkeypatch.setattr("azieltether.client.probe_health", fake_health_down)
    down = shelf_sync(st, probe=True)
    assert down["ok"] is True
    assert down["worker_up"] is False
    assert down["code"] == "SHELF-DOWN"
    assert down["active_plane"] == "C"
    assert down["sha256"] == sealed_hash
    assert first in down["tip_hashes"]
    local = serve_last_local(st)
    assert local["ok"] is True
    assert local["re_expand_from_archive"] is True
    assert local["manifest"]["sha256"] == sealed_hash

    # Extra local work while down
    extra = st.chain().append("queued while yanked", node_id=st.node_id(), created_at="2026-09-04T00:01:00Z")
    monkeypatch.setattr("azieltether.client.probe_health", fake_health_up)
    restore = shelf_sync(st, probe=True)
    assert restore["ok"] is True
    assert restore["code"] == "SHELF-RESTORE"
    assert restore["active_plane"] == "A"
    assert restore["mode"] == "reconcile-on-restore"
    hashes = {i.hash for i in st.chain().items}
    assert first in hashes
    assert extra.hash in hashes
    assert st.chain().verify().ok
    # Original item bytes/hash unchanged
    assert st.chain()[0].hash == first


def test_shelf_sync_refuses_lie_when_down(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    st = _home(tmp_path)
    monkeypatch.setattr(
        "azieltether.client.probe_health",
        lambda host=None, **kw: {"ok": False, "prefer_central": False},
    )
    rec = shelf_sync(st, probe=True, incoming={"worker_up": True})
    assert rec["ok"] is False
    assert rec["code"] == "SHELF-LIE-REFUSED"


def test_shelf_sync_refuses_rewrite_payload(tmp_path: Path) -> None:
    st = _home(tmp_path)
    rec = shelf_sync(st, probe=False, incoming={"rewrite_key": "x"})
    assert rec["code"] == "SHELF-REWRITE-REFUSED"


def test_usb_airgap_roundtrip(tmp_path: Path) -> None:
    live = _home(tmp_path / "live")
    usb = tmp_path / "usb"
    out = export_usb(live, usb)
    assert out["ok"] is True
    assert (usb / "manifest.json").is_file()
    assert (usb / "manifest.sha256").is_file()
    assert (usb / "queue.jsonl").is_file()
    assert (usb / "README.txt").is_file()
    readme = (usb / "README.txt").read_text(encoding="utf-8")
    assert PERSON_ID in readme
    assert CROSS_NETWORK_SPEC in readme
    assert NO_LIE_SPEC in readme
    assert "15:20" not in readme

    air = Store(tmp_path / "air")
    rec = import_usb(air, usb)
    assert rec["ok"] is True
    assert rec["merge"]["added"] == 1
    assert air.chain()[0].hash == live.chain()[0].hash
    assert air.chain().verify().ok

    # Tamper refuses
    (usb / "manifest.json").write_text('{"sha256":"' + "0" * 64 + '","items":[]}\n', encoding="utf-8")
    bad = import_usb(Store(tmp_path / "poison"), usb)
    assert bad["ok"] is False
    assert bad["code"] in {"SHELF-HASH-MISMATCH", "SHELF-MANIFEST-INVALID"}


def test_pull_local_manifest_then_merge(tmp_path: Path) -> None:
    src = _home(tmp_path / "src")
    sealed = seal_shelf(src)
    assert sealed["ok"] is True
    dest = Store(tmp_path / "dest")
    rec = fetch_manifest(str(src.shelf_dir / "manifest.json"), expected_sha256=sealed["bytes_sha256"])
    assert rec["ok"] is True
    assert rec["manifest"]["person_id"] == PERSON_ID
    from azieltether.shelf import merge_verified_items

    merged = merge_verified_items(dest, rec["manifest"]["items"])
    assert merged["added"] == 1
    assert dest.chain()[0].hash == src.chain()[0].hash


def test_person_id_cannot_be_forked(tmp_path: Path) -> None:
    doc = {
        "author": "Aziel Eliab",
        "person_id": "https://example.test/#someone-else",
        "items": [],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    rec = fetch_manifest(str(path))
    assert rec["ok"] is False
    assert rec["code"] == "SHELF-PERSON-REFUSED"


def test_refuse_delete_shelf(tmp_path: Path) -> None:
    with pytest.raises(AppendOnlyError):
        refuse_delete_shelf(tmp_path / "shelf" / "manifest.json")


def test_operator_planes_a_b_c(monkeypatch: pytest.MonkeyPatch) -> None:
    a = plane_a_card()
    assert a["count"] == 4
    assert len(PLANE_A_HUBS) == 4
    assert a["same_tunnel"] is True
    assert a["survives_cf_yank"] is False
    assert all("workers.dev" in h for h in PLANE_A_HUBS)
    c = plane_c_card()
    assert c["survives_cf_yank"] is True
    assert c["forge_publish"] is False
    monkeypatch.delenv("AZIELTETHER_ZENODO_DOI", raising=False)
    monkeypatch.delenv("AZIELTETHER_ZENODO_URL", raising=False)
    b = plane_b_status()
    assert b["ok"] is False
    assert b["code"] == "SHELF-SLOT-ZENODO-DOI"
    assert doi_is_live("") is False
    assert doi_is_live("10.5281/zenodo.example") is False
    assert doi_is_live("10.5281/zenodo.0") is False
    assert doi_is_live("10.5281/zenodo.1") is False
    assert doi_is_live("10.5281/zenodo.123456") is True
    invented = plane_b_status(doi="10.5281/zenodo.XXXX")
    assert invented["code"] == "SHELF-DOI-REFUSED"
    live = plane_b_status(doi="10.5281/zenodo.123456", url="https://zenodo.org/records/123456/files/shelf.json")
    assert live["ok"] is True
    assert live["doi_live"] is True
