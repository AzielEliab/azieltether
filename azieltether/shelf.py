"""COLD-SHELF-TETHER — offline/peer cold-shelf so tip/receipts survive yank.

Prefer the Worker when it is up (probe + ingest-as-receipt). When the
Worker is dead, serve the last local cold-shelf. On restore, reconcile
by hash. Never rewrite history. Never lie to survive.

The Worker is zero-retention. Durable tip/receipts live on the local
shelf and on operator-configured non-Cloudflare URLs (Codeberg raw,
archive.org, GitFlic, local path, USB). Zenodo is IP-banned — do not
invent a DOI. Sister work is aziel-corpus COLD-MULTI-SHELF-1.0 — cite
the same lockset tip hashes. Do not fork Person @id
https://www.azieleliab.com/#aziel.

MOCK/SLOT (not live): multi-homed DNS, invented IPFS CIDs, auto-publish
to those hosts, anycast, AZ Generator, Zenodo DOI, Plane B until
hash-verify on alternate shelves. Each has a refuse code.

Laws: CROSS-NETWORK-SURVIVAL-1.0, NO-LIE-NO-REWRITE-1.0,
COLD-MULTI-SHELF-1.0, ingest-as-receipt, RE-EXPAND-FROM-ARCHIVE,
REHEAL, NO-FAN. Lamb Lens: Service→Clarity→Peace.

Author: Aziel Eliab only.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse

from azieltether.canon import canonical_json, require_hex64
from azieltether.errors import AppendOnlyError
from azieltether.item import utc_now
from azieltether.survival import item_digest_ok
from azieltether.wires import cite_ok, hash_holds

SHELF_SPEC = "COLD-SHELF-TETHER-1.0"
SISTER_SPEC = "COLD-MULTI-SHELF-1.0"
CROSS_NETWORK_SPEC = "CROSS-NETWORK-SURVIVAL-1.0"
NO_LIE_SPEC = "NO-LIE-NO-REWRITE-1.0"
CNS_OPERATOR_ATTEST = "CNS-OPERATOR-ATTEST"
SHELF_AUTHOR = "Aziel Eliab"
PERSON_ID = "https://www.azieleliab.com/#aziel"
PRODUCT = "azieltether"
SHELF_URLS_ENV = "AZIELTETHER_SHELF_URLS"
ZENODO_DOI_ENV = "AZIELTETHER_ZENODO_DOI"
ZENODO_URL_ENV = "AZIELTETHER_ZENODO_URL"
PLANE_B_URL_ENV = "AZIELTETHER_PLANE_B_URL"
LAMB_LENS = "Service→Clarity→Peace"

# Operator 2026-09-14 tip-pack cite. Do not invent a DOI.
OPERATOR_DATE = "2026-09-14"
OPERATOR_LOCKSET_TIP = "c831429befc221bd41caeb0a6d1c5361602db5684abab7af6d39714084b6b245"
OPERATOR_PACK_SHA256 = "b549362c0736ddb54ddc488812327c464e0da1167281f92fd1a4263eedf5df37"
PLANE_B_HOSTS = ("codeberg.org", "archive.org", "gitflic.ru")

# Operator planes. A is the same Cloudflare tunnel — it does not survive a CF yank.
PLANE_A = "A"
PLANE_B = "B"
PLANE_C = "C"
PLANE_A_HUBS = (
    "https://azieltether-download-tracker.vibelock.workers.dev",
    "https://azclce-download-tracker.vibelock.workers.dev",
    "https://temporallock-download-tracker.vibelock.workers.dev",
    "https://staticclock-download-tracker.vibelock.workers.dev",
)
PLANE_A_TUNNEL = "vibelock.workers.dev"
PLANE_A_SURVIVES_CF_YANK = False
REWRITE_KEYS = frozenset(
    {
        "rewrite_key",
        "rewrite",
        "replace_hash",
        "historian_key",
        "lie_key",
        "survive_key",
    }
)

# Honest inventory. Do not claim a SLOT is live.
REAL = (
    "worker_probe",
    "ingest_as_receipt",
    "local_seal",
    "serve_last_local_when_down",
    "hash_reconcile_on_restore",
    "manifest_sha256_verify",
    "fetch_local_path",
    "fetch_https_raw",
    "usb_airgap_export_import",
    "refuse_rewrite_key",
    "refuse_lie_to_survive",
    "refuse_hash_mismatch",
    "re_expand_from_archive",
    "no_fan_unverified",
    "plane_a_probe",
    "plane_c_usb_local",
    "plane_b_alt_shelf_hash_verify",
    "plane_c_operator_attest",
)

SLOTS = {
    "multihome_dns": "SHELF-SLOT-MULTIHOME-DNS",
    "ipfs": "SHELF-SLOT-IPFS",
    "auto_publish": "SHELF-SLOT-AUTO-PUBLISH",
    "anycast": "SHELF-SLOT-ANYCAST",
    "az_generator": "SHELF-SLOT-AZ-GENERATOR",
    "zenodo_doi": "SHELF-SLOT-ZENODO-DOI",
    "alt_shelf": "SHELF-SLOT-ALT-SHELF",
    "forge_publish": "SHELF-SLOT-FORGE-PUBLISH",
}

LAWS = (
    CROSS_NETWORK_SPEC,
    NO_LIE_SPEC,
    "COLD-COPY-SURVIVAL-1.0",
    "REHEAL-1.0",
    "SPLIT-THE-WIRES-1.0",
    "ingest-as-receipt",
    "RE-EXPAND-FROM-ARCHIVE",
    "NO-FAN",
    SISTER_SPEC,
)

LAW = (
    "COLD-SHELF TETHER. Prefer Worker when up: probe + ingest-as-receipt, "
    "then seal tip+receipts locally. When Worker is dead, serve the last "
    "local cold-shelf. On restore, reconcile by hash — never rewrite. "
    "Fetch/verify a SHA-256 manifest from operator URLs (Codeberg raw, "
    "archive.org, GitFlic, local path). Hash mismatch refuses. No rewrite "
    "key. No lie-to-survive. Multi-homed DNS, IPFS CIDs, auto-publish, "
    "anycast, and AZ Generator are MOCK/SLOT. Operator planes: A = four "
    "CF hubs on the same tunnel (does not survive a CF yank); B = "
    "independent shelves (Codeberg / archive.org / GitFlic) SLOT until "
    "hash-verify — Zenodo is IP-banned, do not invent a DOI; C = USB/"
    "local cold copy. USB tip-pack goes LIVE only after sha256sum -c "
    "plus operator attest (CNS-OPERATOR-ATTEST until then). Worker-up "
    "pulls A; Worker-down serves last C; restore reconciles by hash — "
    "never rewrite. Sister: aziel-corpus COLD-MULTI-SHELF-1.0 — cite "
    "the same lockset tip hashes. Lamb Lens: Service→Clarity→Peace. "
    "Person @id https://www.azieleliab.com/#aziel. Author: Aziel Eliab only."
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_digest(doc: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical manifest excluding its own sha256 field."""
    body = {k: v for k, v in dict(doc).items() if k != "sha256"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def _refuse(code: str, note: str, **extra: Any) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "ok": False,
        "code": code,
        "note": note,
        "spec": SHELF_SPEC,
        "author": SHELF_AUTHOR,
        "person_id": PERSON_ID,
        "applied": False,
    }
    rec.update(extra)
    return rec


def refuse_slot(name: str) -> dict[str, Any]:
    """Anything not implemented is MOCK/SLOT with a refuse code."""
    key = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "dns": "multihome_dns",
        "multi_homed_dns": "multihome_dns",
        "multi-homed-dns": "multihome_dns",
        "ipfs_cid": "ipfs",
        "cid": "ipfs",
        "publish": "auto_publish",
        "gitlab_publish": "auto_publish",
        "codeberg_publish": "auto_publish",
        "zenodo_publish": "auto_publish",
        "azgenerator": "az_generator",
        "az_gen": "az_generator",
        "zenodo": "zenodo_doi",
        "doi": "zenodo_doi",
        "plane_b": "alt_shelf",
        "alt": "alt_shelf",
        "alternate": "alt_shelf",
        "gitflic": "alt_shelf",
        "archive": "alt_shelf",
        "archive_org": "alt_shelf",
        "forge": "forge_publish",
        "gitlab": "forge_publish",
        "codeberg": "forge_publish",
    }
    slot = aliases.get(key, key)
    if slot not in SLOTS:
        return _refuse(
            "SHELF-SLOT-UNKNOWN",
            "Unknown slot. Live work is local seal / HTTPS fetch+verify / USB.",
            slot=slot,
            mock=True,
        )
    notes = {
        "multihome_dns": "Live multi-homed DNS is not implemented. Do not claim it.",
        "ipfs": "IPFS CIDs are not implemented. Do not invent a CID.",
        "auto_publish": "Auto-publish to Codeberg/archive.org/GitFlic is not implemented. Operator copies files.",
        "anycast": "Anycast / geo-DNS is not implemented.",
        "az_generator": "AZ Generator is MirageGrid-only. AzielTether refuses the call.",
        "zenodo_doi": "Zenodo is IP-banned. Do not invent a DOI. Plane B uses Codeberg / archive.org / GitFlic after hash-verify.",
        "alt_shelf": "Plane B is SLOT until SHA-256 verify on Codeberg, archive.org, or GitFlic. Not Zenodo.",
        "forge_publish": "Auto-publish to a non-GitHub forge is SLOT. Operator copies files (Plane C USB or raw URL).",
    }
    return _refuse(SLOTS[slot], notes[slot], slot=slot, mock=True, live=False)


def refuse_rewrite_key(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """NO-LIE / NO-REWRITE: there is no rewrite key. History is append-only."""
    data = dict(payload or {})
    hit = [k for k in REWRITE_KEYS if data.get(k) not in (None, False, "", 0)]
    if hit:
        return _refuse(
            "SHELF-REWRITE-REFUSED",
            "No rewrite key. Tip/receipts are hash-absolute. Corrections are new items.",
            keys=hit,
            law=NO_LIE_SPEC,
        )
    return {
        "ok": True,
        "code": "SHELF-NO-REWRITE",
        "rewrite_key": False,
        "author": SHELF_AUTHOR,
        "law": NO_LIE_SPEC,
    }


def refuse_lie_to_survive(
    *,
    worker_up_claimed: bool | None = None,
    worker_actually_up: bool | None = None,
    invented_tips: Sequence[str] | None = None,
    known_hashes: Sequence[str] | None = None,
    claim_ipfs_live: bool = False,
    claim_multihome_dns: bool = False,
    claim_rewrite_to_survive: bool = False,
    claim_worker_holds_chain: bool = False,
    claim_zenodo_live: bool = False,
    claim_usb_live: bool = False,
) -> dict[str, Any]:
    """CROSS-NETWORK-SURVIVAL + NO-LIE: never lie, even to survive a yank."""
    if claim_rewrite_to_survive:
        return _refuse(
            "SHELF-LIE-REFUSED",
            "No rewrite-to-survive. Yank does not authorize a historian.",
            law=NO_LIE_SPEC,
        )
    if worker_up_claimed is True and worker_actually_up is False:
        return _refuse(
            "SHELF-LIE-REFUSED",
            "Cannot claim Worker is up when the probe failed. Serve last local instead.",
            law=NO_LIE_SPEC,
        )
    if claim_worker_holds_chain:
        return _refuse(
            "SHELF-LIE-REFUSED",
            "Hosted Worker is zero-retention. It does not hold the chain.",
            law=NO_LIE_SPEC,
        )
    if claim_ipfs_live:
        rec = refuse_slot("ipfs")
        rec["code"] = "SHELF-LIE-REFUSED"
        rec["note"] = "Cannot claim a live IPFS CID. That slot is MOCK."
        rec["slot_code"] = SLOTS["ipfs"]
        return rec
    if claim_multihome_dns:
        rec = refuse_slot("multihome_dns")
        rec["code"] = "SHELF-LIE-REFUSED"
        rec["note"] = "Cannot claim live multi-homed DNS. That slot is MOCK."
        rec["slot_code"] = SLOTS["multihome_dns"]
        return rec
    if claim_zenodo_live:
        return _refuse(
            "SHELF-DOI-REFUSED",
            "Cannot claim Zenodo LIVE. Zenodo is IP-banned. Do not invent a DOI.",
            law=NO_LIE_SPEC,
            zenodo_dead=True,
        )
    if claim_usb_live:
        return refuse_operator_attest(attested=False, sha256sum_ok=False)
    known = {str(h).lower() for h in (known_hashes or []) if h}
    invented = [str(t) for t in (invented_tips or []) if t and str(t).lower() not in known]
    if invented:
        return _refuse(
            "SHELF-LIE-REFUSED",
            "Cannot invent a tip hash that is not in the verified set.",
            invented=invented,
            law=NO_LIE_SPEC,
        )
    return {
        "ok": True,
        "code": "SHELF-HONEST",
        "author": SHELF_AUTHOR,
        "law": NO_LIE_SPEC,
        "cross_network": CROSS_NETWORK_SPEC,
    }


def refuse_fan(body: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """NO-FAN: unverified shelf bodies are not pushed to a crowd."""
    data = dict(body or {})
    fan = data.get("fan") or data.get("fanout") or data.get("broadcast_body")
    items = data.get("items") or data.get("payload")
    if fan or (data.get("push") and items):
        return _refuse(
            "SHELF-NO-FAN",
            "NO-FAN. Receiver pulls a verified shelf. Do not fan unverified bodies.",
            law="NO-FAN",
        )
    return {"ok": True, "code": "SHELF-NO-FAN-OK", "fan": False, "author": SHELF_AUTHOR}


def doi_is_live(doi: str | None) -> bool:
    """Zenodo is IP-banned. A DOI is never LIVE. Do not invent one."""
    return False


def doi_looks_invented(doi: str | None) -> bool:
    """Any DOI string is treated as invented or dead — never accept."""
    return bool(str(doi or "").strip())


def operator_tip_ref() -> dict[str, str]:
    return {
        "date": OPERATOR_DATE,
        "lockset_tip": OPERATOR_LOCKSET_TIP,
        "pack_sha256": OPERATOR_PACK_SHA256,
        "note": "Operator 2026-09-14 cite. Do not invent a DOI.",
    }


def plane_b_host(url: str | None) -> str | None:
    """Return the independent shelf host, or None. Zenodo is never a host."""
    text = str(url or "").strip()
    if not text:
        return None
    host = (urlparse(text).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host or "zenodo" in host:
        return None
    for allowed in PLANE_B_HOSTS:
        if host == allowed or host.endswith("." + allowed):
            return allowed
    return None


def plane_a_card() -> dict[str, Any]:
    return {
        "plane": PLANE_A,
        "name": "cf-hubs",
        "hubs": list(PLANE_A_HUBS),
        "count": len(PLANE_A_HUBS),
        "tunnel": PLANE_A_TUNNEL,
        "same_tunnel": True,
        "survives_cf_yank": PLANE_A_SURVIVES_CF_YANK,
        "live": True,
        "note": "Four product Workers on the same Cloudflare tunnel. Worker-up pulls this plane. A CF yank takes all four — that is why Plane C exists.",
        "author": SHELF_AUTHOR,
    }


def plane_b_status(
    *,
    doi: str | None = None,
    url: str | None = None,
    sha256: str | None = None,
    verified: bool | None = None,
) -> dict[str, Any]:
    """Independent shelves. SLOT until hash-verify. Zenodo dead — no invented DOI."""
    raw_doi = (doi if doi is not None else os.environ.get(ZENODO_DOI_ENV, "")).strip()
    raw_url = (
        url
        if url is not None
        else (os.environ.get(PLANE_B_URL_ENV, "") or os.environ.get(ZENODO_URL_ENV, ""))
    ).strip()
    if raw_doi:
        return _refuse(
            "SHELF-DOI-REFUSED",
            "Zenodo is IP-banned. Do not invent a DOI. Plane B is SLOT until hash-verify on Codeberg, archive.org, or GitFlic.",
            plane=PLANE_B,
            doi=raw_doi,
            doi_live=False,
            zenodo_dead=True,
            shelves=list(PLANE_B_HOSTS),
            law=CROSS_NETWORK_SPEC,
        )
    if raw_url and ("zenodo" in raw_url.lower() or urlparse(raw_url).hostname and "zenodo" in (urlparse(raw_url).hostname or "").lower()):
        rec = refuse_slot("zenodo_doi")
        rec["plane"] = PLANE_B
        rec["name"] = "alt-independent-shelves"
        rec["survives_cf_yank"] = True
        rec["doi_live"] = False
        rec["zenodo_dead"] = True
        rec["url"] = raw_url
        rec["shelves"] = list(PLANE_B_HOSTS)
        rec["note"] = "Zenodo is IP-banned. Do not invent a DOI. Plane B stays SLOT until hash-verify on Codeberg / archive.org / GitFlic."
        return rec
    host = plane_b_host(raw_url)
    hash_ok = bool(verified) and bool(sha256) and bool(host)
    if hash_ok:
        return {
            "ok": True,
            "code": "SHELF-PLANE-B-LIVE",
            "plane": PLANE_B,
            "name": "alt-independent-shelves",
            "url": raw_url,
            "host": host,
            "sha256": sha256,
            "doi_live": False,
            "zenodo_dead": True,
            "live": True,
            "pull": True,
            "verified": True,
            "survives_cf_yank": True,
            "shelves": list(PLANE_B_HOSTS),
            "tip_ref": operator_tip_ref(),
            "author": SHELF_AUTHOR,
            "laws": list(LAWS),
            "lamb_lens": LAMB_LENS,
            "note": "Plane B LIVE after SHA-256 verify on an independent shelf. Auto-publish remains SLOT.",
        }
    rec = refuse_slot("alt_shelf")
    rec["plane"] = PLANE_B
    rec["name"] = "alt-independent-shelves"
    rec["survives_cf_yank"] = True
    rec["doi_live"] = False
    rec["zenodo_dead"] = True
    rec["live"] = False
    rec["url"] = raw_url or None
    rec["host"] = host
    rec["sha256"] = sha256 or None
    rec["verified"] = False
    rec["shelves"] = list(PLANE_B_HOSTS)
    rec["tip_ref"] = operator_tip_ref()
    rec["note"] = (
        "Plane B is SLOT until hash-verify on Codeberg, archive.org, or GitFlic. "
        "Zenodo is IP-banned. Do not invent a DOI. A URL alone is not LIVE."
    )
    return rec


def refuse_operator_attest(
    *,
    attested: bool = False,
    sha256sum_ok: bool = False,
) -> dict[str, Any]:
    """CROSS-NETWORK-SURVIVAL: USB tip-pack is not LIVE until operator attest."""
    if attested and sha256sum_ok:
        return {
            "ok": True,
            "code": "SHELF-OPERATOR-ATTEST",
            "plane": PLANE_C,
            "usb_tip_pack_live": True,
            "sha256sum_c": True,
            "operator_attest": True,
            "author": SHELF_AUTHOR,
            "law": CROSS_NETWORK_SPEC,
        }
    return _refuse(
        CNS_OPERATOR_ATTEST,
        "USB tip-pack is not LIVE until the operator attests after sha256sum -c.",
        plane=PLANE_C,
        usb_tip_pack_live=False,
        attested=attested,
        sha256sum_c=sha256sum_ok,
        tip_ref=operator_tip_ref(),
        law=CROSS_NETWORK_SPEC,
        no_lie=NO_LIE_SPEC,
        sister_spec=SISTER_SPEC,
        lamb_lens=LAMB_LENS,
    )


def plane_c_card(store: Any = None) -> dict[str, Any]:
    attest = {}
    if store is not None:
        attest = store.plane_c_attest()
    usb_live = bool(attest.get("ok") and attest.get("usb_tip_pack_live"))
    rec: dict[str, Any] = {
        "ok": True,
        "plane": PLANE_C,
        "name": "usb-local-cold-copy",
        "live": True,
        "local_last_seal": True,
        "usb_tip_pack_live": usb_live,
        "survives_cf_yank": True,
        "forge_publish": False,
        "forge_publish_slot": SLOTS["forge_publish"],
        "tip_ref": operator_tip_ref(),
        "lamb_lens": LAMB_LENS,
        "note": (
            "Last local cold-shelf + USB airgap. Worker-down serves last local seal. "
            "USB tip-pack goes LIVE only after sha256sum -c plus operator attest."
        ),
        "author": SHELF_AUTHOR,
    }
    if usb_live:
        rec["attest"] = {
            "ok": True,
            "code": "SHELF-OPERATOR-ATTEST",
            "sha256": attest.get("sha256"),
            "lockset_tip": attest.get("lockset_tip"),
            "pack_sha256": attest.get("pack_sha256"),
        }
    else:
        rec["attest"] = refuse_operator_attest(attested=False, sha256sum_ok=False)
    return rec


def pull_plane_a(*, host: str | None = None, timeout: float | None = None) -> dict[str, Any]:
    """Worker-up: probe the four same-tunnel CF hubs. Ingest stays on this product."""
    from azieltether.client import probe_health

    hubs = list(PLANE_A_HUBS)
    if host:
        extra = host.rstrip("/")
        if extra not in hubs:
            hubs = [extra, *hubs]
    results: list[dict[str, Any]] = []
    up = 0
    for hub in hubs:
        rec = probe_health(hub, timeout=timeout)
        ok = bool(rec.get("prefer_central"))
        up += int(ok)
        results.append({"hub": hub, "ok": ok, "prefer_central": ok})
    primary = (host or PLANE_A_HUBS[0]).rstrip("/")
    primary_up = any(r["ok"] and r["hub"].rstrip("/") == primary for r in results) or (
        any(r["ok"] for r in results[:1])
    )
    if host:
        primary_up = bool(next((r["ok"] for r in results if r["hub"].rstrip("/") == host.rstrip("/")), False))
    return {
        "ok": True,
        "code": "SHELF-PLANE-A",
        "plane": PLANE_A,
        "hubs": results,
        "up": up,
        "primary": primary,
        "primary_up": primary_up,
        "same_tunnel": True,
        "survives_cf_yank": False,
        "author": SHELF_AUTHOR,
        "note": "Same Cloudflare tunnel. Counts are probes, not a durable store.",
    }


def classify_url(url: str) -> str:
    text = str(url or "").strip()
    if not text:
        return "empty"
    lower = text.lower()
    if lower.startswith("ipfs://") or "/ipfs/" in lower or lower.startswith("cid:"):
        return "ipfs"
    parsed = urlparse(text)
    scheme = (parsed.scheme or "").lower()
    if scheme in {"ipfs", "ipns"}:
        return "ipfs"
    if scheme in {"dns", "anycast"}:
        return "multihome_dns"
    if "multi-home" in lower or "multihome" in lower or "anycast" in lower:
        return "multihome_dns"
    if scheme in {"", "file"}:
        return "local"
    if scheme in {"http", "https"}:
        return "https"
    return "unknown"


def as_local_path(url: str) -> Path | None:
    text = str(url or "").strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme in {"", "file"}:
        if parsed.scheme == "file":
            return Path(parsed.path)
        return Path(text)
    return None


def fetch_bytes(url: str, *, timeout: float | None = None) -> dict[str, Any]:
    """Read bytes from a local path or raw HTTPS URL. Slots refuse."""
    kind = classify_url(url)
    if kind == "ipfs":
        return refuse_slot("ipfs")
    if kind == "multihome_dns":
        return refuse_slot("multihome_dns")
    if kind == "empty":
        return _refuse("SHELF-URL-REQUIRED", "A shelf URL or local path is required.")
    if kind == "unknown":
        return _refuse("SHELF-URL-REFUSED", "Only file/local path or http(s) raw URLs are live.")
    if kind == "local":
        path = as_local_path(url)
        if path is None or not path.is_file():
            return _refuse("SHELF-LOCAL-MISSING", "Local shelf path is not a file.", url=url)
        data = path.read_bytes()
        return {
            "ok": True,
            "code": "SHELF-FETCH-LOCAL",
            "url": str(path),
            "kind": "local",
            "bytes": data,
            "sha256": sha256_bytes(data),
            "author": SHELF_AUTHOR,
        }
    from azieltether.client import http_bytes

    rec = http_bytes(url, timeout=timeout)
    if not rec.get("ok"):
        return _refuse(
            "SHELF-FETCH-FAILED",
            str(rec.get("error") or "HTTPS fetch failed"),
            url=url,
            kind="https",
            http_status=rec.get("http_status"),
        )
    data = rec["bytes"]
    return {
        "ok": True,
        "code": "SHELF-FETCH-HTTPS",
        "url": url,
        "kind": "https",
        "bytes": data,
        "sha256": sha256_bytes(data),
        "author": SHELF_AUTHOR,
        "note": "Raw HTTPS GET + SHA-256 verify. Auto-publish remains a SLOT.",
    }


def verify_sha256(data: bytes, expected: str | None) -> dict[str, Any]:
    digest = sha256_bytes(data)
    if not expected:
        return {
            "ok": True,
            "code": "SHELF-SHA256",
            "sha256": digest,
            "expected": None,
            "checked": False,
            "author": SHELF_AUTHOR,
        }
    want = str(expected).strip().lower()
    if len(want.split()) > 1:
        want = want.split()[0]
    try:
        want = require_hex64("sha256", want)
    except ValueError as exc:
        return _refuse("SHELF-SHA256-BAD", str(exc), sha256=digest)
    if digest != want:
        return _refuse(
            "SHELF-HASH-MISMATCH",
            "Manifest/file SHA-256 does not match the expected digest. Refuse.",
            sha256=digest,
            expected=want,
            law=NO_LIE_SPEC,
        )
    return {
        "ok": True,
        "code": "SHELF-SHA256-OK",
        "sha256": digest,
        "expected": want,
        "checked": True,
        "author": SHELF_AUTHOR,
    }


def parse_manifest(data: bytes) -> dict[str, Any]:
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _refuse("SHELF-MANIFEST-INVALID", f"JSON required: {exc}")
    if not isinstance(raw, dict):
        return _refuse("SHELF-MANIFEST-INVALID", "Manifest must be a JSON object.")
    posted = raw.get("sha256")
    digest = manifest_digest(raw)
    if posted:
        try:
            posted_hex = require_hex64("sha256", posted)
        except ValueError as exc:
            return _refuse("SHELF-MANIFEST-INVALID", str(exc))
        if posted_hex != digest:
            return _refuse(
                "SHELF-HASH-MISMATCH",
                "Embedded manifest sha256 does not match canonical body.",
                sha256=digest,
                expected=posted_hex,
            )
    if raw.get("person_id") and str(raw["person_id"]) != PERSON_ID:
        return _refuse(
            "SHELF-PERSON-REFUSED",
            "Do not fork Person @id https://www.azieleliab.com/#aziel.",
            person_id=raw.get("person_id"),
        )
    rewrite = refuse_rewrite_key(raw)
    if not rewrite.get("ok"):
        return rewrite
    return {
        "ok": True,
        "code": "SHELF-MANIFEST-OK",
        "manifest": raw,
        "sha256": digest,
        "author": SHELF_AUTHOR,
        "person_id": PERSON_ID,
    }


def fetch_manifest(
    url: str,
    *,
    expected_sha256: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Fetch a cold-shelf manifest and refuse on SHA-256 mismatch."""
    pulled = fetch_bytes(url, timeout=timeout)
    if not pulled.get("ok"):
        return pulled
    data: bytes = pulled["bytes"]
    check = verify_sha256(data, expected_sha256)
    if not check.get("ok"):
        return check
    parsed = parse_manifest(data)
    if not parsed.get("ok"):
        return parsed
    rec = {
        "ok": True,
        "code": "SHELF-PULL-OK",
        "url": pulled.get("url") or url,
        "kind": pulled.get("kind"),
        "bytes_sha256": pulled["sha256"],
        "manifest_sha256": parsed["sha256"],
        "manifest": parsed["manifest"],
        "author": SHELF_AUTHOR,
        "person_id": PERSON_ID,
        "spec": SHELF_SPEC,
        "sister_spec": SISTER_SPEC,
    }
    if expected_sha256:
        rec["expected"] = check.get("expected")
        rec["checked"] = True
    return rec


def _receipts_from_items(items: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in items:
        digest = str(raw.get("hash") or "")
        if not digest or digest in seen:
            continue
        if not item_digest_ok(raw):
            continue
        seen.add(digest)
        kind = str(raw.get("kind") or "item")
        out.append({"hash": digest, "kind": kind})
    return out


def build_shelf_document(
    *,
    items: Sequence[Mapping[str, Any]],
    tip_hashes: Sequence[str],
    lockset_hash: str | None,
    node_id: str,
    tips: Mapping[str, Any] | None = None,
    ingest_acks: Sequence[str] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    sealed_items = [dict(i) for i in items if isinstance(i, Mapping) and item_digest_ok(i)]
    receipts = _receipts_from_items(sealed_items)
    for ack in ingest_acks or []:
        try:
            digest = require_hex64("receipt", ack)
        except ValueError:
            continue
        if digest not in {r["hash"] for r in receipts}:
            receipts.append({"hash": digest, "kind": "ingest-ack"})
    heads = [require_hex64("tip", h) for h in tip_hashes if h]
    lock = ""
    if lockset_hash:
        lock = require_hex64("lockset", lockset_hash)
    body: dict[str, Any] = {
        "author": SHELF_AUTHOR,
        "created_at": created_at or utc_now(),
        "items": sealed_items,
        "laws": list(LAWS),
        "lockset_hash": lock,
        "mock": sorted(SLOTS.keys()),
        "node_id": node_id,
        "person_id": PERSON_ID,
        "product": PRODUCT,
        "real": list(REAL),
        "receipts": receipts,
        "sister_spec": SISTER_SPEC,
        "spec": SHELF_SPEC,
        "tip_hashes": heads,
        "tips": dict(tips or {}),
        "worker_durable_store": False,
        "zero_retention_worker": True,
    }
    body["sha256"] = manifest_digest(body)
    return body


def _item_hashes(items: Sequence[Mapping[str, Any]] | None) -> list[str]:
    out: list[str] = []
    for raw in items or []:
        digest = str(raw.get("hash") or "")
        if digest:
            out.append(digest)
    return out


def seal_shelf(store: Any, *, ingest_acks: Sequence[str] | None = None) -> dict[str, Any]:
    """Write the current DAG + tips + lockset into the local cold-shelf."""
    from azieltether.store import Store

    st: Store = store
    chain = st.chain()
    verified = chain.verify()
    if not verified.ok:
        return _refuse(
            "SHELF-POISON-REFUSED",
            "Refuse to seal a broken DAG. Hash-absolute, fail-closed.",
            errors=list(verified.errors),
        )
    lock = st.lockset() or st.seal_lockset()
    tips = st.tips() or {}
    if not tips.get("surfaces"):
        from azieltether.lattice import bind_surfaces

        tips = bind_surfaces(chain, node_id=st.node_id())
        st.write_tips(tips)
    doc = build_shelf_document(
        items=[i.as_dict() for i in chain.items],
        tip_hashes=list(verified.tip_hashes),
        lockset_hash=str(lock.get("hash") or ""),
        node_id=st.node_id(),
        tips=tips,
        ingest_acks=ingest_acks,
    )
    existing = load_last_shelf(st)
    if existing.get("ok"):
        prev = existing["manifest"]
        same_items = _item_hashes(prev.get("items") if isinstance(prev.get("items"), list) else []) == _item_hashes(
            doc["items"]
        )
        same_tips = list(prev.get("tip_hashes") or []) == list(doc["tip_hashes"])
        if same_items and same_tips:
            dest = st.shelf_dir
            manifest_path = dest / "manifest.json"
            data = manifest_path.read_bytes() if manifest_path.is_file() else b""
            return {
                "ok": True,
                "code": "SHELF-SEAL-UNCHANGED",
                "spec": SHELF_SPEC,
                "author": SHELF_AUTHOR,
                "person_id": PERSON_ID,
                "path": str(manifest_path),
                "queue": str(dest / "queue.jsonl"),
                "sha256": prev.get("sha256") or existing.get("sha256"),
                "bytes_sha256": sha256_bytes(data) if data else st.state().get("last_shelf_bytes_sha256"),
                "tip_hashes": list(prev.get("tip_hashes") or []),
                "lockset_hash": prev.get("lockset_hash") or "",
                "receipts": len(prev.get("receipts") or []),
                "items": len(prev.get("items") or []),
                "sister_spec": SISTER_SPEC,
                "laws": list(LAWS),
                "real": list(REAL),
                "mock": sorted(SLOTS.keys()),
                "rewritten": False,
            }
    dest = st.shelf_dir
    dest.mkdir(parents=True, exist_ok=True)
    manifest_path = dest / "manifest.json"
    line_path = dest / "queue.jsonl"
    sha_path = dest / "manifest.sha256"
    raw = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    data = raw.encode("utf-8")
    manifest_path.write_text(raw, encoding="utf-8")
    sha_path.write_text(sha256_bytes(data) + "  manifest.json\n", encoding="utf-8")
    with line_path.open("w", encoding="utf-8") as handle:
        for item in doc["items"]:
            handle.write(canonical_json(item) + "\n")
    state = st.state()
    state["last_shelf_sha256"] = doc["sha256"]
    state["last_shelf_bytes_sha256"] = sha256_bytes(data)
    state["last_shelf_tips"] = list(doc["tip_hashes"])
    st.write_state(state)
    st.multiply_copies()
    return {
        "ok": True,
        "code": "SHELF-SEAL",
        "spec": SHELF_SPEC,
        "author": SHELF_AUTHOR,
        "person_id": PERSON_ID,
        "path": str(manifest_path),
        "queue": str(line_path),
        "sha256": doc["sha256"],
        "bytes_sha256": sha256_bytes(data),
        "tip_hashes": doc["tip_hashes"],
        "lockset_hash": doc["lockset_hash"],
        "receipts": len(doc["receipts"]),
        "items": len(doc["items"]),
        "sister_spec": SISTER_SPEC,
        "laws": list(LAWS),
        "real": list(REAL),
        "mock": sorted(SLOTS.keys()),
    }


def load_last_shelf(store: Any) -> dict[str, Any]:
    from azieltether.store import Store

    st: Store = store
    path = st.shelf_dir / "manifest.json"
    if not path.is_file():
        return _refuse("SHELF-NO-LOCAL", "No sealed local cold-shelf yet. Run shelf seal.")
    return parse_manifest(path.read_bytes())


def serve_last_local(store: Any) -> dict[str, Any]:
    """When Worker is dead: serve the last local cold copy. Do not invent."""
    loaded = load_last_shelf(store)
    if not loaded.get("ok"):
        return loaded
    doc = loaded["manifest"]
    return {
        "ok": True,
        "code": "SHELF-SERVE-LOCAL",
        "spec": SHELF_SPEC,
        "author": SHELF_AUTHOR,
        "person_id": PERSON_ID,
        "mode": "serve-last-local",
        "worker_up": False,
        "re_expand_from_archive": True,
        "manifest": doc,
        "sha256": loaded["sha256"],
        "tip_hashes": list(doc.get("tip_hashes") or []),
        "lockset_hash": doc.get("lockset_hash") or "",
        "receipts": doc.get("receipts") or [],
        "items": doc.get("items") or [],
        "note": "Worker dead or unprobed. Last local cold-shelf. No invented tip.",
        "laws": list(LAWS),
    }


def re_expand_from_archive(store: Any) -> dict[str, Any]:
    """RE-EXPAND-FROM-ARCHIVE: the last sealed shelf is the archive."""
    rec = serve_last_local(store)
    if rec.get("ok"):
        rec["code"] = "SHELF-RE-EXPAND"
        rec["law"] = "RE-EXPAND-FROM-ARCHIVE"
    return rec


def merge_verified_items(store: Any, incoming: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Union by hash. Never rewrite an existing item."""
    from azieltether.item import Item
    from azieltether.store import Store

    st: Store = store
    chain = st.chain()
    clean: list[dict[str, Any]] = []
    skipped = 0
    for raw in incoming:
        if not isinstance(raw, Mapping) or not item_digest_ok(raw):
            skipped += 1
            continue
        try:
            clean.append(Item.from_mapping(raw).as_dict())
        except Exception:
            skipped += 1
    lock = st.lockset() or st.seal_lockset()
    cite = chain.last_good_tip() or chain.last_hash()
    merged = chain.merge(
        clean,
        operator=False,
        cite=cite,
        lockset=str(lock.get("hash") or ""),
    )
    merged["skipped_poison"] = skipped
    return merged


def _configured_urls(store: Any, extra: Sequence[str] | None) -> list[str]:
    urls: list[str] = []
    env = os.environ.get(SHELF_URLS_ENV, "").strip()
    if env:
        urls.extend(p.strip() for p in env.split(",") if p.strip())
    if store is not None:
        urls.extend(store.shelf_urls())
    if extra:
        urls.extend(str(u).strip() for u in extra if str(u).strip())
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def shelf_sync(
    store: Any,
    *,
    urls: Sequence[str] | None = None,
    expected_sha256: str | None = None,
    host: str | None = None,
    probe: bool = True,
    incoming: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Up → pull+seal; down → last local; restore → hash reconcile."""
    from azieltether.client import ingest_item, post_tip, probe_health, pull_shelf_card
    from azieltether.lattice import bind_surfaces
    from azieltether.protocol import MODE_PEER, MODE_PREFER, MODE_RECONCILE, offline_forced
    from azieltether.store import Store

    st: Store = store
    rewrite = refuse_rewrite_key(incoming)
    if not rewrite.get("ok"):
        return rewrite
    fan = refuse_fan(incoming)
    if not fan.get("ok"):
        return fan
    if incoming:
        lie = refuse_lie_to_survive(
            worker_up_claimed=bool(incoming.get("worker_up")) if "worker_up" in incoming else None,
            worker_actually_up=None,
            claim_ipfs_live=bool(incoming.get("ipfs_live") or incoming.get("cid")),
            claim_multihome_dns=bool(incoming.get("multihome_dns") or incoming.get("anycast")),
            claim_rewrite_to_survive=bool(incoming.get("rewrite_to_survive")),
            claim_worker_holds_chain=bool(incoming.get("worker_holds_chain")),
            claim_zenodo_live=bool(incoming.get("zenodo_live") or incoming.get("doi_live")),
            claim_usb_live=bool(incoming.get("usb_live") and incoming.get("operator_attest") is False),
        )
        if incoming.get("ipfs_live") or incoming.get("cid") or incoming.get("multihome_dns") or incoming.get("anycast") or incoming.get("rewrite_to_survive") or incoming.get("worker_holds_chain") or incoming.get("zenodo_live") or incoming.get("doi_live"):
            if not lie.get("ok"):
                return lie

    if not probe or offline_forced():
        health: dict[str, Any] = {
            "ok": False,
            "prefer_central": False,
            "reason": "offline_forced" if offline_forced() else "not_probed",
        }
    else:
        health = probe_health(host)
    worker_up = bool(health.get("prefer_central"))
    if incoming and incoming.get("worker_up") is True and not worker_up:
        return refuse_lie_to_survive(worker_up_claimed=True, worker_actually_up=False)

    state = st.state()
    was_down = state.get("last_central_ok") is False
    pulls: list[dict[str, Any]] = []
    merged = {"added": 0, "skipped": 0}
    ingest_acks: list[str] = []
    card: dict[str, Any] = {}
    plane_a_pull: dict[str, Any] = {**plane_a_card(), "pulled": False}
    stored = st.plane_b()
    incoming_doi = incoming.get("zenodo_doi") if incoming else None
    incoming_zenodo_url = incoming.get("zenodo_url") if incoming else None
    incoming_b_url = None
    if incoming:
        incoming_b_url = incoming.get("plane_b_url") or incoming.get("alt_shelf_url")
    stored_url = stored.get("url") or None
    if stored_url and "zenodo" in str(stored_url).lower():
        stored_url = None
    plane_b = plane_b_status(
        doi=incoming_doi,
        url=(
            incoming_b_url
            if incoming_b_url is not None
            else (incoming_zenodo_url if incoming_zenodo_url is not None else stored_url)
        ),
        sha256=expected_sha256 or stored.get("sha256"),
        verified=bool(stored.get("verified")) and not incoming_doi,
    )
    if incoming and (incoming.get("zenodo_doi") or incoming.get("zenodo_url")) and not plane_b.get("ok"):
        return plane_b
    if incoming and incoming.get("usb_live") and not st.plane_c_attest().get("usb_tip_pack_live"):
        return refuse_operator_attest(attested=False, sha256sum_ok=False)
    if incoming and incoming_b_url and plane_b.get("code") != "SHELF-DOI-REFUSED":
        st.set_plane_b(url=incoming_b_url, sha256=expected_sha256, verified=False)
    if plane_b.get("ok") and plane_b.get("url") and plane_b.get("verified"):
        urls = list(urls or []) + [str(plane_b["url"])]

    for url in _configured_urls(st, urls):
        pulled = fetch_manifest(url, expected_sha256=expected_sha256)
        pulls.append({k: v for k, v in pulled.items() if k != "manifest"})
        if not pulled.get("ok"):
            continue
        if plane_b_host(url) and pulled.get("checked"):
            st.set_plane_b(url=url, sha256=pulled.get("bytes_sha256"), verified=True)
            plane_b = plane_b_status(
                url=url,
                sha256=pulled.get("bytes_sha256"),
                verified=True,
            )
        doc = pulled["manifest"]
        items = doc.get("items") if isinstance(doc.get("items"), list) else []
        known = st.chain().hashes() | {str(i.get("hash")) for i in items if isinstance(i, dict)}
        lie = refuse_lie_to_survive(
            invented_tips=list(doc.get("tip_hashes") or []),
            known_hashes=list(known),
        )
        if not lie.get("ok"):
            pulls[-1] = lie
            continue
        merged = merge_verified_items(st, items)

    active_plane = PLANE_C
    if worker_up:
        if probe:
            plane_a_pull = pull_plane_a(host=host)
            plane_a_pull["pulled"] = True
        card = pull_shelf_card(host)
        chain = st.chain()
        tips = bind_surfaces(chain, node_id=st.node_id())
        st.write_tips(tips)
        worker_tip = (tips.get("surfaces") or {}).get("worker") or {}
        ack = post_tip(worker_tip, host=host)
        if ack.get("ok") and (ack.get("tip") or {}).get("hash"):
            ingest_acks.append(str(ack["tip"]["hash"]))
        for item in chain.items:
            rec = ingest_item(item.as_dict(), host=host)
            if rec.get("ok") or rec.get("accepted"):
                ingest_acks.append(item.hash)
        active_plane = PLANE_A
        if was_down:
            mode = MODE_RECONCILE
            code = "SHELF-RESTORE"
            note = "Worker restored. Plane A pull + hash reconcile. Existing items unchanged. Never rewrite."
        else:
            mode = MODE_PREFER
            code = "SHELF-UP"
            note = "Worker up. Plane A (four CF hubs, same tunnel). Ingest-as-receipt. Local Plane C sealed."
    else:
        mode = MODE_PEER
        local = serve_last_local(st)
        active_plane = PLANE_C
        if local.get("ok"):
            code = "SHELF-DOWN"
            note = "Worker dead or unprobed. Serving last Plane C local cold-shelf."
        else:
            code = local.get("code") or "SHELF-DOWN"
            note = str(local.get("note") or "Worker down and no Plane C shelf yet.")

    sealed = seal_shelf(st, ingest_acks=ingest_acks)
    state = st.state()
    state.update(
        {
            "mode": mode,
            "last_central_ok": worker_up,
            "last_shelf_code": sealed.get("code") if sealed.get("ok") else code,
        }
    )
    st.write_state(state)
    local_now = load_last_shelf(st)
    return {
        "ok": bool(sealed.get("ok")),
        "code": code if sealed.get("ok") or not worker_up else sealed.get("code") or code,
        "spec": SHELF_SPEC,
        "sister_spec": SISTER_SPEC,
        "author": SHELF_AUTHOR,
        "person_id": PERSON_ID,
        "mode": mode,
        "worker_up": worker_up,
        "central": health,
        "worker_card": {k: card.get(k) for k in ("ok", "code", "durable_store", "zero_retention", "spec") if k in card or True},
        "pulls": pulls,
        "merge": merged,
        "seal": {k: v for k, v in sealed.items() if k != "items"},
        "tip_hashes": (local_now.get("manifest") or {}).get("tip_hashes") or sealed.get("tip_hashes") or [],
        "lockset_hash": (local_now.get("manifest") or {}).get("lockset_hash") or sealed.get("lockset_hash") or "",
        "sha256": sealed.get("sha256") or local_now.get("sha256"),
        "note": note,
        "real": list(REAL),
        "mock": sorted(SLOTS.keys()),
        "slots": {k: {"code": v, "live": False} for k, v in SLOTS.items()},
        "laws": list(LAWS),
        "vpn": False,
        "miragegrid": False,
        "mesh_on_public_boards": False,
        "rewrite_key": False,
        "lie_to_survive": False,
        "durable_worker_store": False,
        "active_plane": active_plane,
        "planes": {
            "A": plane_a_pull,
            "B": plane_b,
            "C": plane_c_card(st),
        },
        "tip_ref": operator_tip_ref(),
        "lamb_lens": LAMB_LENS,
    }


def export_usb(store: Any, dest: str | Path) -> dict[str, Any]:
    """Airgap a USB shelf: manifest + sha256 + queue + tips + operator note."""
    sealed = seal_shelf(store)
    if not sealed.get("ok"):
        return sealed
    root = Path(dest)
    root.mkdir(parents=True, exist_ok=True)
    src = store.shelf_dir
    for name in ("manifest.json", "manifest.sha256", "queue.jsonl"):
        shutil.copy2(src / name, root / name)
    tips = store.tips()
    (root / "tips.json").write_text(
        json.dumps(tips, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lock = store.lockset()
    if lock:
        (root / "lockset.json").write_text(
            json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    readme = (
        "AzielTether cold-shelf (COLD-SHELF-TETHER-1.0)\n"
        "Author: Aziel Eliab only\n"
        f"Person @id: {PERSON_ID}\n"
        f"Sister: aziel-corpus {SISTER_SPEC} — cite the same lockset tip hashes.\n"
        f"Laws: {CROSS_NETWORK_SPEC}, {NO_LIE_SPEC}. No rewrite key. No lie-to-survive.\n"
        f"manifest sha256 (canonical): {sealed['sha256']}\n"
        f"manifest.json bytes sha256: {sealed['bytes_sha256']}\n"
        "On the airgapped machine:\n"
        f"  azieltether shelf usb-import --src {root}\n"
        "On this USB, verify then attest (USB tip-pack is not LIVE until then):\n"
        "  sha256sum -c manifest.sha256\n"
        f"  azieltether shelf attest --src {root}\n"
        f"Refuse {CNS_OPERATOR_ATTEST} until sha256sum -c + operator attest.\n"
        "Refuse if SHA-256 mismatches. Multi-homed DNS / IPFS / auto-publish / invented DOIs are SLOT.\n"
        "Zenodo is IP-banned. Do not invent a DOI.\n"
        "Planes: A = four CF hubs same tunnel (does not survive CF yank). "
        "B = Codeberg / archive.org / GitFlic SLOT until hash-verify. "
        "C = this USB / last local copy. Worker-up A; Worker-down last C; restore hash-reconcile never rewrite.\n"
        f"Tip ref {OPERATOR_DATE}: lockset tip {OPERATOR_LOCKSET_TIP}\n"
        f"pack_sha256 {OPERATOR_PACK_SHA256}\n"
        f"Laws: {CROSS_NETWORK_SPEC}, {NO_LIE_SPEC}, {SISTER_SPEC}. NO-FAN. Lamb Lens: {LAMB_LENS}.\n"
    )
    (root / "README.txt").write_text(readme, encoding="utf-8")
    return {
        "ok": True,
        "code": "SHELF-USB-EXPORT",
        "dest": str(root),
        "sha256": sealed["sha256"],
        "bytes_sha256": sealed["bytes_sha256"],
        "tip_hashes": sealed["tip_hashes"],
        "lockset_hash": sealed["lockset_hash"],
        "author": SHELF_AUTHOR,
        "person_id": PERSON_ID,
        "spec": SHELF_SPEC,
        "sister_spec": SISTER_SPEC,
        "note": "Unplug the USB. Import on the airgapped node with shelf usb-import.",
    }


def import_usb(
    store: Any,
    src: str | Path,
    *,
    expected_sha256: str | None = None,
    claim_live: bool = False,
    operator_attest: bool = False,
) -> dict[str, Any]:
    """Verify a USB shelf and merge by hash. Never rewrite. LIVE needs attest."""
    root = Path(src)
    manifest = root / "manifest.json"
    if not manifest.is_file():
        return _refuse("SHELF-USB-MISSING", "USB shelf needs manifest.json.", src=str(root))
    data = manifest.read_bytes()
    sidecar = root / "manifest.sha256"
    expect = expected_sha256
    if expect is None and sidecar.is_file():
        expect = sidecar.read_text(encoding="utf-8").strip().split()[0]
    check = verify_sha256(data, expect)
    if not check.get("ok"):
        return check
    parsed = parse_manifest(data)
    if not parsed.get("ok"):
        return parsed
    doc = parsed["manifest"]
    items = doc.get("items") if isinstance(doc.get("items"), list) else []
    queue = root / "queue.jsonl"
    if queue.is_file():
        for line in queue.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                return _refuse("SHELF-USB-POISON", "queue.jsonl has a broken line.")
            if isinstance(raw, dict):
                items.append(raw)
    if claim_live and not operator_attest:
        return refuse_operator_attest(attested=False, sha256sum_ok=bool(check.get("ok")))
    merged = merge_verified_items(store, items)
    sealed = seal_shelf(store)
    attest = None
    if operator_attest:
        attest = attest_usb(
            store,
            root,
            expected_sha256=expected_sha256 or check.get("expected") or check.get("sha256"),
        )
        if not attest.get("ok"):
            return attest
    return {
        "ok": bool(sealed.get("ok")),
        "code": "SHELF-USB-IMPORT",
        "src": str(root),
        "merge": merged,
        "seal": {k: v for k, v in sealed.items() if k != "items"},
        "sha256": parsed["sha256"],
        "bytes_sha256": check.get("sha256"),
        "usb_tip_pack_live": bool(attest and attest.get("usb_tip_pack_live")),
        "attest": attest,
        "author": SHELF_AUTHOR,
        "person_id": PERSON_ID,
        "spec": SHELF_SPEC,
        "sister_spec": SISTER_SPEC,
        "rewrite_key": False,
        "tip_ref": operator_tip_ref(),
        "lamb_lens": LAMB_LENS,
    }


def sha256sum_c(src: str | Path, *, expected: str | None = None) -> dict[str, Any]:
    """Operator `sha256sum -c` on the USB tip-pack sidecar."""
    root = Path(src)
    manifest = root / "manifest.json"
    if not manifest.is_file():
        return _refuse("SHELF-USB-MISSING", "USB shelf needs manifest.json for sha256sum -c.", src=str(root))
    data = manifest.read_bytes()
    sidecar = root / "manifest.sha256"
    sidecar_hex = None
    if sidecar.is_file():
        sidecar_hex = sidecar.read_text(encoding="utf-8").strip().split()[0]
    want = expected or sidecar_hex
    if not want:
        return refuse_operator_attest(attested=False, sha256sum_ok=False)
    check = verify_sha256(data, want)
    if not check.get("ok"):
        return check
    return {
        "ok": True,
        "code": "SHELF-SHA256SUM-C",
        "sha256": check["sha256"],
        "expected": check.get("expected"),
        "sidecar": sidecar_hex,
        "checked": True,
        "author": SHELF_AUTHOR,
        "law": NO_LIE_SPEC,
    }


def attest_usb(
    store: Any,
    src: str | Path,
    *,
    expected_sha256: str | None = None,
    operator_attest: bool = True,
    pack_sha256: str | None = None,
    lockset_tip: str | None = None,
) -> dict[str, Any]:
    """Mark a USB tip-pack LIVE after sha256sum -c. Refuse CNS-OPERATOR-ATTEST until then."""
    if not operator_attest:
        return refuse_operator_attest(attested=False, sha256sum_ok=False)
    check = sha256sum_c(src, expected=expected_sha256)
    if not check.get("ok"):
        return check
    if pack_sha256:
        pack_check = verify_sha256(Path(src).joinpath("manifest.json").read_bytes(), pack_sha256)
        if not pack_check.get("ok"):
            return pack_check
    tip = lockset_tip or OPERATOR_LOCKSET_TIP
    try:
        tip = require_hex64("lockset_tip", tip)
    except ValueError as exc:
        return _refuse("SHELF-SHA256-BAD", str(exc))
    rec = {
        "ok": True,
        "code": "SHELF-OPERATOR-ATTEST",
        "plane": PLANE_C,
        "usb_tip_pack_live": True,
        "sha256sum_c": True,
        "operator_attest": True,
        "operator_date": OPERATOR_DATE,
        "src": str(Path(src)),
        "sha256": check["sha256"],
        "lockset_tip": tip,
        "pack_sha256": pack_sha256 or check["sha256"],
        "tip_ref": operator_tip_ref(),
        "spec": SHELF_SPEC,
        "sister_spec": SISTER_SPEC,
        "cross_network": CROSS_NETWORK_SPEC,
        "no_lie": NO_LIE_SPEC,
        "laws": list(LAWS),
        "lamb_lens": LAMB_LENS,
        "author": SHELF_AUTHOR,
        "person_id": PERSON_ID,
        "rewrite_key": False,
        "note": "Operator attested after sha256sum -c. USB tip-pack LIVE. Never rewrite.",
    }
    store.set_plane_c_attest(rec)
    return rec


def refuse_delete_shelf(path: str | Path) -> None:
    raise AppendOnlyError("cold-shelf is append-only; data outlives creators")


def hash_holds_absolute(digest_ok: bool, votes_for: int = 0) -> bool:
    return hash_holds(digest_ok=digest_ok, votes_for=votes_for)


def cite_lockset_ok(cite: str | None, lockset: str | None) -> bool:
    return cite_ok(cite, lockset)


def law_card() -> dict[str, Any]:
    return {
        "ok": True,
        "spec": SHELF_SPEC,
        "sister_spec": SISTER_SPEC,
        "cross_network": CROSS_NETWORK_SPEC,
        "no_lie": NO_LIE_SPEC,
        "product": PRODUCT,
        "author": SHELF_AUTHOR,
        "identity": SHELF_AUTHOR,
        "person_id": PERSON_ID,
        "durable_store": False,
        "zero_retention": True,
        "worker_holds_chain": False,
        "rewrite_key": False,
        "lie_to_survive": False,
        "fan": False,
        "multihome_dns": False,
        "ipfs": False,
        "auto_publish": False,
        "anycast": False,
        "az_generator": False,
        "zenodo_dead": True,
        "invented_doi": False,
        "planes": {
            "A": plane_a_card(),
            "B": plane_b_status(),
            "C": plane_c_card(),
        },
        "tip_ref": operator_tip_ref(),
        "real": list(REAL),
        "mock": sorted(SLOTS.keys()),
        "slots": {k: {"code": v, "live": False} for k, v in SLOTS.items()},
        "laws": list(LAWS),
        "law": LAW,
        "lamb_lens": LAMB_LENS,
        "no_fan": True,
    }
