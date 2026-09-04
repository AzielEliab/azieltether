"""On-disk node home for AzielTether.

Default: ``~/.azieltether`` (override ``AZIELTETHER_HOME``).

    node.json     local node identity
    queue.jsonl   append-only DAG
    tips.json     lattice tips per surface
    peers.json    peer URLs for sync-when-down
    state.json    last pulse / mode

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from azieltether.canon import sha256_hex
from azieltether.chain import Chain
from azieltether.item import utc_now

HOME_ENV = "AZIELTETHER_HOME"
DEFAULT_DIRNAME = ".azieltether"


def default_home() -> Path:
    env = os.environ.get(HOME_ENV, "").strip()
    if env:
        return Path(env)
    return Path.home() / DEFAULT_DIRNAME


class Store:
    def __init__(self, home: str | Path | None = None) -> None:
        self.home = Path(home) if home is not None else default_home()
        self.home.mkdir(parents=True, exist_ok=True)

    @property
    def node_path(self) -> Path:
        return self.home / "node.json"

    @property
    def queue_path(self) -> Path:
        return self.home / "queue.jsonl"

    @property
    def tips_path(self) -> Path:
        return self.home / "tips.json"

    @property
    def peers_path(self) -> Path:
        return self.home / "peers.json"

    @property
    def state_path(self) -> Path:
        return self.home / "state.json"

    def _read_json(self, path: Path, fallback: Any) -> Any:
        if not path.is_file():
            return fallback
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return fallback

    def _write_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def node_id(self) -> str:
        rec = self._read_json(self.node_path, {})
        if isinstance(rec, dict) and rec.get("node_id"):
            return str(rec["node_id"])
        seed = uuid.uuid4().hex + utc_now()
        node_id = sha256_hex("azieltether-node:" + seed)
        rec = {
            "product": "azieltether",
            "author": "Aziel Eliab",
            "node_id": node_id,
            "created_at": utc_now(),
        }
        self._write_json(self.node_path, rec)
        return node_id

    def node_record(self) -> dict[str, Any]:
        self.node_id()
        rec = self._read_json(self.node_path, {})
        return rec if isinstance(rec, dict) else {}

    def chain(self) -> Chain:
        return Chain.load(self.queue_path)

    def peers(self) -> list[str]:
        rec = self._read_json(self.peers_path, {"peers": []})
        if isinstance(rec, dict):
            peers = rec.get("peers") or []
            return [str(p).rstrip("/") for p in peers if str(p).strip()]
        if isinstance(rec, list):
            return [str(p).rstrip("/") for p in rec if str(p).strip()]
        return []

    def set_peers(self, peers: list[str]) -> list[str]:
        clean = [str(p).rstrip("/") for p in peers if str(p).strip()]
        self._write_json(self.peers_path, {"peers": clean, "author": "Aziel Eliab"})
        return clean

    def add_peer(self, url: str) -> list[str]:
        peers = self.peers()
        url = url.rstrip("/")
        if url and url not in peers:
            peers.append(url)
        return self.set_peers(peers)

    def tips(self) -> dict[str, Any]:
        rec = self._read_json(self.tips_path, {"surfaces": {}})
        return rec if isinstance(rec, dict) else {"surfaces": {}}

    def write_tips(self, tips: dict[str, Any]) -> None:
        tips = dict(tips)
        tips.setdefault("author", "Aziel Eliab")
        tips.setdefault("product", "azieltether")
        self._write_json(self.tips_path, tips)

    def state(self) -> dict[str, Any]:
        rec = self._read_json(self.state_path, {})
        return rec if isinstance(rec, dict) else {}

    def write_state(self, state: dict[str, Any]) -> None:
        state = dict(state)
        state.setdefault("author", "Aziel Eliab")
        state["updated_at"] = utc_now()
        self._write_json(self.state_path, state)
