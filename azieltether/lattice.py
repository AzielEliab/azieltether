"""Cross-product survival lattice. Any surviving tip can rehydrate the others."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping

from azieltether.chain import ChainError, require_hex64, verify_batch
from azieltether.constants import (
    GENESIS_PREV_HASH,
    LATTICE_PRODUCTS,
    LATTICE_SCOPE,
    PRODUCT_SLUG_RE,
    WORK_SCOPES,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_product(product: str) -> str:
    slug = str(product or "").strip().lower()
    if slug in LATTICE_PRODUCTS:
        return slug
    if re.match(PRODUCT_SLUG_RE, slug):
        return slug
    raise ChainError(f"unknown lattice product {product!r}")


def local_cross_links(store: Any) -> dict[str, str]:
    links: dict[str, str] = {}
    for scope in WORK_SCOPES:
        tip = store.tip_hash(scope)
        if tip:
            links[scope] = tip
    lattice_tip = store.tip_hash(LATTICE_SCOPE)
    if lattice_tip:
        links[LATTICE_SCOPE] = lattice_tip
    return links


def anchor_payload(
    *,
    product: str,
    tip_hash: str,
    prev_anchor: str,
    node_id: str,
    timestamp: str | None = None,
    cross_links: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    product = normalize_product(product)
    tip = require_hex64("tip_hash", tip_hash)
    prev = require_hex64("prev_anchor", prev_anchor or GENESIS_PREV_HASH)
    links = {}
    for key, value in dict(cross_links or {}).items():
        links[normalize_product(key)] = require_hex64("cross_link", value)
    links[product] = tip
    return {
        "product": product,
        "tip_hash": tip,
        "prev_anchor": prev,
        "timestamp": timestamp or utc_now(),
        "node_id": node_id,
        "cross_links": links,
        "survival": (
            "If any product software node survives, GodLock and corpus "
            "rehydrate from these anchored cross-links. Mutual: GodLock "
            "survives ⇒ corpus can survive, and vice versa."
        ),
    }


def mint_anchor(store: Any, product: str, tip_hash: str | None = None) -> dict[str, Any]:
    product = normalize_product(product)
    links = local_cross_links(store)
    tip = tip_hash or links.get(product)
    if not tip and product in WORK_SCOPES:
        tip = store.tip_hash(product)
    if not tip:
        raise ChainError(f"no local tip for {product}; mint work first or pass tip_hash")
    prev = store.tip_hash(LATTICE_SCOPE) or GENESIS_PREV_HASH
    node = store.load_node()
    payload = anchor_payload(
        product=product,
        tip_hash=tip,
        prev_anchor=prev,
        node_id=node["node_id"],
        cross_links=links,
    )
    return store.mint_batch(LATTICE_SCOPE, "anchor", payload)


def mint_survival_round(store: Any) -> list[dict[str, Any]]:
    """Post one lattice anchor per local work tip (plus azieltether if only lattice)."""
    links = local_cross_links(store)
    posted = []
    products = [p for p in WORK_SCOPES if p in links] or ["azieltether"]
    for product in products:
        tip = links.get(product)
        if product == "azieltether" and not tip:
            # Anchor the lattice to itself only when no work tips exist yet.
            continue
        posted.append(mint_anchor(store, product, tip_hash=tip or links.get(product)))
    return posted


def verify_lattice(anchors: list[Mapping[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    expected = GENESIS_PREV_HASH
    tips: dict[str, str] = {}
    for index, raw in enumerate(anchors):
        try:
            batch = verify_batch(raw, expected_prev=expected if index else None)
        except ChainError as exc:
            errors.append(str(exc))
            break
        if batch.get("scope") != LATTICE_SCOPE or batch.get("kind") != "anchor":
            errors.append("not a lattice anchor")
            break
        payload = batch.get("payload") or {}
        try:
            require_hex64("tip_hash", payload.get("tip_hash"))
            require_hex64("prev_anchor", payload.get("prev_anchor"))
            normalize_product(str(payload.get("product") or ""))
        except ChainError as exc:
            errors.append(str(exc))
            break
        if index and payload.get("prev_anchor") != expected:
            errors.append("prev_anchor does not follow lattice tip")
            break
        for key, value in dict(payload.get("cross_links") or {}).items():
            try:
                tips[normalize_product(key)] = require_hex64("cross_link", value)
            except ChainError as exc:
                errors.append(str(exc))
        tips[str(payload["product"])] = str(payload["tip_hash"])
        expected = batch["hash"]
    if anchors and not errors:
        tips[LATTICE_SCOPE] = str(anchors[-1]["hash"])
    return {"ok": not errors, "errors": errors, "tips": tips, "length": len(anchors)}


def rehydrate(
    anchors: list[Mapping[str, Any]],
    *,
    surviving_product: str | None = None,
    surviving_tip: str | None = None,
) -> dict[str, Any]:
    """From any surviving product tip, recover the other anchored tips."""
    verified = verify_lattice(anchors)
    if not verified["ok"]:
        return {**verified, "rehydrated": {}, "note": "lattice failed verify"}
    tips = dict(verified["tips"])
    if surviving_product:
        slug = normalize_product(surviving_product)
        if slug not in tips:
            return {
                "ok": False,
                "errors": [f"surviving product {slug} is not in the lattice"],
                "rehydrated": {},
                "tips": tips,
            }
        if surviving_tip and require_hex64("surviving_tip", surviving_tip) != tips[slug]:
            return {
                "ok": False,
                "errors": ["surviving tip does not match the anchored tip"],
                "rehydrated": {},
                "tips": tips,
            }
    rehydrated = dict(tips)
    return {
        "ok": True,
        "errors": [],
        "tips": tips,
        "rehydrated": rehydrated,
        "godlock": tips.get("godlock"),
        "aziel-corpus": tips.get("aziel-corpus"),
        "from": surviving_product,
        "note": (
            "Mutual survival: any surviving tip bootstraps verification of the "
            "others via anchored cross-links. GodLock ↔ corpus. Any product "
            "node (FoldLock, AZ-CLCE, TemporalLock, StaticClock, MirageGrid, "
            "AZOS, …) can rehydrate GodLock and corpus."
        ),
    }
