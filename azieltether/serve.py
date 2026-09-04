"""Loopback node HTTP + a plain-language status page."""

from __future__ import annotations

import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from azieltether.chain import ChainError
from azieltether.constants import (
    AUTHOR,
    DEFAULT_HOST,
    DEFAULT_PORT,
    LOOPBACK_HOSTS,
    MOTTO,
    NOTE_NOT_VPN,
    PRODUCT,
    VERSION,
)
from azieltether.hooks import on_transfer, transfer_event
from azieltether.router import Router
from azieltether.store import Store
from azieltether.transport import TransportError


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, router: Router | None = None) -> None:
    if host not in LOOPBACK_HOSTS:
        raise ValueError("AzielTether serve binds loopback only (127.0.0.1 / localhost / ::1).")
    if router is None:
        from azieltether.wiring import build_router

        router = build_router()
    router.store.set_endpoint(f"http://{host}:{port}")
    handler = partial(TetherHandler, router=router)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"AzielTether {VERSION} on http://{host}:{port} (this computer only)")
    print(MOTTO)
    print(f"Author: {AUTHOR}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


class TetherHandler(BaseHTTPRequestHandler):
    router: Router

    def __init__(self, *args: Any, router: Router, **kwargs: Any) -> None:
        self.router = router
        super().__init__(*args, **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, b"", "text/plain")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        store: Store = self.router.store
        if path == "/":
            self._send(200, status_page(self.router).encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/v1/health":
            self._json(200, {"ok": True, "product": PRODUCT, "version": VERSION, "author": AUTHOR})
            return
        if path == "/v1/status":
            self._json(200, self.router.doctor())
            return
        if path == "/v1/skill":
            from azieltether.skilltext import SKILL

            self._send(200, SKILL.encode("utf-8"), "text/markdown; charset=utf-8")
            return
        if path == "/v1/peers":
            product = (query.get("product") or ["*"])[0]
            peers = store.load_peers()
            if product not in {"", "*"}:
                peers = [p for p in peers if p.get("product") == product]
            self._json(200, {"ok": True, "peers": peers, "count": len(peers)})
            return
        if path == "/v1/batch":
            since = (query.get("since") or [""])[0]
            product = (query.get("product") or query.get("scope") or ["*"])[0]
            batches = []
            scopes = [product] if product not in {"", "*"} else list(store.status()["batches"])
            for scope in scopes:
                for batch in store.load_batches(scope):
                    if since and str(batch.get("created_at") or "") < since:
                        continue
                    batches.append(batch)
            self._json(200, {"ok": True, "batches": batches, "count": len(batches)})
            return
        if path == "/v1/conflicts":
            self._json(200, self.router.conflict_status())
            return
        if path == "/v1/lattice":
            self._json(200, self.router.lattice_status())
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except ValueError:
            self._json(400, {"error": "JSON body required"})
            return
        if not isinstance(body, dict):
            self._json(400, {"error": "JSON object required"})
            return
        try:
            if path == "/v1/announce":
                peer = {
                    "node_id": body.get("node_id"),
                    "pubkey": body.get("pubkey"),
                    "endpoint": body.get("endpoint"),
                    "product": body.get("product") or PRODUCT,
                }
                if not peer["node_id"] or not peer["pubkey"]:
                    self._json(400, {"error": "node_id and pubkey are required"})
                    return
                self.router.store.remember_peer(peer)
                self._json(200, {"ok": True, "via": "local-serve", "peers": len(self.router.store.load_peers())})
                return
            if path == "/v1/batch":
                accepted = self.router.store.accept_batch(body)
                hooks = on_transfer(
                    transfer_event(
                        direction="download",
                        batch=accepted,
                        via="local-serve",
                        store=self.router.store,
                        offline=self.router.route_name() == "local",
                    )
                )
                conflicted = self.router.store.last_accept == "precedent"
                self._json(
                    200,
                    {
                        "ok": True,
                        "via": "precedent" if conflicted else "local-serve",
                        "hash": accepted["hash"],
                        "conflict": conflicted,
                        "hooks": hooks,
                    },
                )
                return
        except (ChainError, TransportError, KeyError, TypeError) as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(404, {"error": "not found"})

    def _json(self, status: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body, indent=2, ensure_ascii=False).encode("utf-8")
        self._send(status, payload, "application/json; charset=utf-8")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        if body:
            self.wfile.write(body)


def status_page(router: Router) -> str:
    doctor = router.doctor()
    central_up = doctor["prefer_central"]
    office = "OPEN" if central_up else "CLOSED"
    office_color = "#1b7f4a" if central_up else "#a33b3b"
    peers = doctor.get("peer_count") or 0
    backlog = doctor.get("backlog") or 0
    batches = doctor.get("batches") or {}
    batch_total = sum(int(v) for v in batches.values())
    lattice = doctor.get("lattice_anchors") or 0
    conflicts = doctor.get("precedent_length") or 0
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AzielTether status</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{
      font: 20px/1.45 system-ui, sans-serif;
      max-width: 40rem;
      margin: 2.5rem auto;
      padding: 0 1.2rem 3rem;
      background: #101318;
      color: #eef1f6;
    }}
    h1 {{ font-size: 2rem; margin: 0 0 .4rem; }}
    .lead {{ color: #b7c0ce; margin: 0 0 1.4rem; }}
    .cards {{ display: grid; gap: .8rem; }}
    .card {{
      border: 1px solid #2b3342;
      border-radius: 14px;
      padding: 1rem 1.1rem;
      background: #171c26;
    }}
    .big {{
      font-size: 2.1rem;
      font-weight: 750;
      margin: .15rem 0 0;
      color: {office_color};
    }}
    .label {{ color: #9aa6b8; font-size: 1rem; }}
    .note {{
      margin-top: 1.3rem;
      padding: 1rem 1.1rem;
      border-radius: 12px;
      background: #1d2430;
      border: 1px solid #334056;
    }}
    code {{ font-size: .92em; }}
    footer {{ margin-top: 1.5rem; color: #8b95a6; font-size: .95rem; }}
  </style>
</head>
<body>
  <h1>AzielTether</h1>
  <p class="lead">A homework folder for software. If the main office is closed, classmates can still trade work. When the office opens, everyone turns the folder in.</p>
  <div class="cards">
    <section class="card">
      <div class="label">Main office (central)</div>
      <p class="big">{office}</p>
    </section>
    <section class="card">
      <div class="label">Friend computers that downloaded this software</div>
      <p class="big" style="color:#d7deea">{peers}</p>
    </section>
    <section class="card">
      <div class="label">Work waiting to send back</div>
      <p class="big" style="color:#e6c36a">{backlog}</p>
    </section>
    <section class="card">
      <div class="label">Batches already on this computer</div>
      <p class="big" style="color:#d7deea">{batch_total}</p>
    </section>
    <section class="card">
      <div class="label">Survival bookmarks (lattice anchors)</div>
      <p class="big" style="color:#d7deea">{lattice}</p>
    </section>
    <section class="card">
      <div class="label">Conflict notes (second chain — first chain was not erased)</div>
      <p class="big" style="color:#e6c36a">{conflicts}</p>
    </section>
  </div>
  <div class="note">
    <p><strong>What this is:</strong> a tether for receipts, public library envelopes, catalog events, and a shared survival lattice. If one product folder survives, the others can find their last page from the bookmarks.</p>
    <p><strong>What this is not:</strong> a VPN, a secret network, or a way to change the public websites. Those sites stay ordinary HTTPS.</p>
    <p>If two folders accidentally share the same last page, we do not pretend they are one folder. We write a second notebook that remembers both.</p>
    <p>Commands: <code>azieltether doctor</code> · <code>azieltether announce</code> · <code>azieltether push</code> · <code>azieltether pull</code> · <code>azieltether reconcile</code> · <code>azieltether conflict-status</code> · <code>azieltether anchor</code></p>
  </div>
  <footer>Author Aziel Eliab · {PRODUCT} {VERSION} · loopback only · {NOTE_NOT_VPN}</footer>
</body>
</html>
"""
