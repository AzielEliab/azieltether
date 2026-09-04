"""Bundled SKILL.md text for local serve."""

from __future__ import annotations

from pathlib import Path

_FALLBACK = """# AzielTether

Central × decentral software tether by Aziel Eliab.
Prefer central. Fall back to peers. Reconcile when central returns.
Not a VPN. Live public HTTPS boards stay mesh-free.
"""


def load_skill() -> str:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "SKILL.md"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return _FALLBACK


SKILL = load_skill()
