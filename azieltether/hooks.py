"""Structure-verify extension points. SPRE/CLCE and siblings register here.

On every sensed upload or download, AzielTether runs ``on_transfer(event)``
after verifying the whole local structure. Sibling engines rescore from
that callback; they are not imported by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from azieltether.chain import ChainError, verify_batch
from azieltether.constants import SCOPES, WORK_SCOPES

HookFn = Callable[[dict[str, Any]], Any]

_HOOKS: dict[str, HookFn] = {}


@dataclass
class StructureReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    tips: dict[str, str] = field(default_factory=dict)
    batch_ok: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "tips": dict(self.tips),
            "batch_ok": self.batch_ok,
        }


def register(name: str, fn: HookFn) -> None:
    """Register ``fn(event_dict)`` for every transfer. Name is a sibling slug."""
    if not name or not callable(fn):
        raise ValueError("hook name and callable are required")
    _HOOKS[str(name)] = fn


def unregister(name: str) -> None:
    _HOOKS.pop(str(name), None)


def clear_hooks() -> None:
    _HOOKS.clear()


def registered() -> list[str]:
    return sorted(_HOOKS)


def verify_structure(store: Any, batch: Mapping[str, Any] | None = None) -> StructureReport:
    """Walk every local chain and optionally the incoming batch."""
    errors: list[str] = []
    batch_ok = True
    if batch is not None:
        try:
            verify_batch(batch)
        except (ChainError, KeyError, TypeError) as exc:
            batch_ok = False
            errors.append(f"batch: {exc}")
    chain_ok, chain_errors = store.chain_ok()
    errors.extend(chain_errors)
    tips = {}
    for scope in SCOPES:
        tip = store.tip_hash(scope)
        if tip:
            tips[scope] = tip
    return StructureReport(ok=batch_ok and chain_ok and not errors, errors=errors, tips=tips, batch_ok=batch_ok)


def transfer_event(
    *,
    direction: str,
    batch: Mapping[str, Any],
    via: str,
    store: Any,
    offline: bool = False,
) -> dict[str, Any]:
    if direction not in {"upload", "download"}:
        raise ValueError("direction must be upload or download")
    report = verify_structure(store, batch)
    return {
        "direction": direction,
        "via": via,
        "offline": bool(offline),
        "scope": batch.get("scope"),
        "kind": batch.get("kind"),
        "hash": batch.get("hash"),
        "batch": dict(batch),
        "structure": report.to_dict(),
        "work_scopes": list(WORK_SCOPES),
        "note": (
            "Whole-structure verify. Sibling engines (SPRE, AZ-CLCE, …) "
            "register azieltether.hooks.register(name, fn) and rescore here."
        ),
    }


def on_transfer(event: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Run every registered hook. Built-in structure result is always first."""
    payload = dict(event)
    results = [
        {
            "hook": "structure",
            "ok": bool((payload.get("structure") or {}).get("ok", False)),
            "result": payload.get("structure"),
        }
    ]
    for name, fn in list(_HOOKS.items()):
        try:
            results.append({"hook": name, "ok": True, "result": fn(payload)})
        except Exception as exc:  # noqa: BLE001 — isolate sibling engines
            results.append({"hook": name, "ok": False, "error": str(exc)})
    payload["hooks"] = results
    return results
