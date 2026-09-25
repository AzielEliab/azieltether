"""Self-check for AzielTether. No telemetry. Network only if asked.

    azieltether doctor
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Callable

from azieltether import __author__, __version__
from azieltether.canon import GENESIS_PREV_HASH, digest_mapping
from azieltether.chain import Chain, detect_dual_chain
from azieltether.item import Item
from azieltether.lattice import mint_tip
from azieltether.store import Store
from azieltether.shelf import (
    PERSON_ID,
    SHELF_SPEC,
    refuse_lie_to_survive,
    refuse_rewrite_key,
    refuse_slot,
    seal_shelf,
    verify_sha256,
)
from azieltether.survival import MIN_COLD_COPIES, multiply_cold_copies, poison_refused, single_server_pull
from azieltether.wires import (
    GATE_SOCKET,
    TICK_FRAME_BYTES,
    TICK_SOCKET,
    assert_distinct_sockets,
    encode_tick,
    hash_holds,
)

AUTHOR = "Aziel Eliab"
Check = tuple[str, bool, str]


def _ok(name: str, detail: str = "") -> Check:
    return name, True, detail


def _fail(name: str, detail: str) -> Check:
    return name, False, detail


def _check_version() -> Check:
    if __version__ == "0.1.0":
        return _ok("version", __version__)
    return _fail("version", __version__)


def _check_identity() -> Check:
    blob = f"{__author__} {AUTHOR}"
    forbidden = ("Col" + "lin H" + "orton", "Ja" + "ck Al" + "tman", "GodLock" + ".AZ", "Reve" + "aler")
    if any(x in blob for x in forbidden):
        return _fail("identity", "forbidden identity label")
    if "Aziel Eliab" not in blob:
        return _fail("identity", __author__)
    return _ok("identity", AUTHOR)


def _check_hash_stable() -> Check:
    body = {
        "created_at": "2026-09-04T00:00:00Z",
        "engine_version": "0.1.0",
        "kind": "work",
        "node_id": "n" * 64,
        "payload": "desk closed",
        "prev_hash": GENESIS_PREV_HASH,
        "report_hash": "a" * 64,
        "scope": "azieltether",
    }
    a = digest_mapping(body)
    b = digest_mapping(body)
    if a != b or len(a) != 64:
        return _fail("hash", a)
    return _ok("canonical hash", "stable")


def _check_dual_chain() -> Check:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        node = "b" * 64
        chain = Chain.genesis(home / "queue.jsonl", payload="parent", node_id=node, created_at="2026-09-04T00:00:00Z")
        parent = chain[0]
        left = Item.create(
            payload="left",
            prev_hash=parent.hash,
            node_id=node,
            created_at="2026-09-04T00:01:00Z",
        )
        right = Item.create(
            payload="right",
            prev_hash=parent.hash,
            node_id=node,
            created_at="2026-09-04T00:02:00Z",
        )
        chain.append_item(left)
        chain.append_item(right)
        forks = detect_dual_chain(chain.items)
        if len(forks) != 1 or len(forks[0].child_hashes) != 2:
            return _fail("dual-chain", str(forks))
        if left.hash == right.hash:
            return _fail("dual-chain", "same hash")
        result = chain.verify()
        if not result.ok:
            return _fail("dual-chain verify", str(result.errors))
        return _ok("dual-chain", "both children kept")


def _check_json_roundtrip() -> Check:
    from azieltether.jsonio import export_json, import_json

    with tempfile.TemporaryDirectory() as tmp:
        st = Store(Path(tmp) / "home")
        st.chain().append("roundtrip", node_id=st.node_id())
        src = Path(tmp) / "out.json"
        rec = export_json(src, store=st)
        if not rec.get("ok"):
            return _fail("export", str(rec))
        rec2 = import_json(src, store=st)
        if not rec2.get("ok"):
            return _fail("import", str(rec2))
        return _ok("json import/export", "roundtrip")


def _check_tip() -> Check:
    tip = mint_tip(surface="worker", tip_hash="c" * 64, node_id="d" * 64)
    if len(tip.hash) != 64 or tip.surface != "worker":
        return _fail("tip", tip.hash)
    return _ok("lattice tip", tip.surface)


def _check_wires() -> Check:
    try:
        assert_distinct_sockets(TICK_SOCKET, GATE_SOCKET)
        frame = encode_tick(node_id="a" * 64, tip_hash="b" * 64)
        if len(bytes.fromhex(frame["frame"])) != TICK_FRAME_BYTES:
            return _fail("split-wires", "tick frame size")
        if hash_holds(digest_ok=False, votes_for=777):
            return _fail("split-wires", "quorum outvoted hash")
    except Exception as exc:  # noqa: BLE001
        return _fail("split-wires", str(exc))
    return _ok("split-wires", "tick/gate sockets distinct")


def _check_survival() -> Check:
    with tempfile.TemporaryDirectory() as tmp:
        node = "e" * 64
        chain = Chain.genesis(Path(tmp) / "q.jsonl", payload="cold", node_id=node, created_at="2026-09-04T00:00:00Z")
        rec = multiply_cold_copies(chain[0], Path(tmp) / "copies")
        if rec.get("count", 0) < MIN_COLD_COPIES:
            return _fail("cold-copy", "not enough copies")
        pull = single_server_pull([chain[0].hash], [])
        if pull.get("dropped"):
            return _fail("cold-copy", "single-server pull killed local")
        if poison_refused(digest_ok=False, votes_for=99).get("ok"):
            return _fail("cold-copy", "poison accepted")
    return _ok("cold-copy survival", f"{MIN_COLD_COPIES} copies")


def _check_shelf() -> Check:
    from azieltether.store import Store

    rewrite = refuse_rewrite_key({"rewrite_key": "please"})
    if rewrite.get("ok"):
        return _fail("cold-shelf", "rewrite key accepted")
    lie = refuse_lie_to_survive(worker_up_claimed=True, worker_actually_up=False)
    if lie.get("ok"):
        return _fail("cold-shelf", "lie-to-survive accepted")
    slot = refuse_slot("ipfs")
    if slot.get("ok") or slot.get("code") != "SHELF-SLOT-IPFS":
        return _fail("cold-shelf", "ipfs slot claimed live")
    from azieltether.shelf import CNS_OPERATOR_ATTEST, doi_is_live, plane_b_status, refuse_operator_attest

    if doi_is_live("10.5281/zenodo.123456"):
        return _fail("cold-shelf", "Zenodo DOI claimed live")
    if plane_b_status(doi="10.5281/zenodo.123456").get("ok"):
        return _fail("cold-shelf", "invented DOI accepted")
    attest = refuse_operator_attest()
    if attest.get("ok") or attest.get("code") != CNS_OPERATOR_ATTEST:
        return _fail("cold-shelf", "USB LIVE without attest")
    mismatch = verify_sha256(b"hello", "0" * 64)
    if mismatch.get("ok"):
        return _fail("cold-shelf", "hash mismatch accepted")
    with tempfile.TemporaryDirectory() as tmp:
        st = Store(Path(tmp) / "home")
        st.chain().append("shelf", node_id=st.node_id(), created_at="2026-09-04T00:00:00Z")
        rec = seal_shelf(st)
        if not rec.get("ok") or rec.get("spec") != SHELF_SPEC:
            return _fail("cold-shelf", str(rec.get("code")))
        if rec.get("person_id") != PERSON_ID:
            return _fail("cold-shelf", "person @id forked")
    return _ok("cold-shelf tether", "seal + refuse rewrite/lie/ipfs")


def _check_reheal() -> Check:
    from azieltether.reheal import chatter_allowed, decide, refuse_vote_to_fix

    vote = refuse_vote_to_fix(votes_for=99, neighbor_fix="please")
    if vote.get("ok"):
        return _fail("reheal", "neighbor vote-to-fix accepted")
    if chatter_allowed({"body": "nope"}):
        return _fail("reheal", "illegal chatter")
    if not chatter_allowed({"live": 1, "locked": 0, "isolated": 0, "tip_hash": "a" * 64}):
        return _fail("reheal", "legal chatter refused")
    wait = decide(own_tip="a" * 64, actor_node_id="n", failed_node_id="n")
    if wait.get("wait") != "phoenix-WAIT":
        return _fail("reheal", str(wait.get("code")))
    return _ok("reheal", "own tip + phoenix-WAIT; no vote-to-fix")


CHECKS: tuple[Callable[[], Check], ...] = (
    _check_version,
    _check_identity,
    _check_hash_stable,
    _check_dual_chain,
    _check_json_roundtrip,
    _check_tip,
    _check_wires,
    _check_survival,
    _check_shelf,
    _check_reheal,
)


def run_doctor(*, as_json: bool = False) -> int:
    results = []
    failed = 0
    for fn in CHECKS:
        name, ok, detail = fn()
        results.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            failed += 1
        mark = "ok" if ok else "FAIL"
        if not as_json:
            print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    payload = {
        "ok": failed == 0,
        "failed": failed,
        "checks": results,
        "version": __version__,
        "author": AUTHOR,
        "role": "central×decentral software tether",
        "network": False,
        "telemetry": False,
        "vpn": False,
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print("doctor", "passed" if failed == 0 else "failed")
        print("Next: azieltether ui" if failed == 0 else "Next: azieltether doctor")
    return 0 if failed == 0 else 1
