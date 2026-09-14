"""SPLIT THE WIRES mesh law — executable protocol.

Two planes, two sockets. Fast tick never carries a body. Payload is
receiver-pull on the 777s gate. Update is proof, not a timer.

Author: Aziel Eliab only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from azieltether.canon import require_hex64, sha256_hex
from azieltether.errors import WiresError

WIRES_SPEC = "SPLIT-THE-WIRES-1.0"
WIRES_AUTHOR = "Aziel Eliab"
TICK_MIN_MS = 500
TICK_MAX_MS = 1000
GATE_DWELL_S = 777
TICK_SOCKET = "tick"
GATE_SOCKET = "gate"
PLANE_TICK = "tick"
PLANE_PAYLOAD = "payload"
TICK_FRAME_BYTES = 256
TICK_MAGIC = b"ATW1"
TICK_PLANE_BYTE = 0x01
PUSH_FANOUT = False
AUTO_SPLICE = False
CLOCK_DESYNC_IS_YES = False
QUORUM_OUTVOTES_HASH = False
TICK_FORBIDDEN = frozenset(
    {
        "body",
        "payload",
        "diff",
        "file",
        "items",
        "data",
        "blob",
        "content",
        "chain",
    }
)

LAW = (
    "SPLIT THE WIRES. Fast 0.5–1s tick: presence + tip hash only. "
    "Fixed-size. No body/diff/file on the tick plane. Payload on the "
    "second plane the receiver pulls — never sender push fan-out. "
    "Update is proof not timer: cite prev + lockset, fail-closed; "
    "777s dwell after valid cite; clock desync is not yes; ambiguous "
    "tip isolates. Equivocation ends the peer (same prev, two tips → "
    "lock/isolate). Quorum cannot outvote a broken hash. Emit last "
    "locally after verify. Phoenix is local to the failed node only. "
    "No unsend of an unverified body. Partition: split brain does not "
    "auto-splice; rejoin needs cite + operator/lockset. Heartbeat loss "
    "is not poison and does not apply the last packet. The 1s loop and "
    "the 777s gate never share a socket. Author: Aziel Eliab only."
)


def tick_interval_ok(ms: float) -> bool:
    return TICK_MIN_MS <= float(ms) <= TICK_MAX_MS


def bind_socket(plane: str) -> str:
    if plane == PLANE_TICK:
        return TICK_SOCKET
    if plane == PLANE_PAYLOAD:
        return GATE_SOCKET
    raise WiresError(f"unknown plane {plane}")


def assert_distinct_sockets(tick_socket: str, gate_socket: str) -> None:
    if not tick_socket or not gate_socket or tick_socket == gate_socket:
        raise WiresError("1s loop and 777s gate never share a socket")
    if tick_socket != TICK_SOCKET or gate_socket != GATE_SOCKET:
        raise WiresError("socket names are tick and gate")


def assert_plane_socket(plane: str, socket: str) -> None:
    expected = bind_socket(plane)
    if socket != expected:
        raise WiresError(f"{plane} plane must use the {expected} socket")
    if plane == PLANE_TICK and socket == GATE_SOCKET:
        raise WiresError("1s loop and 777s gate never share a socket")
    if plane == PLANE_PAYLOAD and socket == TICK_SOCKET:
        raise WiresError("1s loop and 777s gate never share a socket")


def _hex32(name: str, value: str) -> bytes:
    text = require_hex64(name, value)
    return bytes.fromhex(text)


def tick_frame(node_id: str, tip_hash: str) -> bytes:
    """Fixed-size tick: magic + plane + presence + tip. No body."""
    node = _hex32("node_id", node_id)
    tip = _hex32("tip_hash", tip_hash)
    raw = TICK_MAGIC + bytes([TICK_PLANE_BYTE]) + node + tip
    if len(raw) > TICK_FRAME_BYTES:
        raise WiresError("tick frame overflow")
    return raw + (b"\x00" * (TICK_FRAME_BYTES - len(raw)))


def parse_tick_frame(raw: bytes) -> dict[str, str]:
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != TICK_FRAME_BYTES:
        raise WiresError("tick frame must be fixed-size")
    if raw[:4] != TICK_MAGIC or raw[4] != TICK_PLANE_BYTE:
        raise WiresError("tick frame magic/plane refused")
    if any(raw[69:]):
        raise WiresError("tick frame pad must be empty (no smuggled body)")
    return {
        "plane": PLANE_TICK,
        "node_id": raw[5:37].hex(),
        "tip_hash": raw[37:69].hex(),
    }


def tick_forbidden(body: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(body, Mapping):
        return []
    return sorted(k for k in body if k.lower() in TICK_FORBIDDEN)


def encode_tick(*, node_id: str, tip_hash: str) -> dict[str, Any]:
    frame = tick_frame(node_id, tip_hash)
    parsed = parse_tick_frame(frame)
    return {
        "plane": PLANE_TICK,
        "spec": WIRES_SPEC,
        "socket": TICK_SOCKET,
        "node_id": parsed["node_id"],
        "tip_hash": parsed["tip_hash"],
        "frame": frame.hex(),
        "frame_bytes": TICK_FRAME_BYTES,
        "author": WIRES_AUTHOR,
    }


def accept_tick(body: Mapping[str, Any] | None, *, socket: str = TICK_SOCKET) -> dict[str, Any]:
    """Presence + tip only. Fail-closed on body/diff/file or wrong socket."""
    assert_plane_socket(PLANE_TICK, socket)
    if not isinstance(body, Mapping):
        raise WiresError("tick body required")
    banned = tick_forbidden(body)
    if banned:
        raise WiresError("no body/diff/file on the tick plane")
    frame_hex = str(body.get("frame") or "")
    if frame_hex:
        try:
            raw = bytes.fromhex(frame_hex)
        except ValueError as exc:
            raise WiresError("tick frame must be hex") from exc
        parsed = parse_tick_frame(raw)
        node_id = parsed["node_id"]
        tip_hash = parsed["tip_hash"]
        if body.get("node_id") and require_hex64("node_id", str(body["node_id"])) != node_id:
            raise WiresError("tick node_id does not match frame")
        if body.get("tip_hash") and require_hex64("tip_hash", str(body["tip_hash"])) != tip_hash:
            raise WiresError("tick tip_hash does not match frame")
    else:
        try:
            node_id = require_hex64("node_id", body.get("node_id"))
            tip_hash = require_hex64("tip_hash", body.get("tip_hash"))
        except ValueError as exc:
            raise WiresError("ambiguous tip = isolate") from exc
        raw = tick_frame(node_id, tip_hash)
    if not tip_hash or tip_hash == "0" * 64 and not node_id:
        raise WiresError("ambiguous tip = isolate")
    return {
        "ok": True,
        "code": "WIRES-TICK",
        "plane": PLANE_TICK,
        "socket": TICK_SOCKET,
        "spec": WIRES_SPEC,
        "node_id": node_id,
        "tip_hash": tip_hash,
        "frame": raw.hex(),
        "frame_bytes": TICK_FRAME_BYTES,
        "author": WIRES_AUTHOR,
    }


def pull_request(*, cite: str, lockset: str, want: Sequence[str] | None = None) -> dict[str, Any]:
    """Receiver-pull envelope. Never a sender push."""
    try:
        prev = require_hex64("cite", cite)
        lock = require_hex64("lockset", lockset)
    except ValueError as exc:
        raise WiresError("cite prev + lockset required (fail-closed)") from exc
    wanted: list[str] = []
    for raw in want or ():
        try:
            wanted.append(require_hex64("want", raw))
        except ValueError as exc:
            raise WiresError("payload want must be hash-absolute") from exc
    return {
        "ok": True,
        "plane": PLANE_PAYLOAD,
        "socket": GATE_SOCKET,
        "spec": WIRES_SPEC,
        "cite": prev,
        "lockset": lock,
        "want": wanted,
        "push_fanout": False,
        "author": WIRES_AUTHOR,
    }


def refuse_push_fanout(body: Mapping[str, Any] | None) -> dict[str, Any]:
    items = []
    if isinstance(body, Mapping):
        raw = body.get("items") or body.get("payload") or body.get("body")
        if isinstance(raw, list):
            items = raw
        elif raw:
            items = [raw]
    if items:
        return {
            "ok": False,
            "code": "WIRES-PUSH-REFUSED",
            "plane": PLANE_PAYLOAD,
            "push_fanout": False,
            "note": "Receiver pulls. Sender never push-fans a body.",
            "author": WIRES_AUTHOR,
        }
    return {"ok": True, "code": "WIRES-NO-PUSH", "push_fanout": False, "author": WIRES_AUTHOR}


def cite_ok(cite: str | None, lockset: str | None) -> bool:
    try:
        if not cite or not lockset:
            return False
        require_hex64("cite", cite)
        require_hex64("lockset", lockset)
    except ValueError:
        return False
    return True


def dwell_ready(
    *,
    cited_at: float,
    now: float,
    dwell_s: float = GATE_DWELL_S,
) -> bool:
    """777s after a valid cite. Clock desync is not yes."""
    if CLOCK_DESYNC_IS_YES:
        return True
    if now < cited_at:
        return False
    return (now - cited_at) >= dwell_s


def apply_update(
    *,
    cite: str | None,
    lockset: str | None,
    cited_at: float,
    now: float,
    tip_hashes: Sequence[str] | None = None,
    digest_ok: bool = True,
    votes_for: int = 0,
    dwell_s: float = GATE_DWELL_S,
) -> dict[str, Any]:
    """Proof, not timer. Fail-closed."""
    if not cite_ok(cite, lockset):
        return {
            "ok": False,
            "code": "WIRES-CITE-REQUIRED",
            "applied": False,
            "author": WIRES_AUTHOR,
        }
    if not digest_ok or not hash_holds(digest_ok=digest_ok, votes_for=votes_for):
        return {
            "ok": False,
            "code": "WIRES-HASH-ABSOLUTE",
            "applied": False,
            "author": WIRES_AUTHOR,
        }
    tips = [t for t in (tip_hashes or ()) if t]
    if len(set(tips)) > 1:
        return {
            "ok": False,
            "code": "WIRES-AMBIGUOUS-TIP",
            "applied": False,
            "isolate": True,
            "author": WIRES_AUTHOR,
        }
    if not dwell_ready(cited_at=cited_at, now=now, dwell_s=dwell_s):
        return {
            "ok": False,
            "code": "WIRES-DWELL",
            "applied": False,
            "dwell_s": dwell_s,
            "author": WIRES_AUTHOR,
        }
    return {
        "ok": True,
        "code": "WIRES-APPLY",
        "applied": True,
        "cite": cite,
        "lockset": lockset,
        "author": WIRES_AUTHOR,
    }


def hash_holds(*, digest_ok: bool, votes_for: int = 0, votes_against: int = 0) -> bool:
    """Quorum cannot outvote a broken hash."""
    if QUORUM_OUTVOTES_HASH:
        return bool(digest_ok) or votes_for > votes_against
    if not digest_ok:
        return False
    return True


@dataclass(frozen=True)
class Equivocation:
    node_id: str
    prev_hash: str
    tip_hashes: tuple[str, ...]


def detect_equivocation(
    ticks: Sequence[Mapping[str, Any]],
) -> list[Equivocation]:
    """Same peer, same prev, two tips → lock/isolate that peer."""
    by_peer_prev: dict[tuple[str, str], list[str]] = {}
    for raw in ticks:
        node = str(raw.get("node_id") or "")
        prev = str(raw.get("prev_hash") or raw.get("cite") or "")
        tip = str(raw.get("tip_hash") or raw.get("hash") or "")
        if not node or not prev or not tip:
            continue
        key = (node, prev)
        by_peer_prev.setdefault(key, [])
        if tip not in by_peer_prev[key]:
            by_peer_prev[key].append(tip)
    found: list[Equivocation] = []
    for (node, prev), tips in by_peer_prev.items():
        if len(tips) > 1:
            found.append(Equivocation(node_id=node, prev_hash=prev, tip_hashes=tuple(tips)))
    return found


def equivocation_verdict(ticks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    forks = detect_equivocation(ticks)
    if not forks:
        return {"ok": True, "code": "WIRES-OK", "isolate": [], "author": WIRES_AUTHOR}
    return {
        "ok": False,
        "code": "WIRES-EQUIVOCATION",
        "isolate": [f.node_id for f in forks],
        "forks": [
            {"node_id": f.node_id, "prev_hash": f.prev_hash, "tip_hashes": list(f.tip_hashes)}
            for f in forks
        ],
        "note": "Equivocation ends the peer. Lock/isolate. Dual-chain DAG forks from distinct nodes stay.",
        "author": WIRES_AUTHOR,
    }


def emit_last(*, verified: bool, item: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not verified:
        raise WiresError("emit last locally after verify")
    return {"ok": True, "code": "WIRES-EMIT-LOCAL", "item": dict(item or {}), "author": WIRES_AUTHOR}


def phoenix_allowed(*, failed_node_id: str, actor_node_id: str) -> bool:
    return bool(failed_node_id) and failed_node_id == actor_node_id


def refuse_unsend(*, verified: bool) -> dict[str, Any]:
    if not verified:
        raise WiresError("no unsend unverified body")
    raise WiresError("unsend refused (append-only; emit a correction)")


def partition_rejoin(*, cite: str | None, lockset: str | None, operator: bool) -> dict[str, Any]:
    if AUTO_SPLICE:
        return {"ok": True, "code": "WIRES-AUTO-SPLICE", "author": WIRES_AUTHOR}
    if cite_ok(cite, lockset) and operator:
        return {"ok": True, "code": "WIRES-REJOIN", "author": WIRES_AUTHOR}
    return {
        "ok": False,
        "code": "WIRES-NO-AUTO-SPLICE",
        "isolate": True,
        "note": "Split brain does not auto-splice. Rejoin needs cite + operator/lockset.",
        "author": WIRES_AUTHOR,
    }


def on_heartbeat_loss() -> dict[str, Any]:
    return {
        "ok": True,
        "code": "WIRES-HEARTBEAT-LOSS",
        "poison": False,
        "apply_last_packet": False,
        "isolate": False,
        "note": "Heartbeat loss is not poison and does not apply the last packet.",
        "author": WIRES_AUTHOR,
    }


def mint_lockset(tip_hashes: Iterable[str], *, node_id: str) -> dict[str, Any]:
    tips = sorted({require_hex64("tip", t) for t in tip_hashes})
    body = "azieltether-lockset:" + node_id + ":" + ",".join(tips)
    digest = sha256_hex(body)
    return {
        "hash": digest,
        "tips": tips,
        "node_id": node_id,
        "spec": WIRES_SPEC,
        "author": WIRES_AUTHOR,
        "sealed": True,
    }


def law_card() -> dict[str, Any]:
    return {
        "ok": True,
        "spec": WIRES_SPEC,
        "product": "azieltether",
        "author": WIRES_AUTHOR,
        "identity": WIRES_AUTHOR,
        "tick_ms": [TICK_MIN_MS, TICK_MAX_MS],
        "gate_dwell_s": GATE_DWELL_S,
        "tick_frame_bytes": TICK_FRAME_BYTES,
        "sockets": {
            "tick": TICK_SOCKET,
            "gate": GATE_SOCKET,
            "shared": False,
        },
        "planes": [PLANE_TICK, PLANE_PAYLOAD],
        "push_fanout": PUSH_FANOUT,
        "auto_splice": AUTO_SPLICE,
        "clock_desync_is_yes": CLOCK_DESYNC_IS_YES,
        "quorum_outvotes_hash": QUORUM_OUTVOTES_HASH,
        "law": LAW,
    }
