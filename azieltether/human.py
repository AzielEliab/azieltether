"""Human text for the AzielTether CLI.

Machine output stays JSON via --json. This module only formats words
a person reads. Author: Aziel Eliab.
"""

from __future__ import annotations

import json
from pathlib import Path

from azieltether import __version__
from azieltether.errors import AzielTetherError
from azieltether.store import default_home

HELP = """\
AzielTether keeps a hash-chained copy of your work on this computer
and syncs it with the central Worker when that Worker is up.

Author: Aziel Eliab

Common commands:
  ui           Open the local app
  init         Create this node's home
  genesis      Write the first item
  append       Add an item to the chain
  status       Show this node
  pulse        Check the Worker and sync
  doctor       Run a self-check
  version      Print the version

Advanced commands:
  verify       Check hashes and links
  show         List saved items
  node-id      Print this node's id
  peer-sync    Sync with a peer URL
  reconcile    Merge items and push when the Worker is up
  dual-chain   Show forks (both children are kept)
  tip          Refresh a lattice tip
  harvest      Copy sibling queues into this chain
  wires        Show the wires, survival, reheal, and shelf laws
  survival     Write local cold copies
  reheal       Heal from this node's last good tip
  shelf        Seal, pull, or check the cold shelf
  import       Import a JSON export
  export       Export the chain as JSON

Examples:
  azieltether
  azieltether ui
  azieltether genesis --payload "desk closed"
  azieltether doctor
  azieltether status --json

Add --json for machine-readable output.
Run `azieltether <command> --help` for command details.
"""

MODE_PLAIN = {
    "prefer-central": "Prefer the Worker",
    "peer-sync-when-down": "Peer sync (Worker not in use)",
    "reconcile-on-restore": "Reconcile with the Worker",
}


class HumanParserMixin:
    """Plain misuse errors: reason, then one next step."""

    def error(self, message: str) -> None:
        self.exit(2, friendly_arg_error(self.prog, message) + "\n")


def friendly_arg_error(prog: str, message: str) -> str:
    tail = (prog or "azieltether").split()[-1]
    if "invalid choice:" in message:
        choice = message.split("invalid choice:", 1)[1].strip().split()[0].strip("'\"")
        return f'Unknown command "{choice}". Try: azieltether ui   or   azieltether --help'
    if "required" in message and "--payload" in message:
        if tail == "append":
            return 'Append needs a note.\nNext: azieltether append --payload "your note"'
        return 'Genesis needs a note.\nNext: azieltether genesis --payload "desk closed"'
    if "required" in message and "file" in message:
        if tail == "import":
            return "Import needs a JSON file.\nNext: azieltether import export.json"
        if tail == "export":
            return "Export needs a file path.\nNext: azieltether export export.json"
        return f"A file path is required.\nNext: azieltether {tail} --help"
    if message.startswith("unrecognized arguments:"):
        extra = message.split(":", 1)[1].strip()
        return f'Unknown option "{extra}". Try: {prog} --help'
    if "expected one argument" in message:
        return f"{message[0].upper()}{message[1:]}.\nNext: {prog} --help"
    return f"{message}\nNext: azieltether --help"


def resolve_home(home_arg: str | None) -> Path:
    if home_arg:
        return Path(home_arg)
    return default_home()


def peek_chain(home: Path) -> tuple[int | None, bool | None]:
    """Read an existing queue without creating a node home."""
    queue = home / "queue.jsonl"
    if not queue.is_file():
        return 0, None
    try:
        from azieltether.chain import Chain

        result = Chain.load(queue).verify()
    except (OSError, json.JSONDecodeError, AzielTetherError, ValueError):
        return None, False
    return result.items, result.ok


def _next_lines(commands: list[str]) -> list[str]:
    lines = ["Next:"]
    lines.extend(f"  {cmd}" for cmd in commands)
    return lines


def welcome_text(home: Path) -> str:
    count, ok = peek_chain(home)
    lines = [
        "AzielTether keeps a hash-chained copy of your work on this computer and syncs it with the central Worker when that Worker is up.",
        "",
    ]
    if count is None:
        lines.append("The chain file on this computer could not be read.")
        lines.extend(_next_lines(["azieltether doctor"]))
    elif count == 0:
        lines.append("No items yet.")
        lines.extend(
            _next_lines(
                [
                    "azieltether ui",
                    "azieltether init",
                    'azieltether genesis --payload "desk closed"',
                    "azieltether doctor",
                ]
            )
        )
    else:
        state = "Chain checks out." if ok else "Chain needs attention."
        lines.append(f"{count} item(s) on this node. {state}")
        lines.extend(_next_lines(["azieltether ui", "azieltether status", "azieltether pulse"]))
    lines.extend(["", "Author: Aziel Eliab"])
    return "\n".join(lines) + "\n"


def welcome_payload(home: Path) -> dict[str, object]:
    count, ok = peek_chain(home)
    if count is None:
        nxt = ["azieltether doctor"]
    elif count == 0:
        nxt = ["azieltether ui", "azieltether init", "azieltether doctor"]
    else:
        nxt = ["azieltether ui", "azieltether status", "azieltether pulse"]
    readable = count is not None
    return {
        "ok": readable and ok is not False,
        "product": "azieltether",
        "author": "Aziel Eliab",
        "version": __version__,
        "home": str(home),
        "items": count if count is not None else 0,
        "chain_ok": ok,
        "readable": readable,
        "next": nxt,
    }


def plain_reason(message: str) -> str:
    known = {
        "append refused: run genesis first": "Append needs a first item.",
        "genesis refused: chain already exists (append only)": "This chain already started. Add a note instead of starting again.",
        "payload is required": "A note is required.",
        "JSON object required": "That file needs to be a JSON object.",
        "shelf pull needs --url": "Shelf pull needs a URL.",
        "shelf usb-import needs --src": "USB import needs a folder.",
        "shelf attest needs --src": "Attest needs the USB folder.",
    }
    if message in known:
        return known[message]
    if message.startswith("kind must be"):
        return "That kind is not one this chain accepts."
    if message.startswith("scope must be"):
        return "That scope is not one this chain accepts."
    if "must be 64 lowercase hex" in message:
        return "That value needs to be 64 lowercase hex characters."
    if "Expecting value" in message or "Invalid \\escape" in message or message.startswith("Expecting"):
        return "That file is not valid JSON."
    return message


def next_step_for(message: str) -> str:
    if "genesis first" in message or message == "payload is required":
        return 'azieltether genesis --payload "desk closed"'
    if "chain already exists" in message:
        return 'azieltether append --payload "your note"'
    if "kind must be" in message or "scope must be" in message:
        return "azieltether genesis --help"
    if "64 lowercase hex" in message:
        return "azieltether --help"
    if "shelf pull" in message:
        return "azieltether shelf pull --url <url>"
    if "usb-import" in message:
        return "azieltether shelf usb-import --src <folder>"
    if "attest needs" in message or message.startswith("shelf attest"):
        return "azieltether shelf attest --src <folder>"
    if "JSON" in message or "Expecting" in message:
        return "azieltether --help"
    return "azieltether --help"


def render_error(message: str) -> str:
    return f"{plain_reason(message)}\nNext: {next_step_for(message)}\n"


def _mode_line(mode: object) -> str:
    if not isinstance(mode, str) or not mode:
        return "Sync: not set yet"
    return "Sync: " + MODE_PLAIN.get(mode, mode)


def _worker_line(central: object) -> str:
    if not isinstance(central, dict):
        return "Worker: not checked"
    if central.get("prefer_central"):
        return "Worker: up"
    reason = str(central.get("reason") or "")
    if reason == "offline_forced":
        return "Worker: not checked (offline is forced)"
    if reason == "not_probed":
        return "Worker: not checked"
    if reason == "network" or central.get("error"):
        return "Worker: not reached"
    return "Worker: not up"


def _hash_line(item: object) -> str:
    if isinstance(item, dict) and item.get("hash"):
        return f"Hash: {item['hash']}"
    return "Hash: (missing)"


def _finish(lines: list[str], nxt: str) -> str:
    lines.extend(["", f"Next: {nxt}"])
    return "\n".join(lines) + "\n"


def _refusal(payload: dict[str, object], nxt: str) -> str:
    note = payload.get("note") or payload.get("error") or "Refused."
    lines = [str(note)]
    code = payload.get("code")
    if code:
        lines.append(f"Code: {code}")
    return _finish(lines, nxt)


def render_show(payload: dict[str, object]) -> str:
    items = payload.get("items")
    rows = items if isinstance(items, list) else []
    if not rows:
        return _finish(["No items yet."], 'azieltether genesis --payload "desk closed"')
    lines = [f"{len(rows)} item(s)", ""]
    for index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            lines.append(f"{index}. (unreadable item)")
            continue
        text = str(item.get("payload") or item.get("report_hash") or "")
        lines.append(f"{index}. {text}")
        if item.get("hash"):
            lines.append(f"   hash {item['hash']}")
    return _finish(lines, "azieltether ui")


def render_shelf(payload: dict[str, object], action: str) -> str:
    if payload.get("ok") is False:
        nxt = "azieltether shelf --help"
        if action == "pull":
            nxt = "azieltether shelf pull --url <url>"
        elif action in {"usb-import", "attest"}:
            nxt = f"azieltether shelf {action} --src <folder>"
        return _refusal(payload, nxt)
    if action == "status" and isinstance(payload.get("planes"), dict):
        planes = payload["planes"]
        a = planes.get("A") if isinstance(planes.get("A"), dict) else {}
        b = planes.get("B") if isinstance(planes.get("B"), dict) else {}
        c = planes.get("C") if isinstance(planes.get("C"), dict) else {}
        spec = ""
        shelf = payload.get("shelf")
        if isinstance(shelf, dict) and shelf.get("spec"):
            spec = str(shelf["spec"])
        lines = ["Cold shelf"]
        if spec:
            lines.append(f"Spec: {spec}")
        lines.append("Plane A: recorded for when the Worker is up." if a.get("live") else "Plane A: not marked live.")
        if b.get("live"):
            lines.append("Plane B: hash-verified.")
        else:
            lines.append("Plane B: waiting for a hash check.")
        if c.get("usb_tip_pack_live"):
            lines.append("USB tip-pack: attested.")
        else:
            lines.append("USB tip-pack: not attested yet.")
        return _finish(lines, "azieltether shelf seal")
    if action == "seal":
        lines = ["Shelf sealed."]
        if payload.get("code"):
            lines.append(f"Code: {payload['code']}")
        return _finish(lines, "azieltether shelf")
    if action == "usb":
        lines = ["USB tip-pack written."]
        if payload.get("dest"):
            lines.append(f"Folder: {payload['dest']}")
        return _finish(lines, "azieltether shelf attest --src <folder>")
    if action == "attest" and payload.get("ok"):
        lines = ["USB tip-pack attested."]
        if payload.get("code"):
            lines.append(f"Code: {payload['code']}")
        if "usb_tip_pack_live" in payload:
            lines.append("USB tip-pack live: " + ("yes" if payload.get("usb_tip_pack_live") else "no"))
        return _finish(lines, "azieltether shelf")
    if action == "pull" and payload.get("ok"):
        return _finish(["Shelf pull checked."], "azieltether shelf")
    if action == "sync" and payload.get("ok"):
        return _finish(["Shelf sync finished."], "azieltether status")
    if action == "usb-import" and payload.get("ok"):
        return _finish(["USB tip-pack imported."], "azieltether shelf")
    lines = ["Done."]
    if payload.get("code"):
        lines.append(f"Code: {payload['code']}")
    return _finish(lines, "azieltether shelf")


def render(cmd: str, payload: dict[str, object], *, shelf_action: str = "status") -> str:
    if cmd == "init":
        return _finish(
            [
                "Node home is ready.",
                f"Home: {payload.get('home')}",
                f"Node id: {payload.get('node_id')}",
            ],
            'azieltether genesis --payload "desk closed"',
        )
    if cmd == "status":
        ok = bool(payload.get("ok"))
        lines = [
            f"Items: {payload.get('items')}",
            "Chain: checks out" if ok else "Chain: needs attention",
            _mode_line(payload.get("mode")),
            f"Home: {payload.get('home')}",
            f"Node id: {payload.get('node_id')}",
        ]
        tips = payload.get("tip_hashes")
        if isinstance(tips, list):
            lines.append(f"Tips: {len(tips)}")
        forks = payload.get("dual_chain")
        if isinstance(forks, list) and forks:
            lines.append(f"Forks: {len(forks)}")
        return _finish(lines, "azieltether ui" if ok else "azieltether doctor")
    if cmd == "genesis":
        item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
        return _finish(["First item written.", _hash_line(item)], 'azieltether append --payload "your note"')
    if cmd == "append":
        item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
        return _finish(["Item added.", _hash_line(item)], "azieltether ui")
    if cmd == "verify":
        if payload.get("ok"):
            lines = ["Chain checks out.", f"Items: {payload.get('items')}"]
            return _finish(lines, "azieltether status")
        lines = ["Chain check failed."]
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            lines.extend(f"- {err}" for err in errors)
        elif payload.get("error"):
            lines.append(str(payload["error"]))
        return _finish(lines, "azieltether doctor")
    if cmd == "show":
        return render_show(payload)
    if cmd == "pulse":
        lines = [
            "Pulse finished.",
            _mode_line(payload.get("mode")),
            _worker_line(payload.get("central")),
            f"Items: {payload.get('items')}",
            f"Unpublished: {payload.get('unpublished')}",
        ]
        return _finish(lines, "azieltether ui")
    if cmd == "peer-sync":
        peers = payload.get("peers_configured")
        count = len(peers) if isinstance(peers, list) else 0
        lines = ["Peer list updated.", f"Peers: {count}", _mode_line(payload.get("mode"))]
        return _finish(lines, "azieltether reconcile")
    if cmd == "reconcile":
        pushed = payload.get("pushed")
        count = len(pushed) if isinstance(pushed, list) else 0
        lines = ["Reconcile finished.", _mode_line(payload.get("mode")), _worker_line(payload.get("central")), f"Pushed: {count}"]
        return _finish(lines, "azieltether status")
    if cmd == "dual-chain":
        forks = payload.get("forks")
        count = len(forks) if isinstance(forks, list) else 0
        lines = [
            f"Items: {payload.get('items')}",
            f"Forks: {count}",
            "Both children of the same previous hash are kept.",
        ]
        return _finish(lines, "azieltether show")
    if cmd == "tip":
        tip = payload.get("tip") if isinstance(payload.get("tip"), dict) else {}
        lines = ["Tip refreshed."]
        if tip.get("surface"):
            lines.append(f"Surface: {tip['surface']}")
        if tip.get("hash"):
            lines.append(f"Hash: {tip['hash']}")
        return _finish(lines, "azieltether status")
    if cmd == "harvest":
        lines = [
            "Harvest finished.",
            f"Added: {payload.get('added', 0)}",
            f"Skipped: {payload.get('skipped', 0)}",
        ]
        sources = payload.get("sources")
        if isinstance(sources, list):
            lines.append(f"Sources: {len(sources)}")
        return _finish(lines, "azieltether show")
    if cmd == "wires":
        lines = ["Laws on this node"]
        for key, label in (
            ("wires", "Wires"),
            ("survival", "Cold copies"),
            ("reheal", "Reheal"),
            ("shelf", "Shelf"),
        ):
            card = payload.get(key)
            spec = card.get("spec") if isinstance(card, dict) else None
            if spec:
                lines.append(f"{label}: {spec}")
        return _finish(lines, "azieltether wires --json")
    if cmd == "survival":
        multiply = payload.get("multiply") if isinstance(payload.get("multiply"), dict) else {}
        lines = ["Cold copies written."]
        if "count" in multiply:
            lines.append(f"Copies: {multiply.get('count')}")
        return _finish(lines, "azieltether shelf")
    if cmd == "reheal":
        if payload.get("ok") is False:
            return _refusal(payload, "azieltether reheal --help")
        verdict = payload.get("reheal") if isinstance(payload.get("reheal"), dict) else {}
        lines = ["Reheal finished."]
        if verdict.get("code"):
            lines.append(f"Code: {verdict['code']}")
        if verdict.get("wait"):
            lines.append(f"Wait: {verdict['wait']}")
        return _finish(lines, "azieltether status")
    if cmd == "shelf":
        return render_shelf(payload, shelf_action)
    if cmd == "import":
        merge = payload.get("merge") if isinstance(payload.get("merge"), dict) else {}
        lines = ["Imported.", f"File: {payload.get('imported')}"]
        if "added" in merge:
            lines.append(f"Added: {merge.get('added')}")
        return _finish(lines, "azieltether show")
    if cmd == "export":
        return _finish(
            ["Exported.", f"File: {payload.get('exported')}", f"Items: {payload.get('items')}"],
            "azieltether show",
        )
    if payload.get("ok") is False:
        return _refusal(payload, "azieltether --help")
    return _finish(["Done.", "Full record: add --json"], "azieltether --help")
