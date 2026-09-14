"""HTTP client for central Worker and peer nodes.

Always sends ``User-Agent: Mozilla/5.0``. Timeouts are short. Network
is never required for local append / verify / doctor.

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 AzielTether"
DEFAULT_CENTRAL = "https://azieltether-download-tracker.vibelock.workers.dev"
CENTRAL_ENV = "AZIELTETHER_CENTRAL"
TIMEOUT_ENV = "AZIELTETHER_TIMEOUT"


def central_host() -> str:
    return os.environ.get(CENTRAL_ENV, DEFAULT_CENTRAL).rstrip("/")


def default_timeout() -> float:
    raw = os.environ.get(TIMEOUT_ENV, "2.5").strip()
    try:
        return max(0.4, float(raw))
    except ValueError:
        return 2.5


def http_json(
    url: str,
    *,
    method: str = "GET",
    body: Any | None = None,
    timeout: float | None = None,
    socket: str | None = None,
) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if socket:
        headers["X-Aziel-Socket"] = socket
    req = Request(url, data=payload, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout if timeout is not None else default_timeout()) as resp:
            raw = resp.read().decode("utf-8")
            status = getattr(resp, "status", 200)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"error": raw or str(exc)}
        if not isinstance(parsed, dict):
            parsed = {"error": raw}
        parsed.setdefault("ok", False)
        parsed["http_status"] = exc.code
        parsed["url"] = url
        return parsed
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc), "url": url, "reason": "network"}
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid JSON", "url": url, "http_status": status}
    if not isinstance(parsed, dict):
        return {"ok": False, "error": "JSON object required", "url": url}
    parsed.setdefault("ok", True)
    parsed["http_status"] = status
    parsed["url"] = url
    return parsed


def probe_health(host: str | None = None, *, timeout: float | None = None) -> dict[str, Any]:
    base = (host or central_host()).rstrip("/")
    rec = http_json(base + "/v1/health", timeout=timeout)
    rec["prefer_central"] = bool(rec.get("ok") and rec.get("http_status") == 200)
    return rec


def ingest_item(item: dict[str, Any], *, host: str | None = None) -> dict[str, Any]:
    base = (host or central_host()).rstrip("/")
    return http_json(base + "/v1/ingest", method="POST", body=item)


def ingest_batch(items: list[dict[str, Any]], *, host: str | None = None) -> dict[str, Any]:
    base = (host or central_host()).rstrip("/")
    return http_json(base + "/v1/reconcile", method="POST", body={"items": items})


def post_tip(tip: dict[str, Any], *, host: str | None = None) -> dict[str, Any]:
    base = (host or central_host()).rstrip("/")
    return http_json(base + "/v1/tip", method="POST", body=tip)


def _peer_urls(peer: str, suffix: str) -> list[str]:
    url = peer.rstrip("/")
    if url.endswith(suffix):
        return [url]
    return [url + suffix]


def peer_tick(
    peer: str,
    *,
    node_id: str,
    tip_hash: str,
    socket: str = "tick",
) -> dict[str, Any]:
    """Tick plane: presence + tip hash only. Never a body."""
    from azieltether.wires import TICK_SOCKET, assert_plane_socket, encode_tick

    assert_plane_socket("tick", socket)
    body = encode_tick(node_id=node_id, tip_hash=tip_hash)
    last: dict[str, Any] = {"ok": False, "error": "no peer URL"}
    for candidate in _peer_urls(peer, "/api/tick"):
        last = http_json(candidate, method="POST", body=body, socket=TICK_SOCKET)
        last["peer"] = peer
        last["plane"] = "tick"
        last["socket"] = TICK_SOCKET
        if last.get("ok") or last.get("http_status") == 200:
            return last
    return last


def peer_pull(
    peer: str,
    *,
    cite: str,
    lockset: str,
    want: list[str] | None = None,
    socket: str = "gate",
) -> dict[str, Any]:
    """Gate plane: receiver pulls. Never sender push fan-out."""
    from azieltether.wires import GATE_SOCKET, assert_plane_socket, pull_request

    assert_plane_socket("payload", socket)
    body = pull_request(cite=cite, lockset=lockset, want=want)
    last: dict[str, Any] = {"ok": False, "error": "no peer URL"}
    for candidate in _peer_urls(peer, "/api/payload"):
        last = http_json(candidate, method="POST", body=body, socket=GATE_SOCKET)
        last["peer"] = peer
        last["plane"] = "payload"
        last["socket"] = GATE_SOCKET
        if last.get("ok") or last.get("http_status") == 200:
            return last
    return last


def peer_exchange(
    peer: str,
    *,
    items: list[dict[str, Any]],
    node_id: str,
    tip_hashes: list[str],
) -> dict[str, Any]:
    """SPLIT THE WIRES: tick only. Items are not pushed (no live body sync)."""
    from azieltether.survival import refuse_live_body_sync
    from azieltether.wires import refuse_push_fanout

    _ = items  # law: ignored — receiver pulls; sender does not fan-out
    refused = refuse_push_fanout({"items": items})
    live = refuse_live_body_sync({"items": items}, plane="tick", verified=False)
    tip = tip_hashes[0] if tip_hashes else "0" * 64
    rec = peer_tick(peer, node_id=node_id, tip_hash=tip)
    rec["push_fanout"] = False
    rec["live_body_sync"] = False
    rec["wires"] = refused
    rec["survival"] = live
    rec["tip_hashes"] = tip_hashes
    rec["items"] = []
    return rec
