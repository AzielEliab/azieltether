"""Build a Router from env + last-known peers."""

from __future__ import annotations

import os
from pathlib import Path

from azieltether.constants import (
    BOOTSTRAP_ENV,
    CORPUS_INGEST_ENV,
    GODLOCK_INGEST_ENV,
    PUBLIC_SITES,
    RUNTIME_INGEST_ENV,
    TETHER_BOOTSTRAP,
)
from azieltether.router import Router
from azieltether.store import Store
from azieltether.transport import HttpTransport, ping


def build_router(home: Path | None = None) -> Router:
    store = Store(home)
    store.ensure_node()
    tether_url = os.environ.get(BOOTSTRAP_ENV) or TETHER_BOOTSTRAP
    tether = HttpTransport(tether_url, name="tether")
    central = _product_ingest_transport()
    peers = []
    for record in store.load_peers():
        endpoint = record.get("endpoint")
        if not endpoint or not str(endpoint).startswith(("http://", "https://")):
            continue
        if "127.0.0.1" in str(endpoint) or "localhost" in str(endpoint):
            peers.append(HttpTransport(str(endpoint), name=str(record.get("node_id") or "peer")))
            continue
        peers.append(HttpTransport(str(endpoint), name=str(record.get("node_id") or "peer")))
    return Router(store, central=central, tether=tether, peers=peers)


def _product_ingest_transport() -> HttpTransport | None:
    """Optional product ingest URLs. Never the public HTTPS boards."""
    for env_name, label in (
        (GODLOCK_INGEST_ENV, "godlock-ingest"),
        (CORPUS_INGEST_ENV, "corpus-ingest"),
        (RUNTIME_INGEST_ENV, "runtime-ingest"),
    ):
        url = os.environ.get(env_name)
        if url:
            return HttpTransport(url, name=label)
    return None


def public_site_health() -> dict[str, bool]:
    """Read-only pings. These sites stay mesh-free."""
    return {name: ping(url) for name, url in PUBLIC_SITES.items()}
