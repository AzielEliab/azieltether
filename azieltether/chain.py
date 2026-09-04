"""Signed hash-chained batches. Verify on accept."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping
from uuid import uuid4

from azieltether.constants import (
    FORBIDDEN_CORPUS_KINDS,
    GENESIS_PREV_HASH,
    PRODUCT,
    SCOPE_KINDS,
    SCOPES,
    VERSION,
)
from azieltether.crypto import canonical_json, sha256_hex, sign_bytes, verify_bytes


class ChainError(ValueError):
    """Batch or chain failed verification."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_hex64(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ChainError(f"{name} must be a string")
    text = value.strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ChainError(f"{name} must be 64 lowercase hex characters")
    return text


def _is_operator_library_write(batch: Mapping[str, Any]) -> bool:
    scope = str(batch.get("scope") or "")
    kind = str(batch.get("kind") or "")
    if kind in FORBIDDEN_CORPUS_KINDS:
        return True
    if scope != "aziel-corpus":
        return False
    payload = batch.get("payload")
    if not isinstance(payload, Mapping):
        return False
    if payload.get("operator") is True:
        return True
    role = str(payload.get("library_role") or payload.get("role") or "").lower()
    if role in {"operator", "aziel_library_operator", "library_operator"}:
        return True
    if payload.get("operator_record") is True:
        return True
    return False


def signing_body(batch: Mapping[str, Any]) -> dict[str, Any]:
    """Fields covered by hash and signature (no hash, no signature)."""
    return {
        "batch_id": batch["batch_id"],
        "created_at": batch["created_at"],
        "kind": batch["kind"],
        "node_id": batch["node_id"],
        "payload": batch.get("payload") if batch.get("payload") is not None else {},
        "prev_hash": batch["prev_hash"],
        "product": batch.get("product") or PRODUCT,
        "pubkey": batch["pubkey"],
        "scope": batch["scope"],
        "version": batch.get("version") or VERSION,
    }


def batch_hash(batch: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json(signing_body(batch)).encode("utf-8"))


def create_batch(
    *,
    private_b64: str,
    public_b64: str,
    node_id: str,
    scope: str,
    kind: str,
    payload: Mapping[str, Any] | None = None,
    prev_hash: str | None = None,
    created_at: str | None = None,
    batch_id: str | None = None,
) -> dict[str, Any]:
    if scope not in SCOPES:
        raise ChainError(f"unknown scope {scope!r}; allowed: {', '.join(SCOPES)}")
    allowed = SCOPE_KINDS[scope]
    if kind not in allowed:
        raise ChainError(f"kind {kind!r} is not allowed for scope {scope} (use {allowed})")
    draft = {
        "batch_id": batch_id or str(uuid4()),
        "created_at": created_at or _utc_now(),
        "kind": kind,
        "node_id": node_id,
        "payload": dict(payload or {}),
        "prev_hash": require_hex64("prev_hash", prev_hash or GENESIS_PREV_HASH),
        "product": PRODUCT,
        "pubkey": public_b64,
        "scope": scope,
        "version": VERSION,
    }
    if _is_operator_library_write(draft):
        raise ChainError(
            "peer/tether path refuses Aziel Library operator records; "
            "aziel-corpus is public ingest envelopes only"
        )
    digest = batch_hash(draft)
    signature = sign_bytes(private_b64, digest.encode("ascii"))
    return {**draft, "hash": digest, "signature": signature}


def verify_batch(batch: Mapping[str, Any], *, expected_prev: str | None = None) -> dict[str, Any]:
    if not isinstance(batch, Mapping):
        raise ChainError("batch must be an object")
    scope = batch.get("scope")
    kind = batch.get("kind")
    if scope not in SCOPES:
        raise ChainError(f"unknown scope {scope!r}")
    if kind not in SCOPE_KINDS[scope]:
        raise ChainError(f"kind {kind!r} is not allowed for scope {scope}")
    if _is_operator_library_write(batch):
        raise ChainError(
            "refused: Aziel Library operator records are not allowed on the peer/tether path"
        )
    require_hex64("prev_hash", batch.get("prev_hash"))
    digest = batch_hash(batch)
    given = batch.get("hash")
    if not isinstance(given, str) or given.lower() != digest:
        raise ChainError("hash mismatch")
    if expected_prev is not None and batch["prev_hash"] != expected_prev:
        raise ChainError(f"prev_hash {batch['prev_hash']} does not link to {expected_prev}")
    pubkey = batch.get("pubkey")
    signature = batch.get("signature")
    if not isinstance(pubkey, str) or not isinstance(signature, str):
        raise ChainError("pubkey and signature are required")
    if not verify_bytes(pubkey, digest.encode("ascii"), signature):
        raise ChainError("Ed25519 signature failed")
    return dict(batch)


def verify_chain(batches: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    expected = GENESIS_PREV_HASH
    for index, raw in enumerate(batches):
        verified = verify_batch(raw, expected_prev=expected if index else None)
        if index and not link_ok(out[-1], verified):
            raise ChainError("chain link broken")
        out.append(verified)
        expected = verified["hash"]
    return out


def link_ok(prev: Mapping[str, Any] | None, nxt: Mapping[str, Any]) -> bool:
    if prev is None:
        return nxt.get("prev_hash") == GENESIS_PREV_HASH
    return nxt.get("prev_hash") == prev.get("hash")
