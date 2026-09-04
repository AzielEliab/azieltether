"""Local UI: loopback only, GET / contains AzielTether. Port 8874."""

from __future__ import annotations

import json
import threading
import urllib.request

import pytest

from azieltether.cli import _build_parser
from azieltether.ui import DEFAULT_HOST, DEFAULT_PORT, LOOPBACK, make_server


def test_cli_ui_defaults() -> None:
    args = _build_parser().parse_args(["ui"])
    assert args.host == "127.0.0.1"
    assert args.host == DEFAULT_HOST
    assert args.port == 8874
    assert args.port == DEFAULT_PORT


def test_ui_rejects_non_loopback() -> None:
    with pytest.raises(ValueError, match="loopback"):
        make_server("0.0.0.0", 9)
    assert "127.0.0.1" in LOOPBACK


def test_ui_get_root_and_genesis(tmp_path) -> None:
    httpd = make_server("127.0.0.1", 0, home=tmp_path / "ui-home")
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as resp:
            assert resp.status == 200
            html = resp.read()
        assert b"AzielTether" in html
        assert b"127.0.0.1" in html
        assert b"Prefer central" in html
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["ok"] is True
        assert payload["bind_host"] == "127.0.0.1"
        assert payload["author"] == "Aziel Eliab"
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/genesis",
            data=json.dumps({"payload": "desk closed"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            minted = json.loads(resp.read().decode("utf-8"))
        assert minted["items"]
        assert minted["items"][0]["hash"]
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/verify",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            verified = json.loads(resp.read().decode("utf-8"))
        assert verified["verify"]["ok"] is True
    finally:
        httpd.shutdown()
        httpd.server_close()
