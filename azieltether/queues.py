"""Harvest sibling product tether queues.

AZ-CLCE / SPRE write ``~/.az-clce/tether-queue.jsonl``. AzielTether
batches those items (scopes ``az-clce`` / ``spre``) and reconciles them
to central on restore. Other product homes may appear later.

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from azieltether.chain import Chain
from azieltether.item import Item, ItemError

SIBLING_QUEUES = (
    Path.home() / ".az-clce" / "tether-queue.jsonl",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            items.append(raw)
    return items


def discover_queues(extra: list[Path] | None = None) -> list[Path]:
    found: list[Path] = []
    for path in list(SIBLING_QUEUES) + list(extra or []):
        if path.is_file() and path not in found:
            found.append(path)
    return found


def harvest(chain: Chain, extra: list[Path] | None = None) -> dict[str, Any]:
    """Copy verifying sibling items into the local DAG. Never rewrite."""
    sources: list[dict[str, Any]] = []
    incoming: list[Item] = []
    skipped = 0
    for path in discover_queues(extra):
        rows = read_jsonl(path)
        ok_here = 0
        for raw in rows:
            try:
                item = Item.from_mapping(raw)
            except ItemError:
                skipped += 1
                continue
            incoming.append(item)
            ok_here += 1
        sources.append({"path": str(path), "items": ok_here})
    merged = chain.merge(incoming)
    merged["sources"] = sources
    merged["harvest_skipped"] = skipped
    merged["note"] = (
        "Harvest copies sibling hash-chained queues. Not a VPN. "
        "Public boards stay mesh-free."
    )
    return merged
