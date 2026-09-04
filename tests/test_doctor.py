"""Doctor self-check."""

from __future__ import annotations

from azieltether.doctor import run_doctor


def test_doctor_passes(capsys) -> None:
    assert run_doctor() == 0
    out = capsys.readouterr().out
    assert "passed" in out
    assert "Aziel Eliab" not in out or "identity" in out


def test_doctor_json(capsys) -> None:
    import json

    assert run_doctor(as_json=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["author"] == "Aziel Eliab"
    assert payload["network"] is False
