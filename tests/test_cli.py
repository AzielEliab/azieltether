"""CLI: version, genesis, append, verify, dual-chain."""

from __future__ import annotations

import json
from pathlib import Path

from azieltether import __version__
from azieltether.cli import main


def test_cli_version(capsys) -> None:
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == f"azieltether {__version__}"


def test_cli_genesis_append_verify(tmp_path: Path, capsys) -> None:
    home = tmp_path / "home"
    rc = main(["--home", str(home), "genesis", "--payload", "sky overcast", "--timestamp", "2026-09-04T00:00:00Z"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "genesis"

    rc = main(["--home", str(home), "append", "--payload", "rain began", "--timestamp", "2026-09-04T00:01:00Z"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "appended"

    rc = main(["--home", str(home), "verify"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["items"] == 2


def test_cli_dual_chain(tmp_path: Path, capsys) -> None:
    home = tmp_path / "home"
    assert main(["--home", str(home), "genesis", "--payload", "p"]) == 0
    capsys.readouterr()
    rc = main(["--home", str(home), "dual-chain"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["winner"] is None
    assert payload["author"] == "Aziel Eliab"


def test_cli_status_and_node_id(tmp_path: Path, capsys) -> None:
    home = tmp_path / "home"
    assert main(["--home", str(home), "init"]) == 0
    capsys.readouterr()
    assert main(["--home", str(home), "node-id"]) == 0
    node = capsys.readouterr().out.strip()
    assert len(node) == 64
