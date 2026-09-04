"""Injectable transports for central, tether bootstrap, and peers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from azieltether.chain import ChainError, verify_batch
from azieltether.constants import USER_AGENT
from azieltether.crypto import canonical_json


class Transport(Protocol):
    name: str

    def health(self) -> bool: ...
    def announce(self, node: dict[str, Any]) -> dict[str, Any]: ...
    def peers(self, product: str = "*") -> list[dict[str, Any]]: ...
    def push_batch(self, batch: dict[str, Any]) -> dict[str, Any]: ...
    def pull_batches(self, since: str = "", product: str = "*") -> list[dict[str, Any]]: ...


@dataclass
class MemoryTransport:
    """In-process stand-in used by tests. Not a network."""

    name: str = "memory"
    up: bool = True
    announced: list[dict[str, Any]] = field(default_factory=list)
    held: list[dict[str, Any]] = field(default_factory=list)
    directory: list[dict[str, Any]] = field(default_factory=list)
    fail_push: bool = False

    def health(self) -> bool:
        return bool(self.up)

    def announce(self, node: dict[str, Any]) -> dict[str, Any]:
        if not self.up:
            raise TransportError(f"{self.name} is down")
        self.announced.append(dict(node))
        self.directory.append(dict(node))
        return {"ok": True, "via": self.name, "node_id": node.get("node_id")}

    def peers(self, product: str = "*") -> list[dict[str, Any]]:
        if not self.up:
            raise TransportError(f"{self.name} is down")
        if product in {"", "*"}:
            return list(self.directory)
        return [p for p in self.directory if p.get("product") == product or product in (p.get("scopes") or [])]

    def push_batch(self, batch: dict[str, Any]) -> dict[str, Any]:
        if not self.up:
            raise TransportError(f"{self.name} is down")
        if self.fail_push:
            raise TransportError(f"{self.name} refused push")
        verified = verify_batch(batch)
        if any(item.get("hash") == verified["hash"] for item in self.held):
            return {"ok": True, "via": self.name, "duplicate": True, "hash": verified["hash"]}
        self.held.append(verified)
        return {"ok": True, "via": self.name, "hash": verified["hash"]}

    def pull_batches(self, since: str = "", product: str = "*") -> list[dict[str, Any]]:
        if not self.up:
            raise TransportError(f"{self.name} is down")
        out = []
        for batch in self.held:
            if product not in {"", "*"} and batch.get("scope") != product:
                continue
            if since and str(batch.get("created_at") or "") < since:
                continue
            out.append(batch)
        return out


class TransportError(RuntimeError):
    """Remote host failed or is unreachable."""


class HttpTransport:
    def __init__(self, base: str, name: str = "http") -> None:
        self.base = base.rstrip("/")
        self.name = name
        self.timeout = 5.0

    def health(self) -> bool:
        for path in ("/v1/tether/health", "/v1/health", "/"):
            try:
                data = self._json("GET", path)
            except TransportError:
                continue
            if isinstance(data, dict) and data.get("ok") is False:
                continue
            return True
        return False

    def announce(self, node: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._json("POST", "/v1/tether/announce", node)
        except TransportError:
            return self._json("POST", "/v1/announce", node)

    def peers(self, product: str = "*") -> list[dict[str, Any]]:
        q = f"?product={product}" if product else ""
        try:
            data = self._json("GET", f"/v1/tether/peers{q}")
        except TransportError:
            data = self._json("GET", f"/v1/peers{q}")
        if isinstance(data, dict):
            peers = data.get("peers") or data.get("items") or []
            return [p for p in peers if isinstance(p, dict)]
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict)]
        return []

    def push_batch(self, batch: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._json("POST", "/v1/tether/batch", batch)
        except TransportError:
            return self._json("POST", "/v1/batch", batch)

    def pull_batches(self, since: str = "", product: str = "*") -> list[dict[str, Any]]:
        q = []
        if since:
            q.append(f"since={since}")
        if product:
            q.append(f"product={product}")
        suffix = ("?" + "&".join(q)) if q else ""
        try:
            data = self._json("GET", f"/v1/tether/batch{suffix}")
        except TransportError:
            data = self._json("GET", f"/v1/batch{suffix}")
        if isinstance(data, dict):
            batches = data.get("batches") or data.get("items") or []
            return [b for b in batches if isinstance(b, dict)]
        if isinstance(data, list):
            return [b for b in data if isinstance(b, dict)]
        return []

    def _json(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = self.base + path
        data = None if body is None else canonical_json(body).encode("utf-8")
        req = Request(
            url,
            data=data,
            method=method,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except HTTPError as exc:
            raise TransportError(f"{self.name} HTTP {exc.code} {path}") from exc
        except URLError as exc:
            raise TransportError(f"{self.name} unreachable: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TransportError(f"{self.name} timeout") from exc
        if not raw:
            return {"ok": True}
        try:
            import json

            return json.loads(raw.decode("utf-8"))
        except ValueError as exc:
            raise TransportError(f"{self.name} returned non-JSON") from exc


def ping(url: str, timeout: float = 4.0) -> bool:
    req = Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 500
    except (HTTPError, URLError, TimeoutError, OSError):
        return False
