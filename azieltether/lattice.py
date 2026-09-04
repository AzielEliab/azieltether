"""Hash lattice tips for survival across product surfaces.

Tips are receipts, not truth claims. They do not mesh godlock.uk.
Public HTTPS boards stay mesh-free. A tip is a last-known hash a
downloaded node can carry to GodLock, Aziel Digital Library, or a
product Worker.

Author: Aziel Eliab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from azieltether.canon import GENESIS_PREV_HASH, digest_mapping
from azieltether.chain import Chain
from azieltether.item import ENGINE_VERSION, utc_now

SURFACES = (
    "worker",
    "godlock",
    "corpus",
    "az-clce",
    "temporallock",
    "staticclock",
    "peer",
)

SURFACE_URLS = {
    "worker": "https://azieltether-download-tracker.vibelock.workers.dev",
    "godlock": "https://godlock.uk",
    "corpus": "https://www.azielcorpuslibrary.net",
    "az-clce": "https://azclce-download-tracker.vibelock.workers.dev",
    "temporallock": "https://temporallock-download-tracker.vibelock.workers.dev",
    "staticclock": "https://staticclock-download-tracker.vibelock.workers.dev",
    "peer": "local-peer",
}

HONEST_TIP = (
    "Lattice tip only. Not a mesh on godlock.uk. Public boards stay "
    "mesh-free. Receipts, not truth claims."
)


@dataclass(frozen=True)
class LatticeTip:
    surface: str
    product: str
    tip_hash: str
    prev_hash: str
    node_id: str
    created_at: str
    hash: str
    url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "engine_version": ENGINE_VERSION,
            "hash": self.hash,
            "kind": "tip",
            "node_id": self.node_id,
            "prev_hash": self.prev_hash,
            "product": self.product,
            "surface": self.surface,
            "tip_hash": self.tip_hash,
            "url": self.url,
            "note": HONEST_TIP,
        }


def mint_tip(
    *,
    surface: str,
    tip_hash: str,
    node_id: str,
    prev_hash: str | None = None,
    created_at: str | None = None,
) -> LatticeTip:
    if surface not in SURFACES:
        raise ValueError(f"surface must be one of {SURFACES}")
    ts = created_at or utc_now()
    body = {
        "created_at": ts,
        "engine_version": ENGINE_VERSION,
        "kind": "tip",
        "node_id": node_id,
        "prev_hash": prev_hash or GENESIS_PREV_HASH,
        "product": "azieltether",
        "surface": surface,
        "tip_hash": tip_hash,
        "url": SURFACE_URLS.get(surface, ""),
        "note": HONEST_TIP,
    }
    digest = digest_mapping(body)
    return LatticeTip(
        surface=surface,
        product="azieltether",
        tip_hash=tip_hash,
        prev_hash=str(body["prev_hash"]),
        node_id=node_id,
        created_at=ts,
        hash=digest,
        url=str(body["url"]),
    )


def tip_from_chain(chain: Chain, *, surface: str, node_id: str) -> LatticeTip:
    tips = chain.tip_hashes()
    tip_hash = tips[0] if tips else chain.last_hash()
    prev = chain[-1].prev_hash if len(chain) else GENESIS_PREV_HASH
    return mint_tip(surface=surface, tip_hash=tip_hash, node_id=node_id, prev_hash=prev)


def bind_surfaces(chain: Chain, *, node_id: str) -> dict[str, Any]:
    """Mint a tip for each survival surface from the current DAG heads."""
    surfaces: dict[str, Any] = {}
    heads = chain.tip_hashes() or [chain.last_hash()]
    for surface in SURFACES:
        tip = mint_tip(
            surface=surface,
            tip_hash=heads[0],
            node_id=node_id,
            prev_hash=chain.last_hash() if len(chain) else GENESIS_PREV_HASH,
        )
        surfaces[surface] = tip.as_dict()
    return {
        "product": "azieltether",
        "author": "Aziel Eliab",
        "version": ENGINE_VERSION,
        "heads": heads,
        "surfaces": surfaces,
        "note": HONEST_TIP,
        "mesh_on_public_boards": False,
    }


def verify_tip(raw: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(raw)
    posted = str(data.get("hash") or "")
    recomputed = digest_mapping(data)
    return {
        "ok": bool(posted) and posted == recomputed,
        "hash": recomputed,
        "posted_hash": posted or None,
        "surface": data.get("surface"),
        "tip_hash": data.get("tip_hash"),
        "note": HONEST_TIP,
        "author": "Aziel Eliab",
    }
