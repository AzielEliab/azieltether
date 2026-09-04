"""Canonical encoding for AzielTether items.

UTF-8 JSON, sorted keys, no extra whitespace
(``separators=(",", ":")``, ``sort_keys=True``, ``ensure_ascii=False``).

The item's own ``hash`` field is excluded from the encoding. SHA-256 of
those bytes is the item hash (lowercase hex). This matches the AZ-CLCE
tether-queue contract so sibling queues verify here.

Genesis ``prev_hash`` is 64 zero hex characters.

Author: Aziel Eliab.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

GENESIS_PREV_HASH = "0" * 64


def canonical_json(obj: Mapping[str, Any]) -> str:
    """Return canonical JSON for a mapping (hash field must already be absent)."""
    return json.dumps(dict(obj), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def body_without_hash(item: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in item.items() if k != "hash"}


def digest_mapping(item: Mapping[str, Any]) -> str:
    """SHA-256 (lowercase hex) of the canonical body excluding ``hash``."""
    return hashlib.sha256(canonical_json(body_without_hash(item)).encode("utf-8")).hexdigest()


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def require_hex64(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    text = value.strip().lower()
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise ValueError(f"{name} must be 64 lowercase hex characters")
    return text
