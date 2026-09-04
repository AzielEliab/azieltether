"""Local node identity, peer directory, and batch backlog."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from azieltether.chain import ChainError, create_batch, verify_batch
from azieltether.constants import HOME_ENV, PRODUCT, SCOPES, VERSION
from azieltether.crypto import generate_keypair, node_id_from_pubkey


class Store:
    def __init__(self, home: Path | None = None) -> None:
        self.home = Path(home) if home is not None else default_home()
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / "batches").mkdir(exist_ok=True)

    @property
    def node_path(self) -> Path:
        return self.home / "node.json"

    @property
    def peers_path(self) -> Path:
        return self.home / "peers.json"

    @property
    def backlog_path(self) -> Path:
        return self.home / "backlog.json"

    def ensure_node(self) -> dict[str, Any]:
        if self.node_path.exists():
            data = self._read(self.node_path)
            if not data.get("node_id") or not data.get("pubkey") or not data.get("private"):
                raise ChainError("node.json is missing node_id, pubkey, or private")
            return data
        private_b64, public_b64 = generate_keypair()
        record = {
            "product": PRODUCT,
            "version": VERSION,
            "author": "Aziel Eliab",
            "node_id": node_id_from_pubkey(public_b64),
            "pubkey": public_b64,
            "private": private_b64,
            "endpoint": "http://127.0.0.1:19740",
        }
        self._write(self.node_path, record)
        return record

    def load_node(self) -> dict[str, Any]:
        return self.ensure_node()

    def public_node(self) -> dict[str, Any]:
        node = self.load_node()
        return {
            "node_id": node["node_id"],
            "pubkey": node["pubkey"],
            "endpoint": node.get("endpoint") or "http://127.0.0.1:19740",
            "product": PRODUCT,
            "version": VERSION,
        }

    def set_endpoint(self, endpoint: str) -> None:
        node = self.load_node()
        node["endpoint"] = endpoint
        self._write(self.node_path, node)

    def load_peers(self) -> list[dict[str, Any]]:
        if not self.peers_path.exists():
            return []
        data = self._read(self.peers_path)
        peers = data.get("peers") if isinstance(data, dict) else data
        if not isinstance(peers, list):
            return []
        return [p for p in peers if isinstance(p, dict)]

    def save_peers(self, peers: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        seen: dict[str, dict[str, Any]] = {}
        for peer in peers:
            node_id = str(peer.get("node_id") or "")
            if not node_id:
                continue
            seen[node_id] = dict(peer)
        out = list(seen.values())
        self._write(self.peers_path, {"product": PRODUCT, "peers": out})
        return out

    def merge_peers(self, incoming: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return self.save_peers([*self.load_peers(), *incoming])

    def remember_peer(self, peer: Mapping[str, Any]) -> list[dict[str, Any]]:
        return self.merge_peers([peer])

    def batches_path(self, scope: str) -> Path:
        if scope not in SCOPES:
            raise ChainError(f"unknown scope {scope!r}")
        return self.home / "batches" / f"{scope}.json"

    def load_batches(self, scope: str) -> list[dict[str, Any]]:
        path = self.batches_path(scope)
        if not path.exists():
            return []
        data = self._read(path)
        batches = data.get("batches") if isinstance(data, dict) else data
        if not isinstance(batches, list):
            return []
        return [b for b in batches if isinstance(b, dict)]

    def tip_hash(self, scope: str) -> str | None:
        batches = self.load_batches(scope)
        if not batches:
            return None
        return str(batches[-1].get("hash"))

    def accept_batch(self, batch: Mapping[str, Any]) -> dict[str, Any]:
        verified = verify_batch(dict(batch))
        scope = str(verified["scope"])
        existing = self.load_batches(scope)
        if any(item.get("hash") == verified["hash"] for item in existing):
            return verified
        tip = existing[-1]["hash"] if existing else None
        if existing and verified["prev_hash"] != tip:
            raise ChainError("batch prev_hash is not the current tip")
        existing.append(verified)
        self._write(
            self.batches_path(scope),
            {"product": PRODUCT, "scope": scope, "batches": existing},
        )
        return verified

    def mint_batch(self, scope: str, kind: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        node = self.load_node()
        from azieltether.constants import GENESIS_PREV_HASH

        prev = self.tip_hash(scope) or GENESIS_PREV_HASH
        batch = create_batch(
            private_b64=node["private"],
            public_b64=node["pubkey"],
            node_id=node["node_id"],
            scope=scope,
            kind=kind,
            payload=payload,
            prev_hash=prev,
        )
        return self.accept_batch(batch)

    def load_backlog(self) -> list[dict[str, Any]]:
        if not self.backlog_path.exists():
            return []
        data = self._read(self.backlog_path)
        items = data.get("items") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return []
        return [i for i in items if isinstance(i, dict)]

    def enqueue_backlog(self, batch: Mapping[str, Any]) -> None:
        items = self.load_backlog()
        digest = batch.get("hash")
        if any(item.get("hash") == digest for item in items):
            return
        items.append(dict(batch))
        self._write(self.backlog_path, {"product": PRODUCT, "items": items})

    def remove_backlog(self, digest: str) -> None:
        items = [item for item in self.load_backlog() if item.get("hash") != digest]
        self._write(self.backlog_path, {"product": PRODUCT, "items": items})

    def chain_ok(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        for scope in SCOPES:
            batches = self.load_batches(scope)
            if not batches:
                continue
            try:
                from azieltether.chain import verify_batch

                expected = batches[0]["prev_hash"]
                for batch in batches:
                    verify_batch(batch, expected_prev=expected)
                    expected = batch["hash"]
            except (ChainError, KeyError) as exc:
                errors.append(f"{scope}: {exc}")
        return (not errors), errors

    def status(self) -> dict[str, Any]:
        node = self.public_node()
        chain_ok, errors = self.chain_ok()
        by_scope = {scope: len(self.load_batches(scope)) for scope in SCOPES}
        return {
            "product": PRODUCT,
            "version": VERSION,
            "author": "Aziel Eliab",
            "node_id": node["node_id"],
            "pubkey": node["pubkey"],
            "endpoint": node["endpoint"],
            "peer_count": len(self.load_peers()),
            "backlog": len(self.load_backlog()),
            "batches": by_scope,
            "chain_ok": chain_ok,
            "chain_errors": errors,
        }

    def _read(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(path)


def default_home() -> Path:
    override = os.environ.get(HOME_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".azieltether"
