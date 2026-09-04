"""Public identity is Aziel Eliab only."""

from __future__ import annotations

from pathlib import Path

from azieltether import __author__


ROOT = Path(__file__).resolve().parents[1]


def test_package_author() -> None:
    assert __author__ == "Aziel Eliab"


def test_readme_author_only() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Aziel Eliab" in text
    assert "Horton" not in text
    assert "Altman" not in text
    assert "GodLock.AZ" not in text
