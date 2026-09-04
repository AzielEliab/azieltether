#!/usr/bin/env python3
"""Local pulse + dual-chain reconcile. No network required."""

from __future__ import annotations

from pathlib import Path

from azieltether.item import Item
from azieltether.protocol import pulse, reconcile
from azieltether.store import Store

OUT = Path(__file__).resolve().parent / "_out"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    st = Store(OUT / "node")
    chain = st.chain()
    if len(chain) == 0:
        chain.append("genesis desk closed", node_id=st.node_id(), created_at="2026-09-04T00:00:00Z")
    parent = st.chain()[0]
    left = Item.create(payload="offline left", prev_hash=parent.hash, node_id=st.node_id())
    right = Item.create(payload="offline right", prev_hash=parent.hash, node_id=st.node_id())
    rec = reconcile(st, incoming=[left.as_dict(), right.as_dict()], probe=False)
    print("reconcile dual_chain", rec["dual_chain"])
    pulsed = pulse(st, probe=False, harvest_siblings=False)
    print("pulse mode", pulsed["mode"], "items", pulsed["items"])
    print("prefer central. peer when down. reconcile on restore")


if __name__ == "__main__":
    main()
