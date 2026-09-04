"""JSON import / export for AzielTether. Author: Aziel Eliab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from azieltether import __version__
from azieltether.store import Store

AUTHOR = "Aziel Eliab"
PRODUCT = "AzielTether"


def import_json(path: str | Path, *, store: Store | None = None) -> dict[str, Any]:
    st = store or Store()
    pth = Path(path)
    doc = json.loads(pth.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("JSON object required")
    incoming = doc.get("items") or doc.get("chain") or doc.get("payload")
    items: list[Any] = []
    if isinstance(incoming, list):
        items = incoming
    elif isinstance(incoming, dict) and isinstance(incoming.get("items"), list):
        items = incoming["items"]
    merged = st.chain().merge(items) if items else {"added": 0, "skipped": 0, "items": len(st.chain())}
    dest = st.home / "imported-state.json"
    dest.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "imported": str(pth),
        "stored": str(dest),
        "merge": merged,
        "author": AUTHOR,
        "product": PRODUCT,
        "version": __version__,
    }


def export_json(path: str | Path, *, store: Store | None = None) -> dict[str, Any]:
    st = store or Store()
    chain = st.chain()
    doc = {
        "product": PRODUCT,
        "package": "azieltether",
        "version": __version__,
        "author": AUTHOR,
        "node": st.node_record(),
        "items": [item.as_dict() for item in chain.items],
        "tips": st.tips(),
        "state": st.state(),
    }
    Path(path).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "exported": str(path),
        "items": len(chain),
        "author": AUTHOR,
        "product": PRODUCT,
        "version": __version__,
    }
