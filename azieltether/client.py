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
) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
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


def peer_exchange(
    peer: str,
    *,
    items: list[dict[str, Any]],
    node_id: str,
    tip_hashes: list[str],
) -> dict[str, Any]:
    url = peer.rstrip("/")
    if not url.endswith("/api/peer") and "/v1/peer-preview" not in url:
        # Prefer local UI peer API; fall back to Worker preview.
        candidates = [url + "/api/peer", url + "/v1/peer-preview"]
    else:
        candidates = [url]
    last: dict[str, Any] = {"ok": False, "error": "no peer URL"}
    body = {
        "node_id": node_id,
        "tip_hashes": tip_hashes,
        "items": items,
        "author": "Aziel Eliab",
        "product": "azieltether",
    }
    for candidate in candidates:
        last = http_json(candidate, method="POST", body=body)
        if last.get("ok") or last.get("http_status") == 200:
            last["peer"] = peer
            return last
    last["peer"] = peer
    return last
