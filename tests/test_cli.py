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


def test_cli_wires_and_survival(tmp_path: Path, capsys) -> None:
    home = tmp_path / "home"
    assert main(["--home", str(home), "genesis", "--payload", "cold"]) == 0
    capsys.readouterr()
    assert main(["--home", str(home), "wires"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["wires"]["spec"] == "SPLIT-THE-WIRES-1.0"
    assert payload["survival"]["spec"] == "COLD-COPY-SURVIVAL-1.0"
    assert payload["reheal"]["spec"] == "REHEAL-1.0"
    assert main(["--home", str(home), "reheal"]) == 0
    rh = json.loads(capsys.readouterr().out)
    assert rh["reheal"]["wait"] == "phoenix-WAIT"
    assert rh["spec"] == "REHEAL-1.0"
    assert main(["--home", str(home), "survival"]) == 0
    surv = json.loads(capsys.readouterr().out)
    assert surv["multiply"]["count"] >= 3
    assert main(["--home", str(home), "shelf"]) == 0
    shelf = json.loads(capsys.readouterr().out)
    assert shelf["shelf"]["spec"] == "COLD-SHELF-TETHER-1.0"
    assert shelf["shelf"]["person_id"] == "https://www.azieleliab.com/#aziel"
    assert main(["--home", str(home), "shelf", "seal"]) == 0
    sealed = json.loads(capsys.readouterr().out)
    assert sealed["ok"] is True
    assert sealed["code"] == "SHELF-SEAL"
    assert main(["--home", str(home), "shelf", "slot", "--name", "ipfs"]) == 1
    slot = json.loads(capsys.readouterr().out)
    assert slot["code"] == "SHELF-SLOT-IPFS"
    assert main(["--home", str(home), "shelf", "sync", "--no-probe", "--zenodo-doi", "10.5281/zenodo.XXXX"]) == 1
    bad = json.loads(capsys.readouterr().out)
    assert bad["code"] == "SHELF-DOI-REFUSED"
    assert main(["--home", str(home), "shelf", "sync", "--no-probe", "--zenodo-doi", "10.5281/zenodo.123456"]) == 1
    dead = json.loads(capsys.readouterr().out)
    assert dead["code"] == "SHELF-DOI-REFUSED"
    usb = home / "usb-shelf"
    assert main(["--home", str(home), "shelf", "usb", "--dest", str(usb)]) == 0
    capsys.readouterr()
    assert main(["--home", str(home), "shelf", "attest", "--src", str(usb)]) == 0
    attested = json.loads(capsys.readouterr().out)
    assert attested["ok"] is True
    assert attested["code"] == "SHELF-OPERATOR-ATTEST"
    assert attested["usb_tip_pack_live"] is True
    assert attested["tip_ref"]["lockset_tip"] == "c831429befc221bd41caeb0a6d1c5361602db5684abab7af6d39714084b6b245"
