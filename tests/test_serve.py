"""Loopback serve and status page."""

from __future__ import annotations

import json
import threading
from urllib.request import Request, urlopen

import pytest

from azieltether.constants import AUTHOR
from azieltether.router import Router
from azieltether.serve import serve, status_page
from azieltether.store import Store
from azieltether.transport import MemoryTransport


def test_status_page_names_office_and_friends(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    router = Router(store, central=MemoryTransport(name="central", up=False), tether=None, peers=[])
    html = status_page(router)
    assert "CLOSED" in html
    assert "Friend computers" in html
    assert AUTHOR in html
    assert "VPN" in html


def test_serve_refuses_non_loopback(tmp_path):
    store = Store(tmp_path)
    router = Router(store, central=None, tether=None, peers=[])
    with pytest.raises(ValueError, match="loopback"):
        serve(host="0.0.0.0", port=19741, router=router)


def test_http_status_and_batch_roundtrip(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    batch = store.mint_batch("godlock", "receipt", {"note": "http"})
    router = Router(
        store,
        central=MemoryTransport(name="central", up=False),
        tether=MemoryTransport(name="tether", up=False),
        peers=[],
    )
    thread = threading.Thread(
        target=serve,
        kwargs={"host": "127.0.0.1", "port": 19742, "router": router},
        daemon=True,
    )
    thread.start()
    import time

    body = None
    for _ in range(40):
        try:
            req = Request("http://127.0.0.1:19742/v1/health", headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=0.5) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            break
        except OSError:
            time.sleep(0.05)
    assert body and body["ok"] is True
    req = Request("http://127.0.0.1:19742/v1/batch?product=godlock", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=2) as resp:
        pulled = json.loads(resp.read().decode("utf-8"))
    assert pulled["count"] == 1
    assert pulled["batches"][0]["hash"] == batch["hash"]
    req = Request("http://127.0.0.1:19742/", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=2) as resp:
        html = resp.read().decode("utf-8")
    assert "AzielTether" in html
    assert "CLOSED" in html
