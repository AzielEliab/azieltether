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
from azieltether.protocol import LIMITATION, accept_peer, dual_chain_report, pulse, reconcile
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
    --bg: #0f1419; --panel: #171e27; --ink: #e8edf2; --muted: #8b97a6;
    --line: #2a3544; --gold: #d4bc6a; --focus: #7aa2d4; --bad: #d4534b;
    --pass: #3dba7a;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; background: var(--bg); color: var(--ink);
    font-family: system-ui, "Segoe UI", sans-serif; line-height: 1.45;
  }
  body { max-width: 48rem; margin: 0 auto; padding: 2.1rem 1.2rem 4rem; }
  .tag {
    font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.72rem;
    letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted);
  }
  h1 { font-size: 2rem; font-weight: 650; letter-spacing: 0.04em; margin: 0.35rem 0 0.25rem; }
  .motto { color: var(--gold); font-style: italic; margin: 0 0 0.85rem; font-size: 1.05rem; }
  .lede { color: var(--muted); margin: 0 0 1.5rem; max-width: 42rem; }
  fieldset {
    border: 1px solid var(--line); border-radius: 10px; background: var(--panel);
    padding: 1.1rem 1.15rem 1.2rem; margin: 0 0 1rem;
  }
  legend {
    font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.72rem;
    letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); padding: 0 0.4rem;
  }
  label { display: block; font-size: 0.92rem; margin: 0.85rem 0 0.3rem; }
  textarea, input[type="text"] {
    width: 100%; padding: 0.55rem 0.65rem; border: 1px solid var(--line);
    border-radius: 6px; background: #10161d; color: var(--ink); font: inherit;
  }
  textarea:focus, input:focus { outline: 2px solid var(--focus); outline-offset: 1px; }
  .actions { display: flex; gap: 0.65rem; flex-wrap: wrap; margin: 0 0 1.2rem; }
  button, .filebtn {
    font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.85rem;
    letter-spacing: 0.04em; padding: 0.65rem 1rem; border-radius: 8px;
    border: 1px solid var(--ink); background: var(--ink); color: var(--bg);
    cursor: pointer; font-weight: 650;
  }
  button.ghost { background: transparent; color: var(--ink); }
  .banner {
    margin: 0 0 1rem; padding: 0.9rem 1rem; border-radius: 10px;
    border: 1px solid var(--line); background: var(--panel); color: var(--muted);
  }
  .banner.ok { color: var(--pass); border-color: var(--pass); }
  .banner.bad { color: var(--bad); border-color: var(--bad); }
  .item {
    border: 1px solid var(--line); border-radius: 10px; background: var(--panel);
    padding: 0.85rem 1rem; margin: 0 0 0.65rem;
  }
  .hash { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.75rem; word-break: break-all; color: var(--muted); }
  footer { margin-top: 2rem; color: var(--muted); font-size: 0.88rem; }
  input[type="file"] { display: none; }
</style>
</head>
<body>
  <header>
    <div class="tag">AzielTether · __VERSION__ · software tether · loopback</div>
    <h1>AzielTether</h1>
    <p class="motto">Prefer central. Peer when down. Reconcile on restore.</p>
    <p class="lede">
      Central × decentral node-mesh software tether. Prefer the Worker when
      it is up. When it is down, nodes sync hash-chained work with each other,
      then reconcile on restore. Dual-chain keeps both children of the same
      prev_hash. Lattice tips survive across GodLock, Aziel Digital Library,
      and product Workers. Public boards stay mesh-free. Bound to 127.0.0.1.
    </p>
  </header>

  <p class="banner" id="status">Loading…</p>

  <fieldset>
    <legend>New item</legend>
    <label for="payload">Payload (required)</label>
    <textarea id="payload" rows="3" placeholder="desk closed / score report / tip note"></textarea>
    <div class="actions" style="margin-top:1rem">
      <button type="button" id="genesis">Genesis</button>
      <button type="button" id="append">Append</button>
      <button type="button" class="ghost" id="verify">Verify</button>
    </div>
  </fieldset>

  <div class="actions">
    <button type="button" id="pulse">Pulse</button>
    <button type="button" class="ghost" id="reconcile">Reconcile</button>
    <button type="button" class="ghost" id="dual">Dual-chain</button>
    <button type="button" class="ghost" id="tips">Tips</button>
    <button type="button" class="ghost" id="doctor">Doctor</button>
    <label class="filebtn">Import JSON<input type="file" id="import-json" accept=".json,application/json"></label>
    <button type="button" class="ghost" id="export">Export JSON</button>
  </div>

  <fieldset>
    <legend>Peer URL (when central is down)</legend>
    <input id="peer" type="text" placeholder="http://127.0.0.1:8875">
    <div class="actions" style="margin-top:0.8rem">
      <button type="button" class="ghost" id="peer-add">Add peer + sync</button>
    </div>
  </fieldset>

  <h2 class="tag">Items</h2>
  <div id="items"></div>
  <pre id="out" class="hash"></pre>
  <footer>
    <p>Author Aziel Eliab. Apache-2.0. Forks welcome. Not a VPN. Not MirageGrid.</p>
    <p class="lede">__LIMIT__</p>
  </footer>
<script>
(function () {
  const $ = (id) => document.getElementById(id);
  const out = $("out");
  const status = $("status");
  function banner(text, ok) {
    status.textContent = text;
    status.className = "banner " + (ok ? "ok" : "bad");
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
    return r.json();
  }
  function draw(data) {
    out.textContent = JSON.stringify(data, null, 2);
    const items = data.items || data.chain || [];
    const box = $("items");
    box.innerHTML = "";
    (Array.isArray(items) ? items : []).forEach((it, i) => {
      const d = document.createElement("div");
      d.className = "item";
      d.innerHTML = "<div class='hash'>#" + i + " " + (it.created_at || "") + " · " + (it.kind || "work") + " · " + (it.scope || "") + "</div>"
        + "<div>" + (it.payload || it.report_hash || "") + "</div>"
        + "<div class='hash'>prev " + (it.prev_hash || "") + "</div>"
        + "<div class='hash'>hash " + (it.hash || "") + "</div>";
      box.appendChild(d);
    });
    const mode = data.mode || (data.verify && data.verify.ok ? "verify-ok" : "");
    if (data.error) banner(data.error, false);
    else banner((mode || "ready") + " · items " + ((data.verify && data.verify.items) || (Array.isArray(items) ? items.length : 0)), !data.error);
  }
  async function refresh() { draw(await get("/api/status")); }
  $("genesis").onclick = async () => draw(await post("/api/genesis", { payload: $("payload").value }));
  $("append").onclick = async () => draw(await post("/api/append", { payload: $("payload").value }));
  $("verify").onclick = async () => draw(await post("/api/verify", {}));
  $("pulse").onclick = async () => draw(await post("/api/pulse", {}));
  $("reconcile").onclick = async () => draw(await post("/api/reconcile", {}));
  $("dual").onclick = async () => draw(await get("/api/dual-chain"));
  $("tips").onclick = async () => draw(await post("/api/tip", {}));
  $("doctor").onclick = async () => draw(await get("/api/doctor"));
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
  };
  refresh().catch((e) => banner(String(e), false));
})();
</script>
</body>
</html>
""".replace("__VERSION__", __version__).replace("__LIMIT__", LIMITATION)


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
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        store = self._store()
        try:
            if path == "/api/peer":
                body = self._read_json()
                self._json(200, accept_peer(store, body))
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
    sys.stdout.write(f"AzielTether UI  http://{host}:{port}/\n")
    sys.stdout.write("Local only. Prefer central. Peer when down. Reconcile on restore.\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nstopped\n")
    finally:
        httpd.server_close()
