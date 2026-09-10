# AzielTether

Central × decentral node-mesh **software tether** by **Aziel Eliab**.

Prefer the central Worker when it is up. When it is down, downloaded nodes
sync hash-chained work with each other when they hit the internet, then
reconcile back to central on restore. Dual-chain on same-hash conflict.
Hash lattice tips survive across GodLock, Aziel Digital Library, and
product Workers.

**Author:** Aziel Eliab
**Date:** September 2026 · v0.1.0
**License:** [Apache-2.0](LICENSE)
**Spec:** `azieltether-v0` — [docs/whitepaper.md](docs/whitepaper.md)

> Prefer central. Peer when down. Reconcile on restore.

**Forks are welcome and always allowed.**

Live public HTTPS boards (e.g. godlock.uk) stay mesh-free — the tether
lives in the **downloaded software**.

## Honest scope

**THIS IS:** a software tether (prefer-central / peer-sync-when-down /
reconcile-on-restore) plus dual-chain forks and lattice tips.

**THIS IS NOT:** a VPN, MirageGrid, a kernel, a truth score, a backdoor,
or a mesh on godlock.uk.

## One-click install

```bash
curl -fsSL https://azieltether-download-tracker.vibelock.workers.dev/install.sh | bash
```

The script curls the **counted** tarball from this project's Worker
(`/download`, User-Agent `Mozilla/5.0`), extracts, makes a venv, and
`pip install -e .`. Then run `azieltether ui`.

Or tap **Download** / **One-click install** on the Worker homepage:
https://azieltether-download-tracker.vibelock.workers.dev/

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
azieltether init
azieltether genesis --payload "desk closed"
azieltether append --payload "score report queued"
azieltether verify
azieltether pulse
azieltether ui
```

Open http://127.0.0.1:8874 (loopback only). No CDN, no telemetry.

Self-check: `azieltether doctor`.

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

Sibling products (AZ-CLCE / SPRE) already append
`~/.az-clce/tether-queue.jsonl`. `azieltether harvest` copies those
items (scopes `az-clce` / `spre`) into the local DAG.

## CLI

```bash
azieltether version
azieltether ui        # localhost UI on 127.0.0.1:8874
azieltether doctor
azieltether init
azieltether genesis --payload "desk closed"
azieltether append --payload "queued while central was down"
azieltether verify
azieltether pulse
azieltether peer-sync --peer http://127.0.0.1:8875
azieltether reconcile
azieltether dual-chain
azieltether tip --surface worker
azieltether harvest
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
CLI, and loopback UI.

## Layout

```
azieltether/                 library (item, chain, protocol, lattice, cli, ui)
tests/                       pytest
docs/whitepaper.md           September 2026 spec
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
