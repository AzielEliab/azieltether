"""COLD-COPY SURVIVAL — multiply sealed copies; refuse live body sync.

Cold copies are local, verified, hash-absolute replicas. They outlive
the creator and a single-server pull. Tips are expensive to erase.
Poison is refused by fail-closed hash.

Lives beside SPLIT THE WIRES: the tick plane never carries a body;
the gate plane is a cite/lockset pull, not a live sync.

Author: Aziel Eliab only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from azieltether.canon import canonical_json, digest_mapping, require_hex64, sha256_hex
from azieltether.errors import AppendOnlyError, SurvivalError
from azieltether.item import Item
from azieltether.wires import WIRES_SPEC, cite_ok, hash_holds

SURVIVAL_SPEC = "COLD-COPY-SURVIVAL-1.0"
SURVIVAL_AUTHOR = "Aziel Eliab"
MIN_COLD_COPIES = 3
LIVE_BODY_SYNC = False
TIP_ERASE_FREE = False
SINGLE_SERVER_CAN_KILL = False
HASH_ABSOLUTE = True
OUTLIVES_CREATORS = True

LAW = (
    "COLD-COPY SURVIVAL. Multiply cold copies. Refuse live body sync "
    "across the network. A tip is expensive to erase. Unkillable by a "
    "single-server pull. Poison is hard: hash-absolute, fail-closed. "
    "Data outlives creators. Author: Aziel Eliab only."
)


def copy_slots(n: int = MIN_COLD_COPIES) -> tuple[str, ...]:
    count = max(MIN_COLD_COPIES, int(n))
    return tuple(str(i) for i in range(count))


def item_digest_ok(raw: Mapping[str, Any]) -> bool:
    digest = raw.get("hash")
    if not digest:
        return False
    try:
        require_hex64("hash", digest)
    except ValueError:
        return False
    return digest_mapping(raw) == digest


def refuse_live_body_sync(
    body: Mapping[str, Any] | None,
    *,
    plane: str,
    verified: bool = False,
) -> dict[str, Any]:
    """Live (unverified / pushed) bodies do not cross the network."""
    if LIVE_BODY_SYNC:
        return {"ok": True, "code": "SURVIVAL-LIVE-OK", "author": SURVIVAL_AUTHOR}
    items: list[Any] = []
    if isinstance(body, Mapping):
        raw = body.get("items") or body.get("body") or body.get("payload")
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = [raw]
        elif raw and plane != "payload":
            items = [raw]
    if plane == "tick" and items:
        return {
            "ok": False,
            "code": "SURVIVAL-LIVE-BODY-REFUSED",
            "note": "Tick plane is presence + tip only. No live body.",
            "author": SURVIVAL_AUTHOR,
        }
    if items and not verified:
        return {
            "ok": False,
            "code": "SURVIVAL-LIVE-BODY-REFUSED",
            "note": "Refuse live body sync across the network. Cold copies are local.",
            "author": SURVIVAL_AUTHOR,
        }
    return {
        "ok": True,
        "code": "SURVIVAL-COLD-ONLY",
        "live_body_sync": False,
        "author": SURVIVAL_AUTHOR,
    }


def multiply_cold_copies(
    item: Mapping[str, Any] | Item,
    dest_dir: str | Path,
    *,
    n: int = MIN_COLD_COPIES,
) -> dict[str, Any]:
    """Write the same verified item to N local copy slots."""
    raw = item.as_dict() if isinstance(item, Item) else dict(item)
    if not item_digest_ok(raw):
        raise SurvivalError("poison hard: hash-absolute fail-closed")
    root = Path(dest_dir)
    written: list[str] = []
    line = canonical_json(raw) + "\n"
    digest = str(raw["hash"])
    for slot in copy_slots(n):
        path = root / slot / "queue.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        if digest not in existing:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        written.append(str(path))
    return {
        "ok": True,
        "code": "SURVIVAL-MULTIPLY",
        "copies": written,
        "count": len(written),
        "hash": raw["hash"],
        "spec": SURVIVAL_SPEC,
        "author": SURVIVAL_AUTHOR,
    }


def list_cold_copies(dest_dir: str | Path) -> list[Path]:
    root = Path(dest_dir)
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob("*/queue.jsonl") if p.is_file())


def copy_count(dest_dir: str | Path) -> int:
    return len(list_cold_copies(dest_dir))


def erase_tip(
    *,
    operator: bool = False,
    lockset: str | None = None,
    cite: str | None = None,
    dwell_ready: bool = False,
) -> dict[str, Any]:
    """Tips are expensive to erase. Bytes stay; a tombstone is the only door."""
    if TIP_ERASE_FREE:
        return {"ok": True, "code": "SURVIVAL-TIP-ERASED", "author": SURVIVAL_AUTHOR}
    if not (operator and cite_ok(cite, lockset) and dwell_ready):
        raise AppendOnlyError(
            "tip expensive to erase: need operator + cite + lockset + 777s dwell"
        )
    return {
        "ok": True,
        "code": "SURVIVAL-TIP-TOMBSTONE",
        "erased": False,
        "tombstone": True,
        "note": "Append a tombstone. Cold copies of the tip remain. No byte delete.",
        "author": SURVIVAL_AUTHOR,
    }


def refuse_delete_copy(path: str | Path) -> None:
    raise AppendOnlyError("cold copies are append-only; data outlives creators")


def single_server_pull(
    local_hashes: Sequence[str],
    remote_hashes: Sequence[str] | None,
) -> dict[str, Any]:
    """A single-server pull cannot kill local copies."""
    if SINGLE_SERVER_CAN_KILL:
        return {"ok": False, "local": [], "author": SURVIVAL_AUTHOR}
    kept = list(local_hashes)
    remote = list(remote_hashes or [])
    # Remote emptiness or subset never unlinks local.
    return {
        "ok": True,
        "code": "SURVIVAL-UNKILLABLE",
        "local": kept,
        "remote": remote,
        "dropped": [],
        "unkillable": True,
        "author": SURVIVAL_AUTHOR,
    }


def poison_refused(*, digest_ok: bool, votes_for: int = 0) -> dict[str, Any]:
    holds = hash_holds(digest_ok=digest_ok, votes_for=votes_for)
    if not holds:
        return {
            "ok": False,
            "code": "SURVIVAL-POISON-REFUSED",
            "applied": False,
            "hash_absolute": True,
            "author": SURVIVAL_AUTHOR,
        }
    return {"ok": True, "code": "SURVIVAL-HASH-OK", "hash_absolute": True, "author": SURVIVAL_AUTHOR}


def creator_gone(copies: Iterable[Mapping[str, Any]], *, creator_alive: bool) -> dict[str, Any]:
    """Copies remain valid after the creator is gone."""
    sealed = [dict(c) for c in copies if item_digest_ok(c)]
    return {
        "ok": bool(sealed) or not creator_alive,
        "code": "SURVIVAL-OUTLIVES-CREATORS",
        "creator_alive": creator_alive,
        "copies": len(sealed),
        "outlives_creators": OUTLIVES_CREATORS,
        "usable": bool(sealed),
        "author": SURVIVAL_AUTHOR,
    }


def copy_manifest(dest_dir: str | Path) -> dict[str, Any]:
    paths = list_cold_copies(dest_dir)
    hashes: list[str] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(raw, dict) and raw.get("hash"):
                hashes.append(str(raw["hash"]))
    return {
        "ok": True,
        "spec": SURVIVAL_SPEC,
        "copies": [str(p) for p in paths],
        "count": len(paths),
        "hashes": sorted(set(hashes)),
        "min": MIN_COLD_COPIES,
        "author": SURVIVAL_AUTHOR,
    }


def survival_lock(tip_hashes: Iterable[str]) -> str:
    tips = ",".join(sorted({require_hex64("tip", t) for t in tip_hashes}))
    return sha256_hex("azieltether-survival:" + SURVIVAL_SPEC + ":" + tips)


def law_card() -> dict[str, Any]:
    return {
        "ok": True,
        "spec": SURVIVAL_SPEC,
        "wires_spec": WIRES_SPEC,
        "product": "azieltether",
        "author": SURVIVAL_AUTHOR,
        "identity": SURVIVAL_AUTHOR,
        "min_cold_copies": MIN_COLD_COPIES,
        "live_body_sync": LIVE_BODY_SYNC,
        "tip_erase_free": TIP_ERASE_FREE,
        "single_server_can_kill": SINGLE_SERVER_CAN_KILL,
        "hash_absolute": HASH_ABSOLUTE,
        "outlives_creators": OUTLIVES_CREATORS,
        "law": LAW,
    }
