"""CLI: version, genesis, append, verify, dual-chain."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from azieltether import __version__
from azieltether.cli import main


def test_cli_version(capsys) -> None:
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == f"azieltether {__version__}"


def test_cli_genesis_append_verify(tmp_path: Path, capsys) -> None:
    home = tmp_path / "home"
    rc = main(["--home", str(home), "--json", "genesis", "--payload", "sky overcast", "--timestamp", "2026-09-04T00:00:00Z"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "genesis"

    rc = main(["--home", str(home), "append", "--payload", "rain began", "--timestamp", "2026-09-04T00:01:00Z", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "appended"

    rc = main(["--home", str(home), "--json", "verify"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["items"] == 2


def test_cli_dual_chain(tmp_path: Path, capsys) -> None:
    home = tmp_path / "home"
    assert main(["--home", str(home), "genesis", "--payload", "p"]) == 0
    capsys.readouterr()
    rc = main(["--home", str(home), "--json", "dual-chain"])
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


def test_cli_wires_and_survival(tmp_path: Path, capsys) -> None:
    home = tmp_path / "home"
    assert main(["--home", str(home), "genesis", "--payload", "cold"]) == 0
    capsys.readouterr()
    assert main(["--home", str(home), "--json", "wires"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["wires"]["spec"] == "SPLIT-THE-WIRES-1.0"
    assert payload["survival"]["spec"] == "COLD-COPY-SURVIVAL-1.0"
    assert payload["reheal"]["spec"] == "REHEAL-1.0"
    assert main(["--home", str(home), "--json", "reheal"]) == 0
    rh = json.loads(capsys.readouterr().out)
    assert rh["reheal"]["wait"] == "phoenix-WAIT"
    assert rh["spec"] == "REHEAL-1.0"
    assert main(["--home", str(home), "--json", "survival"]) == 0
    surv = json.loads(capsys.readouterr().out)
    assert surv["multiply"]["count"] >= 3
    assert main(["--home", str(home), "--json", "shelf"]) == 0
    shelf = json.loads(capsys.readouterr().out)
    assert shelf["shelf"]["spec"] == "COLD-SHELF-TETHER-1.0"
    assert shelf["shelf"]["person_id"] == "https://www.azieleliab.com/#aziel"
    assert main(["--home", str(home), "--json", "shelf", "seal"]) == 0
    sealed = json.loads(capsys.readouterr().out)
    assert sealed["ok"] is True
    assert sealed["code"] == "SHELF-SEAL"
    assert main(["--home", str(home), "--json", "shelf", "slot", "--name", "ipfs"]) == 1
    slot = json.loads(capsys.readouterr().out)
    assert slot["code"] == "SHELF-SLOT-IPFS"
    assert main(["--home", str(home), "--json", "shelf", "sync", "--no-probe", "--zenodo-doi", "10.5281/zenodo.XXXX"]) == 1
    bad = json.loads(capsys.readouterr().out)
    assert bad["code"] == "SHELF-DOI-REFUSED"
    assert main(["--home", str(home), "--json", "shelf", "sync", "--no-probe", "--zenodo-doi", "10.5281/zenodo.123456"]) == 1
    dead = json.loads(capsys.readouterr().out)
    assert dead["code"] == "SHELF-DOI-REFUSED"
    usb = home / "usb-shelf"
    assert main(["--home", str(home), "shelf", "usb", "--dest", str(usb)]) == 0
    capsys.readouterr()
    assert main(["--home", str(home), "--json", "shelf", "attest", "--src", str(usb)]) == 0
    attested = json.loads(capsys.readouterr().out)
    assert attested["ok"] is True
    assert attested["code"] == "SHELF-OPERATOR-ATTEST"
    assert attested["usb_tip_pack_live"] is True
    assert attested["tip_ref"]["lockset_tip"] == "c831429befc221bd41caeb0a6d1c5361602db5684abab7af6d39714084b6b245"


def test_cli_bare_welcome(tmp_path: Path, capsys) -> None:
    home = tmp_path / "fresh"
    assert main(["--home", str(home)]) == 0
    out = capsys.readouterr().out
    assert "AzielTether" in out
    assert "No items yet." in out
    assert "azieltether ui" in out
    assert "arguments are required" not in out
    assert not home.exists()


def test_cli_help(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Common commands" in out
    assert "Advanced commands" in out
    assert "azieltether ui" in out
    assert "--json" in out
    assert "THIS IS NOT" not in out


def test_cli_unknown_command(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["bogus"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert 'Unknown command "bogus"' in err
    assert "azieltether --help" in err
    assert "arguments are required" not in err


def test_cli_genesis_needs_note(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["genesis"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Genesis needs a note." in err
    assert 'azieltether genesis --payload "desk closed"' in err


def test_cli_home_after_command(tmp_path: Path, capsys) -> None:
    home = tmp_path / "later"
    assert main(["append", "--payload", "x", "--home", str(home)]) == 1
    out = capsys.readouterr().out
    assert "first item" in out.lower() or "genesis" in out.lower()
    assert main(["genesis", "--payload", "desk closed", "--home", str(home)]) == 0
    assert "First item written." in capsys.readouterr().out


def test_cli_human_genesis_and_json_error(tmp_path: Path, capsys) -> None:
    home = tmp_path / "home"
    assert main(["--home", str(home), "genesis", "--payload", "desk closed"]) == 0
    out = capsys.readouterr().out
    assert "First item written." in out
    assert not out.lstrip().startswith("{")

    assert main(["--home", str(home), "append", "--payload", "x"]) == 0
    human = capsys.readouterr().out
    assert "Item added." in human

    other = tmp_path / "empty"
    assert main(["--home", str(other), "--json", "append", "--payload", "x"]) == 1
    err = json.loads(capsys.readouterr().out)
    assert err["ok"] is False
    assert "genesis" in err["error"]
    assert "limitation" in err
