"""Ed25519 node keys and SHA-256 helpers. Keep crypto simple."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def b64encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def b64decode(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"), validate=True)


def generate_keypair() -> tuple[str, str]:
    """Return (private_b64, public_b64) raw 32-byte Ed25519 keys."""
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    priv_raw = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    pub_raw = public.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return b64encode(priv_raw), b64encode(pub_raw)


def sign_bytes(private_b64: str, message: bytes) -> str:
    private = Ed25519PrivateKey.from_private_bytes(b64decode(private_b64))
    return b64encode(private.sign(message))


def verify_bytes(public_b64: str, message: bytes, signature_b64: str) -> bool:
    try:
        public = Ed25519PublicKey.from_public_bytes(b64decode(public_b64))
        public.verify(b64decode(signature_b64), message)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no extra spaces, UTF-8 round-trip."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def node_id_from_pubkey(public_b64: str) -> str:
    return sha256_hex(b64decode(public_b64))
