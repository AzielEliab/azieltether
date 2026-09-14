"""DAG store for AzielTether items.

Linear sibling queues (AZ-CLCE) and native dual-chain DAGs both verify
here. Two children of one ``prev_hash`` are a dual-chain. Do not pick a
winner.

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from azieltether.canon import GENESIS_PREV_HASH, canonical_json, digest_mapping, require_hex64
from azieltether.errors import AppendOnlyError, ChainError, ItemError
from azieltether.item import Item
from azieltether.wires import hash_holds

GENESIS_PREV_HASH = GENESIS_PREV_HASH


@dataclass(frozen=True)
class DualFork:
    """Same prev_hash, two or more distinct child hashes. No winner."""

    prev_hash: str
    child_hashes: tuple[str, ...]


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    items: int
    errors: tuple[str, ...]
    tip_hashes: tuple[str, ...]
    first_hash: str | None
    last_hash: str | None
    dual_chain: tuple[DualFork, ...]


def detect_dual_chain(items: Sequence[Mapping[str, Any] | Item]) -> list[DualFork]:
    """Return forks: more than one distinct hash sharing one prev_hash."""
    by_prev: dict[str, list[str]] = {}
    for raw in items:
        data = raw.as_dict() if isinstance(raw, Item) else dict(raw)
        prev = str(data.get("prev_hash") or "")
        digest = str(data.get("hash") or "")
        if not prev or not digest:
            continue
        by_prev.setdefault(prev, [])
        if digest not in by_prev[prev]:
            by_prev[prev].append(digest)
    forks: list[DualFork] = []
    for prev, children in by_prev.items():
        if len(children) > 1:
            forks.append(DualFork(prev_hash=prev, child_hashes=tuple(children)))
    return forks


def _as_dict(item: Mapping[str, Any] | Item) -> dict[str, Any]:
    return item.as_dict() if isinstance(item, Item) else dict(item)


def verify_items(
    items: Sequence[Mapping[str, Any] | Item],
    *,
    votes_for: int = 0,
) -> VerifyResult:
    """Verify hashes and prev links as a DAG. Forks are allowed.

    Hash is absolute: ``votes_for`` cannot flip a broken digest to ok.
    """
    errors: list[str] = []
    known: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for idx, raw in enumerate(items):
        data = _as_dict(raw)
        digest = data.get("hash")
        if not digest:
            errors.append(f"item {idx}: missing hash")
            continue
        try:
            require_hex64("hash", digest)
        except ValueError as exc:
            errors.append(f"item {idx}: {exc}")
            continue
        digest_ok = digest_mapping(data) == digest
        if not hash_holds(digest_ok=digest_ok, votes_for=votes_for):
            errors.append(f"item {idx}: hash mismatch")
        prev = str(data.get("prev_hash") or "")
        if prev != GENESIS_PREV_HASH and prev not in known:
            # prev may appear later in a harvested merge; note only if never seen
            data["_pending_prev"] = prev
        known[str(digest)] = data
        order.append(str(digest))
    for digest, data in known.items():
        prev = str(data.get("prev_hash") or "")
        if prev != GENESIS_PREV_HASH and prev not in known:
            errors.append(f"{digest[:12]}: prev_hash not in store")
    forks = detect_dual_chain(list(known.values()))
    used_as_prev = {str(v.get("prev_hash") or "") for v in known.values()}
    heads = [h for h in known if h not in used_as_prev]
    tip_hashes = tuple(heads) if heads else ((order[-1],) if order else ())
    first = order[0] if order else None
    last = order[-1] if order else None
    return VerifyResult(
        ok=not errors,
        items=len(known),
        errors=tuple(errors),
        tip_hashes=tip_hashes,
        first_hash=first,
        last_hash=last,
        dual_chain=tuple(forks),
    )


class Chain:
    """Append-only JSONL DAG. Edits raise AppendOnlyError."""

    def __init__(self, path: str | Path, items: list[Item] | None = None) -> None:
        self.path = Path(path)
        self._items: list[Item] = list(items or [])

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Item]:
        return iter(self._items)

    def __getitem__(self, idx: int) -> Item:
        return self._items[idx]

    @property
    def items(self) -> list[Item]:
        return list(self._items)

    def hashes(self) -> set[str]:
        return {item.hash for item in self._items}

    def tip_hashes(self) -> list[str]:
        return list(verify_items(self._items).tip_hashes)

    def last_hash(self) -> str:
        if not self._items:
            return GENESIS_PREV_HASH
        return self._items[-1].hash

    def last_good_tip(self) -> str | None:
        """Own last verified prefix tip. Poison stops the walk (fail-closed)."""
        from azieltether.reheal import last_good_tip as _last_good

        return _last_good([item.as_dict() for item in self._items])

    def append_item(self, item: Item) -> Item:
        if item.hash in self.hashes():
            return item
        if self.path.exists():
            existing = self.path.read_text(encoding="utf-8")
            if existing and not existing.endswith("\n"):
                raise AppendOnlyError("refusing to rewrite a mid-file item")
        self._items.append(item)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(item.as_dict()) + "\n")
        return item

    def append(
        self,
        payload: str,
        *,
        node_id: str,
        kind: str = "work",
        scope: str = "azieltether",
        prev_hash: str | None = None,
        created_at: str | None = None,
        extras: Mapping[str, Any] | None = None,
    ) -> Item:
        prev = prev_hash if prev_hash is not None else self.last_hash()
        item = Item.create(
            payload=payload,
            prev_hash=prev,
            node_id=node_id,
            kind=kind,
            scope=scope,
            created_at=created_at,
            extras=extras,
        )
        return self.append_item(item)

    def children_of(self, prev_hash: str) -> list[str]:
        return [item.hash for item in self._items if item.prev_hash == prev_hash]

    def merge(
        self,
        incoming: Iterable[Mapping[str, Any] | Item],
        *,
        operator: bool = True,
        cite: str | None = None,
        lockset: str | None = None,
    ) -> dict[str, Any]:
        """Union by hash. Dual-chain on same-prev conflict. Never rewrite.

        Operator / reconcile may introduce a fork. A peer merge without
        cite+lockset refuses auto-splice (SPLIT THE WIRES partition law).
        """
        from azieltether.wires import cite_ok, partition_rejoin

        added = 0
        skipped = 0
        isolated = False
        for raw in incoming:
            try:
                item = raw if isinstance(raw, Item) else Item.from_mapping(raw)
            except ItemError:
                skipped += 1
                continue
            if item.hash in self.hashes():
                skipped += 1
                continue
            would_fork = bool(self.children_of(item.prev_hash))
            if would_fork and not operator:
                splice = partition_rejoin(cite=cite, lockset=lockset, operator=False)
                if not splice.get("ok") or not cite_ok(cite, lockset):
                    isolated = True
                    skipped += 1
                    continue
            self.append_item(item)
            added += 1
        result = self.verify()
        return {
            "added": added,
            "skipped": skipped,
            "items": result.items,
            "ok": result.ok and not isolated,
            "isolate": isolated,
            "code": "WIRES-NO-AUTO-SPLICE" if isolated else "CHAIN-MERGE",
            "dual_chain": [
                {"prev_hash": f.prev_hash, "child_hashes": list(f.child_hashes)}
                for f in result.dual_chain
            ],
            "tip_hashes": list(result.tip_hashes),
        }

    def refuse_erase(self) -> None:
        raise AppendOnlyError("tip expensive to erase; cold copies stay")

    def verify(self) -> VerifyResult:
        return verify_items(self._items)

    def forks(self) -> list[DualFork]:
        return detect_dual_chain(self._items)

    @classmethod
    def load(cls, path: str | Path) -> Chain:
        pth = Path(path)
        items: list[Item] = []
        if pth.is_file():
            for line in pth.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                items.append(Item.from_mapping(raw))
        return cls(pth, items)

    @classmethod
    def genesis(
        cls,
        path: str | Path,
        *,
        payload: str,
        node_id: str,
        kind: str = "work",
        scope: str = "azieltether",
        created_at: str | None = None,
    ) -> Chain:
        pth = Path(path)
        if pth.exists():
            raise ChainError("genesis refused: chain already exists (append only)")
        chain = cls(pth, [])
        chain.append(
            payload,
            node_id=node_id,
            kind=kind,
            scope=scope,
            prev_hash=GENESIS_PREV_HASH,
            created_at=created_at,
        )
        return chain
