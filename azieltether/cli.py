"""Command-line interface for AzielTether.

    azieltether version
    azieltether ui
    azieltether doctor
    azieltether init
    azieltether genesis --payload TEXT
    azieltether append --payload TEXT
    azieltether verify
    azieltether show
    azieltether pulse
    azieltether peer-sync [--peer URL]
    azieltether reconcile
    azieltether dual-chain
    azieltether tip [--surface worker]
    azieltether harvest
    azieltether status
    azieltether node-id

Prefer central. Peer when down. Reconcile on restore.
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
from azieltether.lattice import SURFACES, bind_surfaces, mint_tip
from azieltether.protocol import LIMITATION, dual_chain_report, pulse, reconcile
from azieltether.queues import harvest
from azieltether.store import Store


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="azieltether",
        description=(
            "AzielTether — central×decentral node-mesh software tether "
            "(Aziel Eliab). Prefer the Worker when up. Peer-sync when down. "
            "Reconcile on restore. Dual-chain on same-hash conflict. "
            "Local UI: `azieltether ui` at http://127.0.0.1:8874."
        ),
        epilog=LIMITATION,
    )
    parser.add_argument("--home", default=None, help="Node home (default ~/.azieltether).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="Print package version.")

    p_ui = sub.add_parser("ui", help="Serve the local UI on 127.0.0.1:8874 (loopback only).")
    p_ui.add_argument("--host", default="127.0.0.1", help="Loopback host (default 127.0.0.1).")
    p_ui.add_argument("--port", type=int, default=8874, help="Port (default 8874).")

    p_doc = sub.add_parser("doctor", help="Self-check: hash, dual-chain, identity, import.")
    p_doc.add_argument("--json", action="store_true", dest="as_json", help="Print doctor results as JSON.")

    sub.add_parser("init", help="Create the local node home and node_id.")
    sub.add_parser("node-id", help="Print this node's id.")
    sub.add_parser("status", help="Print mode, tips, and chain length.")

    p_gen = sub.add_parser("genesis", help="Write the first item (prev_hash = 64 zeros).")
    p_gen.add_argument("--payload", required=True, help="Work / evidence body.")
    p_gen.add_argument("--scope", default="azieltether")
    p_gen.add_argument("--kind", default="work")
    p_gen.add_argument("--timestamp", default=None)

    p_app = sub.add_parser("append", help="Append an item to the local DAG.")
    p_app.add_argument("--payload", required=True, help="Work / evidence body.")
    p_app.add_argument("--scope", default="azieltether")
    p_app.add_argument("--kind", default="work")
    p_app.add_argument("--prev", default=None, dest="prev_hash", help="Override prev_hash (default: last item).")
    p_app.add_argument("--timestamp", default=None)

    p_ver = sub.add_parser("verify", help="Walk hashes and prev links. Dual-chain is allowed.")
    p_ver.add_argument("--file", default=None, help="Optional JSONL path (default: node queue).")

    sub.add_parser("show", help="Print items in the local queue.")

    p_pulse = sub.add_parser("pulse", help="Prefer-central probe; peer-sync when down.")
    p_pulse.add_argument("--no-probe", action="store_true", help="Do not call the network.")
    p_pulse.add_argument("--host", default=None, help="Override central Worker host.")

    p_peer = sub.add_parser("peer-sync", help="Exchange items with a peer URL.")
    p_peer.add_argument("--peer", action="append", default=[], help="Peer base URL (repeatable).")

    p_rec = sub.add_parser("reconcile", help="Merge incoming JSON and push to central if up.")
    p_rec.add_argument("--file", default=None, help="JSON file of items to merge.")
    p_rec.add_argument("--no-probe", action="store_true")
    p_rec.add_argument("--host", default=None)

    sub.add_parser("dual-chain", help="Report same-prev_hash forks. No winner.")

    p_tip = sub.add_parser("tip", help="Mint or refresh a lattice tip.")
    p_tip.add_argument("--surface", default="worker", choices=list(SURFACES))

    p_har = sub.add_parser("harvest", help="Copy sibling tether queues (e.g. ~/.az-clce).")
    p_har.add_argument("--file", action="append", default=[], help="Extra JSONL queue path.")

    p_imp = sub.add_parser("import", help="Import a JSON export.")
    p_imp.add_argument("file")
    p_exp = sub.add_parser("export", help="Export the local DAG as JSON.")
    p_exp.add_argument("file")
    return parser


def _print_json(obj: object) -> None:
    sys.stdout.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def _store(args: argparse.Namespace) -> Store:
    return Store(args.home)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.cmd == "version":
        print(f"azieltether {__version__}")
        return 0

    if args.cmd == "doctor":
        from azieltether.doctor import run_doctor

        return run_doctor(as_json=args.as_json)

    if args.cmd == "ui":
        from azieltether.ui import serve

        serve(host=args.host, port=args.port, home=args.home)
        return 0

    st = _store(args)

    try:
        if args.cmd == "init":
            node_id = st.node_id()
            _print_json({"ok": True, "home": str(st.home), "node_id": node_id, "author": "Aziel Eliab"})
            return 0

        if args.cmd == "node-id":
            print(st.node_id())
            return 0

        if args.cmd == "status":
            chain = st.chain()
            result = chain.verify()
            _print_json(
                {
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
            )
            return 0 if result.ok else 1

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
            _print_json({"ok": True, "action": "genesis", "item": chain[0].as_dict()})
            return 0

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
            _print_json({"ok": True, "action": "appended", "item": item.as_dict()})
            return 0

        if args.cmd == "verify":
            from azieltether.chain import Chain

            chain = Chain.load(args.file) if args.file else st.chain()
            result = chain.verify()
            _print_json(
                {
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
            )
            return 0 if result.ok else 1

        if args.cmd == "show":
            _print_json({"items": [i.as_dict() for i in st.chain().items], "author": "Aziel Eliab"})
            return 0

        if args.cmd == "pulse":
            _print_json(pulse(st, probe=not args.no_probe, host=args.host))
            return 0

        if args.cmd == "peer-sync":
            for url in args.peer:
                st.add_peer(url)
            rec = pulse(st, probe=False, harvest_siblings=False)
            rec["mode"] = "peer-sync-when-down"
            rec["peers_configured"] = st.peers()
            _print_json(rec)
            return 0

        if args.cmd == "reconcile":
            incoming = []
            if args.file:
                doc = json.loads(Path(args.file).read_text(encoding="utf-8"))
                if isinstance(doc, list):
                    incoming = doc
                elif isinstance(doc, dict):
                    incoming = doc.get("items") or doc.get("chain") or []
            _print_json(reconcile(st, incoming=incoming, host=args.host, probe=not args.no_probe))
            return 0

        if args.cmd == "dual-chain":
            _print_json(dual_chain_report(st))
            return 0

        if args.cmd == "tip":
            chain = st.chain()
            if args.surface == "worker" or True:
                tips = bind_surfaces(chain, node_id=st.node_id())
                st.write_tips(tips)
                chosen = tips["surfaces"].get(args.surface) or mint_tip(
                    surface=args.surface,
                    tip_hash=chain.last_hash(),
                    node_id=st.node_id(),
                ).as_dict()
            _print_json({"ok": True, "tip": chosen, "surfaces": list(tips["surfaces"])})
            return 0

        if args.cmd == "harvest":
            extra = [Path(p) for p in args.file]
            _print_json(harvest(st.chain(), extra=extra))
            return 0

        if args.cmd == "import":
            from azieltether.jsonio import import_json

            _print_json(import_json(args.file, store=st))
            return 0

        if args.cmd == "export":
            from azieltether.jsonio import export_json

            _print_json(export_json(args.file, store=st))
            return 0
    except (AzielTetherError, ItemError, ChainError, OSError, ValueError, json.JSONDecodeError) as exc:
        _print_json({"ok": False, "error": str(exc), "limitation": LIMITATION})
        return 1

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
