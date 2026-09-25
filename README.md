# AzielTether

AzielTether keeps a hash-chained copy of your work on this computer and syncs it with the central Worker when that Worker is up.

**Author:** Aziel Eliab
**License:** [Apache-2.0](LICENSE)

Prefer central. Peer when down. Reconcile on restore.

## Start

1. Install:

```bash
python -m venv .venv && source .venv/bin/activate && pip install -e .
```

Or, from the counted download:

```bash
curl -fsSL https://azieltether-download-tracker.vibelock.workers.dev/install.sh | bash
```

2. Open the app:

```bash
azieltether ui
```

3. Open http://127.0.0.1:8874 and press **Start chain**.

Self-check: `azieltether doctor`. Machine-readable output: add `--json`.

Forks are welcome and always allowed. Spec: [docs/whitepaper.md](docs/whitepaper.md).

## Counted download (Cloudflare Worker)

**This is the counted download.** GitHub releases exist as a mirror.
The Worker serves the gzip itself (HTTP 200, no 302 to GitHub).

# → [https://azieltether-download-tracker.vibelock.workers.dev/](https://azieltether-download-tracker.vibelock.workers.dev/) ←

Direct tarball (also counted):
[azieltether-0.1.0.tar.gz](https://azieltether-download-tracker.vibelock.workers.dev/download?asset=azieltether-0.1.0.tar.gz)

- Live count JSON: [https://azieltether-download-tracker.vibelock.workers.dev/count](https://azieltether-download-tracker.vibelock.workers.dev/count)
- Stats: [https://azieltether-download-tracker.vibelock.workers.dev/stats](https://azieltether-download-tracker.vibelock.workers.dev/stats)
- Skill: [https://azieltether-download-tracker.vibelock.workers.dev/v1/skill](https://azieltether-download-tracker.vibelock.workers.dev/v1/skill)
- Suite mesh proxy: [https://azieltether-download-tracker.vibelock.workers.dev/v1/mesh](https://azieltether-download-tracker.vibelock.workers.dev/v1/mesh) — default OFF; QNM live / locked / isolated; QNS-CD-1.0 hub cite (photon QNS1 packet transfer; no public qnsd proxy)
- Wires + survival + reheal + shelf: [https://azieltether-download-tracker.vibelock.workers.dev/v1/wires](https://azieltether-download-tracker.vibelock.workers.dev/v1/wires) · [https://azieltether-download-tracker.vibelock.workers.dev/v1/survival](https://azieltether-download-tracker.vibelock.workers.dev/v1/survival) · [https://azieltether-download-tracker.vibelock.workers.dev/v1/reheal](https://azieltether-download-tracker.vibelock.workers.dev/v1/reheal) · [https://azieltether-download-tracker.vibelock.workers.dev/v1/shelf](https://azieltether-download-tracker.vibelock.workers.dev/v1/shelf)
- OpenAPI: [https://azieltether-download-tracker.vibelock.workers.dev/openapi.json](https://azieltether-download-tracker.vibelock.workers.dev/openapi.json)
- GitHub: [https://github.com/AzielEliab/azieltether](https://github.com/AzielEliab/azieltether)

Isolated counter: Worker `azieltether-download-tracker`, KV `AZIELTETHER_DOWNLOADS`. `/v1` does not increment downloads.

## Protocol

1. **Prefer-central.** `azieltether pulse` probes `GET /v1/health`. When
   the Worker is up, unpublished items POST to `/v1/ingest` (zero
   retention on the host).
2. **Peer-sync-when-down.** If central is down (or `AZIELTETHER_OFFLINE=1`),
   nodes exchange hash-chained items with configured peer URLs
   (`azieltether peer-sync --peer URL`). The local UI exposes
   `POST /api/peer`.
3. **Reconcile-on-restore.** When central returns, `azieltether reconcile`
   merges incoming items and pushes unpublished hashes.
4. **Dual-chain.** Two children of the same `prev_hash` with different
   hashes are both kept. AzielTether does not pick a winner.
5. **Lattice tips.** `azieltether tip --surface godlock|corpus|worker`
   mints a last-known hash for survival across GodLock, Aziel Digital
   Library, and product Workers. Tips are receipts, not a mesh on the
   public boards.
6. **SPLIT THE WIRES** (`SPLIT-THE-WIRES-1.0`). Fast tick is presence +
   tip hash only (fixed-size, 0.5–1s). Payload is a receiver pull on a
   separate 777s gate socket. Update is cite + lockset, fail-closed.
   Equivocation isolates the peer. Heartbeat loss is not poison.
7. **COLD-COPY SURVIVAL** (`COLD-COPY-SURVIVAL-1.0`). Multiply sealed
   local copies. Refuse live body sync across the network. Tips are
   expensive to erase. A single-server pull cannot kill local copies.
   Hash-absolute. Data outlives creators.
8. **REHEAL** (`REHEAL-1.0`). Heal from your own last good tip plus a
   verified trusted pull, or phoenix-WAIT. No neighbor vote-to-fix.
   Allowed chatter is live / locked / isolated / tip-hash only.
9. **COLD-SHELF TETHER** (`COLD-SHELF-TETHER-1.0`). Prefer Worker when
   up (Plane A: ingest-as-receipt, then seal). When Worker is dead,
   serve the last Plane C local cold-shelf. On restore, reconcile by
   hash — never rewrite. Plane B is SLOT until SHA-256 verify on
   Codeberg, archive.org, or GitFlic. Zenodo is IP-banned — do not
   invent a DOI. USB tip-pack goes LIVE only after `sha256sum -c` plus
   operator attest (`CNS-OPERATOR-ATTEST` until then). No rewrite key.
   No lie-to-survive. Multi-homed DNS, IPFS CIDs, auto-publish, and AZ
   Generator are MOCK/SLOT. Sister: aziel-corpus `COLD-MULTI-SHELF-1.0`
   (same lockset tip hashes). Lamb Lens: Service→Clarity→Peace.
   Person @id `https://www.azieleliab.com/#aziel`.

Law: [docs/SPLIT-THE-WIRES.md](docs/SPLIT-THE-WIRES.md) ·
[docs/COLD-COPY-SURVIVAL.md](docs/COLD-COPY-SURVIVAL.md) ·
[docs/REHEAL.md](docs/REHEAL.md) ·
[docs/COLD-SHELF-TETHER.md](docs/COLD-SHELF-TETHER.md)

Sibling products (AZ-CLCE / SPRE) already append
`~/.az-clce/tether-queue.jsonl`. `azieltether harvest` copies those
items (scopes `az-clce` / `spre`) into the local DAG.

## CLI

People get short text. Add `--json` for the same records agents already use.

```bash
azieltether
azieltether ui
azieltether init
azieltether genesis --payload "desk closed"
azieltether append --payload "queued while central was down"
azieltether status
azieltether pulse
azieltether doctor
azieltether version
```

Advanced commands (still installed): `verify`, `show`, `node-id`, `peer-sync`, `reconcile`, `dual-chain`, `tip`, `harvest`, `wires`, `survival`, `reheal`, `shelf`, `import`, `export`.

```bash
azieltether peer-sync --peer http://127.0.0.1:8875
azieltether reconcile
azieltether dual-chain
azieltether tip --surface worker
azieltether harvest
azieltether wires
azieltether survival
azieltether reheal
azieltether shelf
azieltether shelf seal
azieltether shelf sync --plane-b-url https://codeberg.org/… --sha256 <hex>
azieltether shelf usb --dest /media/usb/aziel-shelf
azieltether shelf attest --src /media/usb/aziel-shelf
azieltether status --json
```

## iPhone & Android

Flutter sources: [`mobile/`](mobile/). Application id `com.azieeliab.azieltether`.
Offline. No analytics. Dark matte / gold.

```bash
cd mobile
flutter create --org com.azieeliab --project-name azieltether .
flutter pub get
flutter run
```

The `android/` and `ios/` folders in this tree are skeleton READMEs until
you run `flutter create .` (this machine has no Flutter SDK on PATH).

## Tests

```bash
pip install -e ".[dev]"
python -m pytest -q
```

Offline. They cover genesis linking, dual-chain (no winner), harvest of
AZ-CLCE-shaped items, pulse-when-down, reconcile merge, doctor identity,
CLI, loopback UI, and cold-shelf up→down→restore hash continuity.

## Layout

```
azieltether/                 library (item, chain, protocol, lattice, cli, ui)
tests/                       pytest
docs/whitepaper.md           September 2026 spec
docs/SPLIT-THE-WIRES.md      tick vs 777s gate
docs/COLD-COPY-SURVIVAL.md   multiply copies; no live body sync
docs/REHEAL.md               own tip + trusted pull or phoenix-WAIT
docs/COLD-SHELF-TETHER.md    non-CF shelf; USB airgap; REAL vs MOCK
examples/                    pulse and reconcile demo
workers/download-tracker/    Cloudflare Worker + wrangler.toml
mobile/                      Flutter iPhone + Android (`flutter create .`)
```

## Use with AI assistants

Works with ChatGPT (GPT Actions / OpenAI), Grok (xAI), Venice,
Claude (Anthropic), Cursor (MCP), Glama (MCP), Perplexity,
Microsoft Copilot / Bing, Google Gemini / Vertex, Mistral, Meta AI,
Apple Intelligence surfaces, Amazon Q tooling, DuckAssist, You.com,
Cohere, and other MCP/OpenAPI-capable assistants.

Live HTTPS runtime on the download-tracker Worker. Stateless: send the
items JSON in the body. Always `User-Agent: Mozilla/5.0`.

```
https://azieltether-download-tracker.vibelock.workers.dev/openapi.json
```

MCP catalog (ships separately): `https://aziel-runtime.vibelock.workers.dev/mcp`. Suite mesh `/v1/mesh/*` PROXY via `AZIEL_RUNTIME` (default OFF; QNM-BUILD-1.0 live|locked|isolated; no Node Gate). **QNS-CD-1.0** (photon QNS1 packet transfer) is a hub cite / Worker mesh cross-map only — local `qnsd` lives in [qnm-node](https://github.com/AzielEliab/qnm-node); runtime cites + catalog field live in [aziel-runtime](https://github.com/AzielEliab/aziel-runtime); pair custody is [AZInterface](https://github.com/AzielEliab/azinterface). Not a Softwares-tab product. No public qnsd proxy. Catalog MCP `mesh_*` + FragGate `slug=mesh`.

After first deploy, register slug `azieltether` on aziel-runtime so
`/p/azieltether/{op}` proxies here.

## License

Apache-2.0. See [LICENSE](LICENSE).

Forks are welcome and always allowed.
