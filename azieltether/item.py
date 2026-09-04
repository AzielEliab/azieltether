"""Hash-chained tether items.

Native AzielTether items plus AZ-CLCE / SPRE queue items (scope
``az-clce`` / ``spre``). Both use the same hash contract: SHA-256 of
canonical JSON excluding ``hash``.

Author: Aziel Eliab.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from azieltether.canon import (
    GENESIS_PREV_HASH,
    canonical_json,
    digest_mapping,
    require_hex64,
    sha256_hex,
)
from azieltether.errors import ItemError

KINDS = frozenset({"work", "tip", "peer-sync", "reconcile", "dual-fork", "ingest", "harvest"})
SCOPES = frozenset(
    {
        "azieltether",
        "az-clce",
        "spre",
        "godlock",
        "corpus",
        "temporallock",
        "staticclock",
        "peer",
    }
)
ENGINE_VERSION = "0.1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def digest_item(item: Mapping[str, Any]) -> str:
    return digest_mapping(item)


def report_hash_of(payload: str) -> str:
    return sha256_hex(payload)


@dataclass(frozen=True)
class Item:
    """One append-only tether item.

    ``raw`` is the exact mapping that was hashed (native or sibling).
    ``as_dict`` returns that mapping so harvest never rewrites a hash.
    """

    created_at: str
    engine_version: str
    kind: str
    node_id: str
    payload: str
    prev_hash: str
    report_hash: str
    scope: str
    hash: str
    extras: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        if self.raw:
            return dict(self.raw)
        body: dict[str, Any] = {
            "created_at": self.created_at,
            "engine_version": self.engine_version,
            "kind": self.kind,
            "node_id": self.node_id,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "report_hash": self.report_hash,
            "scope": self.scope,
            "hash": self.hash,
        }
        for key, value in self.extras.items():
            if key not in body:
                body[key] = value
        return body

    def verify_hash(self) -> bool:
        return digest_item(self.as_dict()) == self.hash

    @classmethod
    def create(
        cls,
        *,
        payload: str,
        prev_hash: str = GENESIS_PREV_HASH,
        node_id: str,
        kind: str = "work",
        scope: str = "azieltether",
        created_at: str | None = None,
        extras: Mapping[str, Any] | None = None,
    ) -> Item:
        if not str(payload).strip():
            raise ItemError("payload is required")
        if kind not in KINDS:
            raise ItemError(f"kind must be one of {sorted(KINDS)}")
        if scope not in SCOPES:
            raise ItemError(f"scope must be one of {sorted(SCOPES)}")
        try:
            prev = require_hex64("prev_hash", prev_hash)
        except ValueError as exc:
            raise ItemError(str(exc)) from exc
        if not str(node_id).strip():
            raise ItemError("node_id is required")
        ts = created_at or utc_now()
        extra = dict(extras or {})
        body: dict[str, Any] = {
            "created_at": ts,
            "engine_version": ENGINE_VERSION,
            "kind": kind,
            "node_id": str(node_id),
            "payload": str(payload),
            "prev_hash": prev,
            "report_hash": report_hash_of(str(payload)),
            "scope": scope,
        }
        for key, value in extra.items():
            if key not in body and key != "hash":
                body[key] = value
        digest = digest_mapping(body)
        stored = dict(body)
        stored["hash"] = digest
        return cls(
            created_at=ts,
            engine_version=ENGINE_VERSION,
            kind=kind,
            node_id=str(node_id),
            payload=str(payload),
            prev_hash=prev,
            report_hash=body["report_hash"],
            scope=scope,
            hash=digest,
            extras=extra,
            raw=stored,
        )

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> Item:
        """Load a native or sibling (AZ-CLCE) item. Does not rewrite fields."""
        if not isinstance(raw, Mapping):
            raise ItemError("item must be an object")
        data = dict(raw)
        digest = data.get("hash")
        if not digest:
            raise ItemError("hash is required")
        try:
            require_hex64("hash", digest)
            if data.get("prev_hash"):
                require_hex64("prev_hash", data["prev_hash"])
        except ValueError as exc:
            raise ItemError(str(exc)) from exc
        if digest_mapping(data) != digest:
            raise ItemError("hash mismatch")
        extras = {
            k: v
            for k, v in data.items()
            if k
            not in {
                "created_at",
                "engine_version",
                "kind",
                "node_id",
                "payload",
                "prev_hash",
                "report_hash",
                "scope",
                "hash",
            }
        }
        payload = str(data.get("payload") or data.get("report_hash") or "")
        return cls(
            created_at=str(data.get("created_at") or ""),
            engine_version=str(data.get("engine_version") or ENGINE_VERSION),
            kind=str(data.get("kind") or "work"),
            node_id=str(data.get("node_id") or ""),
            payload=payload,
            prev_hash=str(data.get("prev_hash") or GENESIS_PREV_HASH),
            report_hash=str(data.get("report_hash") or report_hash_of(payload)),
            scope=str(data.get("scope") or "azieltether"),
            hash=str(digest),
            extras=extras,
            raw=dict(data),
        )


def sibling_item_ok(raw: Mapping[str, Any]) -> bool:
    """True when a mapping verifies under the shared hash contract."""
    try:
        Item.from_mapping(raw)
        return True
    except ItemError:
        return False


def canonical_line(item: Mapping[str, Any]) -> str:
    return canonical_json(item)
