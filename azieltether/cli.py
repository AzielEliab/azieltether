"""Command-line interface for AzielTether.

    azieltether
    azieltether ui
    azieltether doctor
    azieltether init
    azieltether genesis --payload TEXT
    azieltether append --payload TEXT
    azieltether status
    azieltether pulse

Advanced commands stay available. Add --json for the machine record.
Author: Aziel Eliab.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from azieltether import __version__
from azieltether.errors import AzielTetherError, ChainError, ItemError
from azieltether.human import HELP, HumanParserMixin, render, render_error, resolve_home, welcome_payload, welcome_text
from azieltether.lattice import SURFACES, bind_surfaces, mint_tip
from azieltether.protocol import (
    LIMITATION,
    dual_chain_report,
    pulse,
    reconcile,
    reheal,
    shelf_sync,
    wires_report,
)
from azieltether.queues import harvest
from azieltether.store import Store


class HumanParser(HumanParserMixin, argparse.ArgumentParser):
    """Subcommand parser: plain misuse errors, normal command help."""


class RootParser(HumanParser):
    """Top-level help stays a short command list."""

    def format_help(self) -> str:
        return (
            "usage: azieltether [--home HOME] [--json] <command> [options]\n\n"
            + HELP
            + "\noptions:\n"
            + "  -h, --help   show this help message and exit\n"
            + "  --home HOME  Node home (default ~/.azieltether).\n"
            + "  --json       Print machine-readable JSON.\n"
        )


def _take_json(argv: list[str]) -> tuple[bool, list[str]]:
    as_json = False
    kept: list[str] = []
    for arg in argv:
        if arg == "--json":
            as_json = True
        else:
            kept.append(arg)
    return as_json, kept


def _cmd(sub: argparse._SubParsersAction, name: str, description: str) -> argparse.ArgumentParser:
    return sub.add_parser(
        name,
        help=argparse.SUPPRESS,
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def _build_parser() -> RootParser:
    parser = RootParser(
        prog="azieltether",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--home", default=None, help="Node home (default ~/.azieltether).")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print machine-readable JSON.")
    sub = parser.add_subparsers(
        dest="cmd",
        metavar="command",
        required=False,
        parser_class=HumanParser,
    )

    _cmd(sub, "version", "Print the package version.")

    p_ui = _cmd(sub, "ui", "Open the local app on 127.0.0.1:8874.")
    p_ui.add_argument("--host", default="127.0.0.1", help="Loopback host (default 127.0.0.1).")
    p_ui.add_argument("--port", type=int, default=8874, help="Port (default 8874).")

    p_doc = _cmd(sub, "doctor", "Self-check. Pass/fail lines, or --json for the machine record.")
    p_doc.add_argument("--json", action="store_true", dest="as_json", help="Print doctor results as JSON.")

    _cmd(sub, "init", "Create the local node home and node id.")
    _cmd(sub, "node-id", "Print this node's id.")
    _cmd(sub, "status", "Show items, chain check, and sync mode.")

    p_gen = _cmd(sub, "genesis", 'Write the first item.\n\nExample: azieltether genesis --payload "desk closed"')
    p_gen.add_argument("--payload", required=True, help="Note to store.")
    p_gen.add_argument("--scope", default="azieltether")
    p_gen.add_argument("--kind", default="work")
    p_gen.add_argument("--timestamp", default=None)

    p_app = _cmd(sub, "append", 'Add an item.\n\nExample: azieltether append --payload "your note"')
    p_app.add_argument("--payload", required=True, help="Note to store.")
    p_app.add_argument("--scope", default="azieltether")
    p_app.add_argument("--kind", default="work")
    p_app.add_argument("--prev", default=None, dest="prev_hash", help="Override prev_hash (default: last item).")
    p_app.add_argument("--timestamp", default=None)

    p_ver = _cmd(sub, "verify", "Check hashes and previous-hash links.")
    p_ver.add_argument("--file", default=None, help="Optional JSONL path (default: node queue).")

    _cmd(sub, "show", "List items in the local queue.")

    p_pulse = _cmd(sub, "pulse", "Check the Worker. Sync with peers when it is down.")
    p_pulse.add_argument("--no-probe", action="store_true", help="Do not call the network.")
    p_pulse.add_argument("--host", default=None, help="Override central Worker host.")

    p_peer = _cmd(sub, "peer-sync", "Exchange items with a peer URL.")
    p_peer.add_argument("--peer", action="append", default=[], help="Peer base URL (repeatable).")

    p_rec = _cmd(sub, "reconcile", "Merge incoming JSON and push to the Worker if it is up.")
    p_rec.add_argument("--file", default=None, help="JSON file of items to merge.")
    p_rec.add_argument("--no-probe", action="store_true")
    p_rec.add_argument("--host", default=None)

    _cmd(sub, "dual-chain", "Report forks that share a previous hash. Both children are kept.")

    p_tip = _cmd(sub, "tip", "Mint or refresh a lattice tip.")
    p_tip.add_argument("--surface", default="worker", choices=list(SURFACES))

    p_har = _cmd(sub, "harvest", "Copy sibling tether queues (for example ~/.az-clce).")
    p_har.add_argument("--file", action="append", default=[], help="Extra JSONL queue path.")

    _cmd(sub, "wires", "Print the wires, cold-copy, reheal, and shelf law cards.")
    _cmd(sub, "survival", "Write local cold copies and print the survival card.")
    p_rh = _cmd(sub, "reheal", "Heal from this node's last good tip. Neighbor votes are refused.")
    p_rh.add_argument("--cite", default=None, help="Trusted-pull cite (must be own last good tip).")
    p_rh.add_argument("--lockset", default=None, help="Sealed lockset hash.")
    p_rh.add_argument("--file", default=None, help="JSON items for a verified trusted pull.")
    p_rh.add_argument("--votes", type=int, default=0, help="Neighbor votes (always refused).")

    p_sh = _cmd(sub, "shelf", "Cold shelf: status, seal, pull, sync, USB. SHA-256 verify.")
    p_sh.add_argument(
        "action",
        nargs="?",
        default="status",
        choices=["status", "seal", "pull", "sync", "usb", "usb-import", "attest", "slot"],
        help="status (default), seal, pull, sync, usb, usb-import, attest, slot",
    )
    p_sh.add_argument("--url", action="append", default=[], help="Shelf URL or local path (repeatable).")
    p_sh.add_argument("--sha256", default=None, dest="sha256", help="Expected SHA-256 (64 lowercase hex).")
    p_sh.add_argument("--dest", default=None, help="USB export directory.")
    p_sh.add_argument("--src", default=None, help="USB import directory.")
    p_sh.add_argument("--host", default=None, help="Override central Worker host.")
    p_sh.add_argument("--no-probe", action="store_true", help="Do not call the Worker.")
    p_sh.add_argument("--name", default=None, help="MOCK/SLOT name to refuse (ipfs, multihome_dns, …).")
    p_sh.add_argument("--zenodo-doi", default=None, help="Refused. Do not invent a DOI.")
    p_sh.add_argument(
        "--zenodo-url",
        default=None,
        help="Refused. Plane B uses Codeberg, archive.org, or GitFlic after a hash check.",
    )
    p_sh.add_argument(
        "--plane-b-url",
        default=None,
        dest="plane_b_url",
        help="Plane B shelf URL (codeberg.org, archive.org, or gitflic.ru).",
    )
    p_sh.add_argument(
        "--lockset-tip",
        default=None,
        dest="lockset_tip",
        help="Optional lockset tip cite when attesting a USB tip-pack.",
    )
    p_sh.add_argument(
        "--pack-sha256",
        default=None,
        dest="pack_sha256",
        help="Optional pack bytes SHA-256 when attesting (sha256sum -c).",
    )
    p_sh.add_argument(
        "--attest",
        action="store_true",
        dest="operator_attest",
        help="Operator attests after sha256sum -c (usb-import / attest).",
    )

    p_imp = _cmd(sub, "import", "Import a JSON export.")
    p_imp.add_argument("file")
    p_exp = _cmd(sub, "export", "Export the local chain as JSON.")
    p_exp.add_argument("file")
    return parser


def _print_json(obj: object) -> None:
    sys.stdout.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def _emit(payload: dict, *, as_json: bool, cmd: str, shelf_action: str = "status", code: int | None = None) -> int:
    if as_json:
        _print_json(payload)
    else:
        sys.stdout.write(render(cmd, payload, shelf_action=shelf_action))
    if code is not None:
        return code
    return 0 if payload.get("ok", True) else 1


def _fail(exc: BaseException, *, as_json: bool) -> int:
    message = str(exc)
    if as_json:
        _print_json({"ok": False, "error": message, "limitation": LIMITATION})
    else:
        sys.stdout.write(render_error(message))
    return 1


def _store(args: argparse.Namespace) -> Store:
    return Store(args.home)


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    as_json, raw = _take_json(raw)
    parser = _build_parser()
    args = parser.parse_args(raw)
    as_json = as_json or bool(getattr(args, "as_json", False))

    if args.cmd is None:
        home = resolve_home(args.home)
        if as_json:
            _print_json(welcome_payload(home))
        else:
            sys.stdout.write(welcome_text(home))
        return 0

    if args.cmd == "version":
        if as_json:
            _print_json({"ok": True, "version": __version__, "product": "azieltether", "author": "Aziel Eliab"})
        else:
            print(f"azieltether {__version__}")
        return 0

    if args.cmd == "doctor":
        from azieltether.doctor import run_doctor

        return run_doctor(as_json=as_json)

    if args.cmd == "ui":
        from azieltether.ui import serve

        try:
            serve(host=args.host, port=args.port, home=args.home)
        except ValueError as exc:
            return _fail(exc, as_json=as_json)
        return 0

    st = _store(args)

    try:
        if args.cmd == "init":
            node_id = st.node_id()
            return _emit(
                {"ok": True, "home": str(st.home), "node_id": node_id, "author": "Aziel Eliab"},
                as_json=as_json,
                cmd="init",
            )

        if args.cmd == "node-id":
            node_id = st.node_id()
            if as_json:
                _print_json({"ok": True, "node_id": node_id, "author": "Aziel Eliab"})
            else:
                print(node_id)
            return 0

        if args.cmd == "status":
            chain = st.chain()
            result = chain.verify()
            payload = {
                "ok": result.ok,
                "home": str(st.home),
                "node_id": st.node_id(),
                "items": result.items,
                "tip_hashes": list(result.tip_hashes),
                "dual_chain": [
                    {"prev_hash": f.prev_hash, "child_hashes": list(f.child_hashes)}
                    for f in result.dual_chain
                ],
                "mode": st.state().get("mode"),
                "limitation": LIMITATION,
                "author": "Aziel Eliab",
            }
            return _emit(payload, as_json=as_json, cmd="status", code=0 if result.ok else 1)

        if args.cmd == "genesis":
            from azieltether.chain import Chain

            chain = Chain.genesis(
                st.queue_path,
                payload=args.payload,
                node_id=st.node_id(),
                kind=args.kind,
                scope=args.scope,
                created_at=args.timestamp,
            )
            return _emit(
                {"ok": True, "action": "genesis", "item": chain[0].as_dict()},
                as_json=as_json,
                cmd="genesis",
            )

        if args.cmd == "append":
            chain = st.chain()
            if len(chain) == 0:
                raise ChainError("append refused: run genesis first")
            item = chain.append(
                args.payload,
                node_id=st.node_id(),
                kind=args.kind,
                scope=args.scope,
                prev_hash=args.prev_hash,
                created_at=args.timestamp,
            )
            return _emit(
                {"ok": True, "action": "appended", "item": item.as_dict()},
                as_json=as_json,
                cmd="append",
            )

        if args.cmd == "verify":
            from azieltether.chain import Chain

            chain = Chain.load(args.file) if args.file else st.chain()
            result = chain.verify()
            payload = {
                "ok": result.ok,
                "items": result.items,
                "errors": list(result.errors),
                "first_hash": result.first_hash,
                "last_hash": result.last_hash,
                "tip_hashes": list(result.tip_hashes),
                "dual_chain": [
                    {"prev_hash": f.prev_hash, "child_hashes": list(f.child_hashes)}
                    for f in result.dual_chain
                ],
                "author": "Aziel Eliab",
            }
            return _emit(payload, as_json=as_json, cmd="verify", code=0 if result.ok else 1)

        if args.cmd == "show":
            return _emit(
                {"items": [i.as_dict() for i in st.chain().items], "author": "Aziel Eliab"},
                as_json=as_json,
                cmd="show",
            )

        if args.cmd == "pulse":
            return _emit(pulse(st, probe=not args.no_probe, host=args.host), as_json=as_json, cmd="pulse")

        if args.cmd == "peer-sync":
            for url in args.peer:
                st.add_peer(url)
            rec = pulse(st, probe=False, harvest_siblings=False)
            rec["mode"] = "peer-sync-when-down"
            rec["peers_configured"] = st.peers()
            return _emit(rec, as_json=as_json, cmd="peer-sync")

        if args.cmd == "reconcile":
            incoming = []
            if args.file:
                doc = json.loads(Path(args.file).read_text(encoding="utf-8"))
                if isinstance(doc, list):
                    incoming = doc
                elif isinstance(doc, dict):
                    incoming = doc.get("items") or doc.get("chain") or []
            return _emit(
                reconcile(st, incoming=incoming, host=args.host, probe=not args.no_probe),
                as_json=as_json,
                cmd="reconcile",
            )

        if args.cmd == "dual-chain":
            return _emit(dual_chain_report(st), as_json=as_json, cmd="dual-chain")

        if args.cmd == "tip":
            chain = st.chain()
            tips = bind_surfaces(chain, node_id=st.node_id())
            st.write_tips(tips)
            chosen = tips["surfaces"].get(args.surface) or mint_tip(
                surface=args.surface,
                tip_hash=chain.last_hash(),
                node_id=st.node_id(),
            ).as_dict()
            return _emit(
                {"ok": True, "tip": chosen, "surfaces": list(tips["surfaces"])},
                as_json=as_json,
                cmd="tip",
            )

        if args.cmd == "harvest":
            extra = [Path(p) for p in args.file]
            return _emit(harvest(st.chain(), extra=extra), as_json=as_json, cmd="harvest")

        if args.cmd == "wires":
            return _emit(wires_report(), as_json=as_json, cmd="wires")

        if args.cmd == "survival":
            from azieltether.survival import copy_manifest, law_card

            copies = st.multiply_copies()
            return _emit(
                {
                    "ok": True,
                    "author": "Aziel Eliab",
                    "survival": law_card(),
                    "multiply": copies,
                    "manifest": copy_manifest(st.copies_dir),
                },
                as_json=as_json,
                cmd="survival",
            )

        if args.cmd == "reheal":
            incoming = []
            if args.file:
                doc = json.loads(Path(args.file).read_text(encoding="utf-8"))
                if isinstance(doc, list):
                    incoming = doc
                elif isinstance(doc, dict):
                    incoming = doc.get("items") or []
            return _emit(
                reheal(
                    st,
                    cite=args.cite,
                    lockset=args.lockset,
                    incoming=incoming,
                    votes_for=args.votes,
                ),
                as_json=as_json,
                cmd="reheal",
            )

        if args.cmd == "shelf":
            from azieltether.shelf import (
                attest_usb,
                export_usb,
                fetch_manifest,
                import_usb,
                law_card,
                load_last_shelf,
                merge_verified_items,
                plane_a_card,
                plane_b_status,
                plane_c_card,
                refuse_slot,
                seal_shelf,
            )

            action = args.action
            if action == "slot":
                rec = refuse_slot(args.name or "ipfs")
                return _emit(rec, as_json=as_json, cmd="shelf", shelf_action=action, code=0 if rec.get("ok") else 1)
            if action == "status":
                if args.plane_b_url:
                    st.set_plane_b(url=args.plane_b_url, sha256=args.sha256, verified=False)
                last = load_last_shelf(st)
                stored = st.plane_b()
                stored_url = stored.get("url") or None
                if stored_url and "zenodo" in str(stored_url).lower():
                    stored_url = None
                return _emit(
                    {
                        "ok": True,
                        "author": "Aziel Eliab",
                        "shelf": law_card(),
                        "planes": {
                            "A": plane_a_card(),
                            "B": plane_b_status(
                                doi=args.zenodo_doi,
                                url=args.plane_b_url or args.zenodo_url or stored_url,
                                sha256=args.sha256 or stored.get("sha256"),
                                verified=bool(stored.get("verified")) and not args.zenodo_doi,
                            ),
                            "C": plane_c_card(st),
                        },
                        "last": {k: v for k, v in last.items() if k != "manifest"} if last.get("ok") else last,
                        "manifest": (last.get("manifest") if last.get("ok") else None),
                    },
                    as_json=as_json,
                    cmd="shelf",
                    shelf_action="status",
                )
            if action == "seal":
                return _emit(seal_shelf(st), as_json=as_json, cmd="shelf", shelf_action="seal")
            if action == "pull":
                if not args.url:
                    return _emit(
                        {"ok": False, "error": "shelf pull needs --url", "limitation": LIMITATION},
                        as_json=as_json,
                        cmd="shelf",
                        shelf_action="pull",
                        code=1,
                    )
                for url in args.url:
                    st.add_shelf_url(url)
                rec = fetch_manifest(args.url[0], expected_sha256=args.sha256)
                if rec.get("ok") and rec.get("manifest", {}).get("items"):
                    rec["merge"] = merge_verified_items(st, rec["manifest"]["items"])
                    rec["seal"] = seal_shelf(st)
                shown = {k: v for k, v in rec.items() if k != "bytes"}
                return _emit(shown, as_json=as_json, cmd="shelf", shelf_action="pull", code=0 if rec.get("ok") else 1)
            if action == "sync":
                for url in args.url:
                    st.add_shelf_url(url)
                incoming = {}
                if args.zenodo_doi:
                    incoming["zenodo_doi"] = args.zenodo_doi
                if args.zenodo_url:
                    incoming["zenodo_url"] = args.zenodo_url
                if args.plane_b_url:
                    incoming["plane_b_url"] = args.plane_b_url
                rec = shelf_sync(
                    st,
                    urls=args.url,
                    expected_sha256=args.sha256,
                    host=args.host,
                    probe=not args.no_probe,
                    incoming=incoming or None,
                )
                return _emit(rec, as_json=as_json, cmd="shelf", shelf_action="sync", code=0 if rec.get("ok") else 1)
            if action == "usb":
                dest = args.dest or str(st.home / "usb-shelf")
                return _emit(export_usb(st, dest), as_json=as_json, cmd="shelf", shelf_action="usb")
            if action == "usb-import":
                if not args.src:
                    return _emit(
                        {"ok": False, "error": "shelf usb-import needs --src", "limitation": LIMITATION},
                        as_json=as_json,
                        cmd="shelf",
                        shelf_action="usb-import",
                        code=1,
                    )
                rec = import_usb(
                    st,
                    args.src,
                    expected_sha256=args.sha256,
                    operator_attest=bool(args.operator_attest),
                )
                return _emit(rec, as_json=as_json, cmd="shelf", shelf_action="usb-import", code=0 if rec.get("ok") else 1)
            if action == "attest":
                src = args.src or args.dest
                if not src:
                    return _emit(
                        {"ok": False, "error": "shelf attest needs --src", "limitation": LIMITATION},
                        as_json=as_json,
                        cmd="shelf",
                        shelf_action="attest",
                        code=1,
                    )
                rec = attest_usb(
                    st,
                    src,
                    expected_sha256=args.sha256,
                    pack_sha256=args.pack_sha256,
                    lockset_tip=args.lockset_tip,
                )
                return _emit(rec, as_json=as_json, cmd="shelf", shelf_action="attest", code=0 if rec.get("ok") else 1)

        if args.cmd == "import":
            from azieltether.jsonio import import_json

            return _emit(import_json(args.file, store=st), as_json=as_json, cmd="import")

        if args.cmd == "export":
            from azieltether.jsonio import export_json

            return _emit(export_json(args.file, store=st), as_json=as_json, cmd="export")
    except (AzielTetherError, ItemError, ChainError, OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail(exc, as_json=as_json)

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
