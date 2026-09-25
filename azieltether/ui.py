"""Localhost UI for AzielTether. Binds 127.0.0.1 only.

Genesis / append / pulse / peer / reconcile / dual-chain / tips.
Import JSON file and Export JSON. No CDN, no telemetry.

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from azieltether import __version__
from azieltether.chain import Chain
from azieltether.errors import AzielTetherError
from azieltether.jsonio import import_json
from azieltether.lattice import bind_surfaces
from azieltether.protocol import (
    LIMITATION,
    accept_peer,
    accept_tick_plane,
    dual_chain_report,
    serve_payload,
    pulse,
    reconcile,
    reheal,
    shelf_sync,
)
from azieltether.store import Store

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8874
LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
MAX_BODY = 2 * 1024 * 1024

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AzielTether</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f7f4ec; --panel: #fffdf8; --ink: #1a1814; --muted: #4e493f;
    --line: #e4dcc8; --gold: #c9a227; --gold-ink: #6e5810; --field: #fffdf8;
    --bad: #9b2c2c; --pass: #146b3a;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #12110e; --panel: #1e1b16; --ink: #f4efe6; --muted: #c8c0b2;
      --line: #3d372c; --gold: #c9a227; --gold-ink: #e0c36a; --field: #16140f;
      --bad: #f0b4ae; --pass: #9ddec0;
    }
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; background: var(--bg); color: var(--ink);
    font-family: system-ui, "Segoe UI", sans-serif; line-height: 1.5;
  }
  body { max-width: 40rem; margin: 0 auto; padding: 1.75rem 1.25rem 3.5rem; }
  :focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
  .tag { font-size: 0.82rem; color: var(--muted); margin: 0; }
  h1 { font-size: 1.85rem; font-weight: 650; letter-spacing: -0.02em; margin: 0.2rem 0 0.4rem; }
  h2 { font-size: 1.05rem; font-weight: 650; margin: 0 0 0.35rem; }
  .motto { color: var(--gold-ink); margin: 0.35rem 0 0; }
  .lede { color: var(--muted); margin: 0.85rem 0 1.25rem; max-width: 38rem; }
  .card, details.panel {
    border: 1px solid var(--line); border-radius: 12px; background: var(--panel);
    padding: 1.1rem 1.15rem 1.2rem; margin: 0 0 1rem;
  }
  details.panel > summary {
    cursor: pointer; font-weight: 650; list-style: none;
  }
  details.panel > summary::-webkit-details-marker { display: none; }
  details.panel[open] > summary { margin-bottom: 0.8rem; }
  label { display: block; font-size: 0.92rem; margin: 0.85rem 0 0.35rem; }
  textarea, input[type="text"] {
    width: 100%; max-width: 100%; padding: 0.65rem 0.7rem; border: 1px solid var(--line);
    border-radius: 8px; background: var(--field); color: var(--ink); font: inherit;
  }
  .actions { display: flex; gap: 0.65rem; flex-wrap: wrap; margin: 1rem 0 0; }
  button, .filebtn {
    font: inherit; font-size: 0.95rem; min-height: 2.75rem;
    padding: 0.55rem 1rem; border-radius: 8px;
    border: 1px solid #1a1814; background: var(--gold); color: #1a1814;
    cursor: pointer; font-weight: 650;
  }
  button.ghost, .filebtn {
    background: transparent; color: var(--ink); border-color: var(--line);
  }
  .banner {
    margin: 0 0 1rem; padding: 0.85rem 1rem; border-radius: 10px;
    border: 1px solid var(--line); background: var(--panel); color: var(--ink);
  }
  .banner.ok { color: var(--pass); border-color: var(--pass); }
  .banner.bad { color: var(--bad); border-color: var(--bad); }
  .item {
    border: 1px solid var(--line); border-radius: 10px; background: var(--panel);
    padding: 0.85rem 1rem; margin: 0 0 0.65rem;
  }
  .hash { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.78rem; word-break: break-word; color: var(--muted); }
  .empty { color: var(--muted); margin: 0.2rem 0 1rem; }
  footer { margin-top: 1.5rem; color: var(--muted); font-size: 0.9rem; }
  pre { white-space: pre-wrap; word-break: break-word; margin: 0.5rem 0 0; }
  input[type="file"] { display: none; }
  @media (max-width: 420px) {
    body { padding: 1rem 0.9rem 2.5rem; }
    h1 { font-size: 1.55rem; }
    .actions { flex-direction: column; align-items: stretch; }
    button, .filebtn { width: 100%; text-align: center; }
  }
</style>
</head>
<body>
  <header>
    <p class="tag">AzielTether · __VERSION__ · this computer · 127.0.0.1</p>
    <h1>AzielTether</h1>
    <p class="lede">Keeps a hash-chained copy of your work on this computer and syncs it with the central Worker when that Worker is up.</p>
    <p class="motto">Prefer central. Peer when down. Reconcile on restore.</p>
  </header>

  <p class="banner" id="status" role="status">Loading…</p>

  <section class="card">
    <h2>Your chain</h2>
    <p class="lede" id="lead">Write one note. That starts the chain on this computer.</p>
    <label for="payload">Note</label>
    <textarea id="payload" rows="3" placeholder="desk closed"></textarea>
    <div class="actions">
      <button type="button" id="primary">Start chain</button>
      <button type="button" class="ghost" id="doctor">Doctor</button>
    </div>
  </section>

  <h2>Items</h2>
  <p class="empty" id="empty">No items yet.</p>
  <div id="items"></div>

  <details class="panel" id="advanced">
    <summary>Advanced</summary>
    <div class="actions">
      <button type="button" class="ghost" id="verify">Check chain</button>
      <button type="button" class="ghost" id="pulse">Pulse</button>
      <button type="button" class="ghost" id="reconcile">Reconcile</button>
      <button type="button" class="ghost" id="dual">Dual-chain</button>
      <button type="button" class="ghost" id="tips">Refresh tips</button>
      <button type="button" class="ghost" id="shelf-seal">Seal shelf</button>
      <button type="button" class="ghost" id="shelf-sync">Shelf sync</button>
      <label class="filebtn">Import JSON<input type="file" id="import-json" accept=".json,application/json"></label>
      <button type="button" class="ghost" id="export">Export JSON</button>
    </div>
    <label for="peer">Peer URL, when the Worker is down</label>
    <input id="peer" type="text" placeholder="http://127.0.0.1:8875">
    <div class="actions">
      <button type="button" class="ghost" id="peer-add">Add peer and sync</button>
    </div>
    <label for="shelf-url">Cold-shelf URL (Codeberg, archive.org, GitFlic, or a local path)</label>
    <input id="shelf-url" type="text" placeholder="https://codeberg.org/…">
    <label for="shelf-sha">Expected SHA-256</label>
    <input id="shelf-sha" type="text" placeholder="64 lowercase hex" autocomplete="off">
    <div class="actions">
      <button type="button" class="ghost" id="shelf-pull">Pull and check</button>
    </div>
    <label for="shelf-usb">USB folder, after sha256sum -c</label>
    <input id="shelf-usb" type="text" placeholder="/media/usb/aziel-shelf">
    <div class="actions">
      <button type="button" class="ghost" id="shelf-attest">Attest USB tip-pack</button>
    </div>
    <details>
      <summary>Last response</summary>
      <pre id="out" class="hash"></pre>
    </details>
  </details>

  <details class="panel" id="notes">
    <summary>Notes</summary>
    <p>This page listens on 127.0.0.1 only. Public boards stay mesh-free. The tether runs in this downloaded software.</p>
    <p>SPLIT THE WIRES: a tick carries presence and the tip only. The payload is a pull on the separate gate. COLD-COPY SURVIVAL: sealed copies stay on this computer. REHEAL uses this node's last good tip, or phoenix-WAIT. COLD-SHELF TETHER: prefer the Worker when it is up, keep the last local shelf when it is down, and reconcile by hash when it returns. Plane B waits for a hash check on Codeberg, archive.org, or GitFlic. A USB tip-pack is attested with sha256sum -c.</p>
    <p>Both children of the same previous hash are kept.</p>
  </details>

  <footer>
    <p>Author Aziel Eliab. Apache-2.0. Forks welcome.</p>
  </footer>
<script>
(function () {
  const $ = (id) => document.getElementById(id);
  const out = $("out");
  const status = $("status");
  let hasChain = false;
  function banner(text, ok) {
    status.textContent = text;
    status.className = "banner " + (ok ? "ok" : "bad");
  }
  function plainError(err) {
    if (err === "payload is required") return "Write a note first.";
    if (err === "run genesis first") return "Start the chain before adding another note.";
    if (err === "attest needs src") return "Enter the USB folder, then attest.";
    return err;
  }
  function syncPrimary() {
    const btn = $("primary");
    const lead = $("lead");
    if (hasChain) {
      btn.textContent = "Add note";
      lead.textContent = "Add a note to the chain on this computer.";
    } else {
      btn.textContent = "Start chain";
      lead.textContent = "Write one note. That starts the chain on this computer.";
    }
  }
  function modeLine(mode) {
    if (mode === "prefer-central") return "Prefer the Worker.";
    if (mode === "peer-sync-when-down") return "Peer sync. The Worker is not in use.";
    if (mode === "reconcile-on-restore") return "Reconciled with the Worker.";
    return "";
  }
  async function get(path) {
    const r = await fetch(path, { headers: { "Accept": "application/json" } });
    return r.json();
  }
  async function post(path, body) {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    const data = await r.json();
    data._httpOk = r.ok;
    return data;
  }
  function draw(data) {
    if (out) out.textContent = JSON.stringify(data, null, 2);
    const hasItems = Array.isArray(data.items);
    if (hasItems) {
      hasChain = data.items.length > 0;
      syncPrimary();
      const box = $("items");
      box.innerHTML = "";
      data.items.forEach((it, i) => {
        const d = document.createElement("div");
        d.className = "item";
        const payload = document.createElement("div");
        payload.textContent = it.payload || it.report_hash || "";
        const meta = document.createElement("div");
        meta.className = "hash";
        meta.textContent = "#" + (i + 1) + "  " + (it.created_at || "");
        const prev = document.createElement("div");
        prev.className = "hash";
        prev.textContent = "prev " + (it.prev_hash || "");
        const hash = document.createElement("div");
        hash.className = "hash";
        hash.textContent = "hash " + (it.hash || "");
        d.appendChild(meta);
        d.appendChild(payload);
        d.appendChild(prev);
        d.appendChild(hash);
        box.appendChild(d);
      });
      $("empty").hidden = hasChain;
    }
    if (data.error) {
      banner(plainError(String(data.error)), false);
      return;
    }
    if (data.code) {
      const known = {
        "SHELF-SEAL": "Shelf sealed on this computer.",
        "SHELF-OPERATOR-ATTEST": "USB tip-pack attested.",
        "CNS-OPERATOR-ATTEST": "USB tip-pack is not attested yet."
      };
      const line = known[data.code] || (data.note ? String(data.note) : ("Finished. Code " + data.code + "."));
      banner(line, data.ok !== false && data._httpOk !== false);
      return;
    }
    const count = (data.verify && typeof data.verify.items === "number") ? data.verify.items : (hasItems ? data.items.length : null);
    const extra = modeLine(data.mode);
    if (data.message && count === 0) {
      banner("No items yet. Write a note, then start the chain.", true);
      return;
    }
    if (data.verify && data.verify.ok === false) {
      banner("Chain needs attention." + (extra ? " " + extra : ""), false);
      return;
    }
    if (count !== null) {
      const head = count === 0 ? "No items yet." : "Chain checks out. " + count + " item" + (count === 1 ? "" : "s") + ".";
      banner((extra ? extra + " " : "") + head, true);
      return;
    }
    if (data.message) banner(String(data.message), data.ok !== false && data._httpOk !== false);
    else if (data.note) banner(String(data.note), data.ok !== false);
    else banner(data.ok === false ? "That did not finish." : "Done.", data.ok !== false);
  }
  async function refresh() { draw(await get("/api/status")); }
  $("primary").onclick = async () => {
    const note = $("payload").value;
    if (!String(note).trim()) {
      banner("Write a note first.", false);
      $("payload").focus();
      return;
    }
    const path = hasChain ? "/api/append" : "/api/genesis";
    const data = await post(path, { payload: note });
    if (!data.error) $("payload").value = "";
    draw(data);
  };
  $("verify").onclick = async () => draw(await post("/api/verify", {}));
  $("pulse").onclick = async () => draw(await post("/api/pulse", {}));
  $("reconcile").onclick = async () => draw(await post("/api/reconcile", {}));
  $("dual").onclick = async () => {
    const data = await get("/api/dual-chain");
    if (out) out.textContent = JSON.stringify(data, null, 2);
    const n = Array.isArray(data.forks) ? data.forks.length : 0;
    banner(n === 0 ? "No forks. Both children of the same previous hash are kept when one appears." : n + " fork(s). Both children are kept.", true);
  };
  $("tips").onclick = async () => draw(await post("/api/tip", {}));
  $("doctor").onclick = async () => {
    const data = await get("/api/doctor");
    banner("Run azieltether doctor in a terminal for the full self-check.", !!data.ok);
  };
  $("shelf-seal").onclick = async () => draw(await post("/api/shelf-seal", {}));
  $("shelf-sync").onclick = async () => draw(await post("/api/shelf-sync", {
    url: $("shelf-url").value,
    sha256: $("shelf-sha").value,
    plane_b_url: $("shelf-url").value,
  }));
  $("shelf-pull").onclick = async () => draw(await post("/api/shelf-pull", {
    url: $("shelf-url").value,
    sha256: $("shelf-sha").value,
    plane_b_url: $("shelf-url").value,
  }));
  $("shelf-attest").onclick = async () => draw(await post("/api/shelf-attest", {
    src: $("shelf-usb").value,
    sha256: $("shelf-sha").value,
  }));
  $("peer-add").onclick = async () => draw(await post("/api/peer-sync", { peer: $("peer").value }));
  $("import-json").onchange = async () => {
    const f = $("import-json").files && $("import-json").files[0];
    if (!f) return;
    const text = await f.text();
    draw(await post("/api/import", { text: text }));
  };
  $("export").onclick = async () => {
    const data = await get("/api/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "azieltether.json";
    a.click();
    URL.revokeObjectURL(a.href);
    banner("Export downloaded.", true);
  };
  refresh().catch((e) => banner(String(e), false));
})();
</script>
</body>
</html>
""".replace("__VERSION__", __version__)


def _wants_json(accept: str | None) -> bool:
    """HTML unless the caller asks for JSON and does not ask for HTML."""
    header = (accept or "").lower()
    if "text/html" in header:
        return False
    return "application/json" in header


class TetherServer(ThreadingHTTPServer):
    store: Store


def _snapshot(store: Store, message: str = "") -> dict[str, Any]:
    chain = store.chain()
    result = chain.verify()
    return {
        "ok": result.ok,
        "message": message,
        "product": "azieltether",
        "author": "Aziel Eliab",
        "version": __version__,
        "node_id": store.node_id(),
        "mode": store.state().get("mode"),
        "items": [item.as_dict() for item in chain.items],
        "verify": {
            "ok": result.ok,
            "items": result.items,
            "errors": list(result.errors),
            "first_hash": result.first_hash,
            "last_hash": result.last_hash,
            "tip_hashes": list(result.tip_hashes),
        },
        "dual_chain": [
            {"prev_hash": f.prev_hash, "child_hashes": list(f.child_hashes)}
            for f in result.dual_chain
        ],
        "tips": store.tips(),
        "limitation": LIMITATION,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _store(self) -> Store:
        return self.server.store  # type: ignore[attr-defined]

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: Any) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("payload too large")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
        return data

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            if _wants_json(self.headers.get("Accept")):
                self._json(200, _snapshot(self._store(), "Local app."))
                return
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/health":
            self._json(
                200,
                {
                    "ok": True,
                    "bind_host": DEFAULT_HOST,
                    "name": "AzielTether",
                    "author": "Aziel Eliab",
                    "version": __version__,
                    "role": "central×decentral software tether",
                    "limitation": LIMITATION,
                },
            )
            return
        if path == "/api/status":
            self._json(200, _snapshot(self._store(), "Local DAG."))
            return
        if path == "/api/dual-chain":
            self._json(200, dual_chain_report(self._store()))
            return
        if path == "/api/doctor":
            from azieltether.doctor import run_doctor

            # doctor prints; return snapshot instead of hijacking stdout
            self._json(200, {"ok": True, "hint": "run azieltether doctor", "author": "Aziel Eliab"})
            return
        if path == "/api/export":
            self._json(
                200,
                {
                    "product": "AzielTether",
                    "author": "Aziel Eliab",
                    "version": __version__,
                    "items": [i.as_dict() for i in self._store().chain().items],
                    "tips": self._store().tips(),
                },
            )
            return
        if path == "/api/shelf":
            from azieltether.shelf import law_card, load_last_shelf, plane_a_card, plane_b_status, plane_c_card

            last = load_last_shelf(self._store())
            stored = self._store().plane_b()
            self._json(
                200,
                {
                    "ok": True,
                    "author": "Aziel Eliab",
                    "shelf": law_card(),
                    "planes": {
                        "A": plane_a_card(),
                        "B": plane_b_status(
                            url=stored.get("url") or None,
                            sha256=stored.get("sha256"),
                            verified=bool(stored.get("verified")),
                        ),
                        "C": plane_c_card(self._store()),
                    },
                    "last": last,
                },
            )
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        store = self._store()
        try:
            if path == "/api/peer":
                body = self._read_json()
                rec = accept_peer(store, body)
                self._json(200 if rec.get("ok") else 400, rec)
                return
            if path == "/api/tick":
                body = self._read_json()
                rec = accept_tick_plane(store, body)
                self._json(200 if rec.get("ok") else 400, rec)
                return
            if path == "/api/payload":
                body = self._read_json()
                rec = serve_payload(store, body)
                self._json(200 if rec.get("ok") else 400, rec)
                return
            if path == "/api/reheal":
                body = self._read_json()
                rec = reheal(
                    store,
                    cite=body.get("cite"),
                    lockset=body.get("lockset"),
                    incoming=body.get("items") if isinstance(body.get("items"), list) else [],
                    votes_for=int(body.get("votes_for") or 0),
                    neighbor_fix=body.get("neighbor_fix"),
                    chatter=body.get("chatter") if isinstance(body.get("chatter"), dict) else None,
                )
                snap = _snapshot(store, rec.get("reheal", {}).get("code", "reheal"))
                snap.update(rec)
                self._json(200 if rec.get("ok") else 400, snap)
                return
            body = self._read_json() if path != "/api/verify" else {}
            if path == "/api/verify":
                self._json(200, _snapshot(store, "Verify."))
                return
            if path == "/api/genesis":
                payload = str(body.get("payload") or "")
                Chain.genesis(store.queue_path, payload=payload, node_id=store.node_id())
                self._json(200, _snapshot(store, "Genesis written."))
                return
            if path == "/api/append":
                chain = store.chain()
                if len(chain) == 0:
                    self._json(400, {"error": "run genesis first"})
                    return
                chain.append(str(body.get("payload") or ""), node_id=store.node_id())
                self._json(200, _snapshot(store, "Appended."))
                return
            if path == "/api/pulse":
                rec = pulse(store, probe=body.get("probe", True))
                rec.update(_snapshot(store, rec.get("mode", "pulse")))
                self._json(200, rec)
                return
            if path == "/api/reconcile":
                incoming = body.get("items") if isinstance(body.get("items"), list) else []
                rec = reconcile(store, incoming=incoming, probe=body.get("probe", True))
                rec.update(_snapshot(store, rec.get("mode", "reconcile")))
                self._json(200, rec)
                return
            if path == "/api/tip":
                tips = bind_surfaces(store.chain(), node_id=store.node_id())
                store.write_tips(tips)
                self._json(200, _snapshot(store, "Lattice tips refreshed."))
                return
            if path == "/api/peer-sync":
                peer = str(body.get("peer") or "").strip()
                if peer:
                    store.add_peer(peer)
                rec = pulse(store, probe=False, harvest_siblings=False)
                rec.update(_snapshot(store, "peer-sync-when-down"))
                self._json(200, rec)
                return
            if path == "/api/import":
                text = str(body.get("text") or "")
                tmp = store.home / "_import.json"
                tmp.write_text(text, encoding="utf-8")
                rec = import_json(tmp, store=store)
                rec.update(_snapshot(store, "Imported."))
                self._json(200, rec)
                return
            if path == "/api/shelf-seal":
                from azieltether.shelf import seal_shelf

                rec = seal_shelf(store)
                rec.update(_snapshot(store, rec.get("code", "shelf-seal")))
                self._json(200 if rec.get("ok") else 400, rec)
                return
            if path == "/api/shelf-sync":
                url = str(body.get("url") or "").strip()
                urls = [url] if url else []
                rec = shelf_sync(
                    store,
                    urls=urls,
                    expected_sha256=str(body.get("sha256") or "").strip() or None,
                    probe=body.get("probe", True),
                    incoming=body,
                )
                rec.update(_snapshot(store, rec.get("code", "shelf-sync")))
                self._json(200 if rec.get("ok") else 400, rec)
                return
            if path == "/api/shelf-attest":
                from azieltether.shelf import attest_usb

                src = str(body.get("src") or "").strip()
                if not src:
                    self._json(400, {"ok": False, "code": "CNS-OPERATOR-ATTEST", "error": "attest needs src"})
                    return
                rec = attest_usb(
                    store,
                    src,
                    expected_sha256=str(body.get("sha256") or "").strip() or None,
                    pack_sha256=str(body.get("pack_sha256") or "").strip() or None,
                    lockset_tip=str(body.get("lockset_tip") or "").strip() or None,
                )
                rec.update(_snapshot(store, rec.get("code", "shelf-attest")))
                self._json(200 if rec.get("ok") else 400, rec)
                return
            if path == "/api/shelf-pull":
                from azieltether.shelf import fetch_manifest, merge_verified_items, seal_shelf

                url = str(body.get("url") or "").strip()
                rec = fetch_manifest(url, expected_sha256=str(body.get("sha256") or "").strip() or None)
                if rec.get("ok") and rec.get("manifest", {}).get("items"):
                    rec["merge"] = merge_verified_items(store, rec["manifest"]["items"])
                    rec["seal"] = seal_shelf(store)
                rec.update(_snapshot(store, rec.get("code", "shelf-pull")))
                self._json(200 if rec.get("ok") else 400, rec)
                return
        except AzielTetherError as exc:
            self._json(400, {"error": str(exc), "limitation": LIMITATION})
            return
        except Exception as exc:  # noqa: BLE001
            self._json(400, {"error": str(exc), "limitation": LIMITATION})
            return
        self._json(404, {"error": "not found"})


def make_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, home: str | Path | None = None) -> TetherServer:
    if host not in LOOPBACK:
        raise ValueError("AzielTether UI binds loopback only (127.0.0.1)")
    httpd = TetherServer((host, port), Handler)
    httpd.store = Store(home)
    return httpd


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, home: str | Path | None = None) -> None:
    httpd = make_server(host, port, home)
    sys.stdout.write(f"Open http://{host}:{port}/\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nstopped\n")
    finally:
        httpd.server_close()
