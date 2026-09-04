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


CHECKS: tuple[Callable[[], Check], ...] = (
    _check_version,
    _check_identity,
    _check_hash_stable,
    _check_dual_chain,
    _check_json_roundtrip,
    _check_tip,
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
    return 0 if failed == 0 else 1
