"""AzielTether command line. Author Aziel Eliab."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from azieltether import __version__
from azieltether.constants import (
    AUTHOR,
    DEFAULT_HOST,
    DEFAULT_PORT,
    MOTTO,
    PRODUCT,
    SCOPE_KINDS,
    SCOPES,
)
from azieltether.wiring import build_router, public_site_health


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="azieltether",
        description=(
            "AzielTether — central × decentral software tether (Aziel Eliab). "
            "Prefer central. Fall back to peers. Reconcile on restore. "
            "Not a VPN. Live public HTTPS boards stay mesh-free."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="Print package version.")

    p_doc = sub.add_parser("doctor", help="Check central health, peer store, and local chain.")
    p_doc.add_argument("--json", action="store_true", dest="as_json")
    p_doc.add_argument("--offline", action="store_true", help="Skip public-site pings.")

    p_serve = sub.add_parser("serve", help="Local node HTTP on loopback (default 127.0.0.1:19740).")
    p_serve.add_argument("--host", default=DEFAULT_HOST)
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    sub.add_parser("ui", help="Alias of serve.")

    p_ann = sub.add_parser("announce", help="Register with central if up, else peer gossip.")
    p_ann.add_argument("--json", action="store_true", dest="as_json")

    p_push = sub.add_parser("push", help="Mint or send a signed hash-chained batch.")
    p_push.add_argument("--scope", choices=SCOPES, default="godlock")
    p_push.add_argument("--kind", default=None, help="receipt | ingest_envelope | catalog_event")
    p_push.add_argument("--payload", default="{}", help="JSON object string.")
    p_push.add_argument("--payload-file", dest="payload_file", default=None)
    p_push.add_argument("--file", dest="batch_file", default=None, help="Existing batch JSON to send.")
    p_push.add_argument("--json", action="store_true", dest="as_json")

    p_pull = sub.add_parser("pull", help="Fetch batches from central or peers.")
    p_pull.add_argument("--scope", default="*", help="godlock | aziel-corpus | aziel-runtime | *")
    p_pull.add_argument("--since", default="")
    p_pull.add_argument("--json", action="store_true", dest="as_json")

    p_rec = sub.add_parser("reconcile", help="Push local backlog to central when it returns.")
    p_rec.add_argument("--json", action="store_true", dest="as_json")

    p_batch = sub.add_parser("batch", help="Mint a local batch without sending.")
    p_batch.add_argument("--scope", choices=SCOPES, default="godlock")
    p_batch.add_argument("--kind", default=None)
    p_batch.add_argument("--payload", default="{}")
    p_batch.add_argument("--payload-file", dest="payload_file", default=None)

    return parser


def _payload(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "payload_file", None):
        text = Path(args.payload_file).read_text(encoding="utf-8")
        data = json.loads(text)
    else:
        data = json.loads(args.payload)
    if not isinstance(data, dict):
        raise SystemExit("payload must be a JSON object")
    return data


def _kind(args: argparse.Namespace) -> str:
    scope = args.scope
    kind = args.kind or SCOPE_KINDS[scope][0]
    if kind not in SCOPE_KINDS[scope]:
        raise SystemExit(f"kind {kind!r} is not allowed for {scope}")
    return kind


def _print(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    for key, value in result.items():
        if key in {"result", "pubkey"}:
            continue
        print(f"{key}: {value}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    if args.cmd == "version":
        print(f"{PRODUCT} {__version__}")
        print(f"author: {AUTHOR}")
        print(MOTTO)
        return 0

    router = build_router()

    if args.cmd in {"serve", "ui"}:
        from azieltether.serve import serve

        host = getattr(args, "host", DEFAULT_HOST)
        port = getattr(args, "port", DEFAULT_PORT)
        try:
            serve(host=host, port=port, router=router)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        return 0

    if args.cmd == "doctor":
        sites = {} if args.offline else public_site_health()
        result = router.doctor(public_sites=sites)
        _print(result, args.as_json)
        return 0 if result.get("ok") else 1

    if args.cmd == "announce":
        result = router.announce()
        _print(result, args.as_json)
        return 0

    if args.cmd == "push":
        if args.batch_file:
            batch = json.loads(Path(args.batch_file).read_text(encoding="utf-8"))
        else:
            batch = router.store.mint_batch(args.scope, _kind(args), _payload(args))
        result = router.push(batch)
        _print(result, args.as_json)
        return 0 if result.get("ok") else 1

    if args.cmd == "pull":
        result = router.pull(since=args.since, product=args.scope)
        _print(result, args.as_json)
        return 0

    if args.cmd == "reconcile":
        result = router.reconcile()
        _print(result, args.as_json)
        return 0 if result.get("ok") else 1

    if args.cmd == "batch":
        batch = router.store.mint_batch(args.scope, _kind(args), _payload(args))
        print(json.dumps(batch, indent=2, ensure_ascii=False))
        return 0

    raise SystemExit(f"unknown command {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
