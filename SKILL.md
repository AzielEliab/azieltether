---
name: AzielTether
description: Use when preferring a central Worker, peer-syncing hash-chained work while it is down, reconciling on restore, or minting lattice tips across GodLock / Aziel Digital Library / product Workers. Software tether, not a VPN. Author Aziel Eliab.
---

# AzielTether

Central × decentral node-mesh **software tether**. Prefer the central Worker when it is up. When it is down, downloaded nodes sync hash-chained work with each other when they hit the internet, then reconcile back to central on restore. Dual-chain on same-hash conflict. Hash lattice tips survive across GodLock, Aziel Digital Library, and product Workers.

Author: **Aziel Eliab**.

**THIS IS:** a software tether (prefer-central / peer-sync-when-down / reconcile-on-restore).

**THIS IS NOT:** a VPN, MirageGrid, a kernel, a truth score, or a mesh on godlock.uk. Public HTTPS boards stay mesh-free. The tether lives in the **downloaded software**. Hosted `/v1` does not increment downloads.

Always send `User-Agent: Mozilla/5.0`. Cloudflare Workers may 403 an empty agent.

## Endpoints (this Worker)

Host: `https://azieltether-download-tracker.vibelock.workers.dev`

| Method | Path | What |
|--------|------|------|
| GET | `/v1/health` | Liveness. Does not increment downloads. |
| GET | `/v1/skill` | This markdown. Does not increment downloads. |
| GET | `/v1/example` | Sample tether item. Does not increment downloads. |
| POST | `/v1/ingest` | Accept one hash-chained item. Zero retention. |
| POST | `/v1/pulse` | Prefer-central probe + unpublished-item preview. |
| POST | `/v1/reconcile` | Merge preview. Dual-chain on same prev_hash. |
| POST | `/v1/dual-chain` | Detect same-prev_hash forks. No winner. |
| POST | `/v1/tip` | Mint or verify a lattice tip. |
| POST | `/v1/verify` | Walk hashes and prev links (DAG). |
| POST | `/v1/peer-preview` | Peer-sync handshake preview. Stateless. |

OpenAPI: `https://azieltether-download-tracker.vibelock.workers.dev/openapi.json`

Catalog OpenAPI: `https://aziel-runtime.vibelock.workers.dev/openapi.json`

MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`

Catalog aliases under `/p/azieltether/…` after the catalog slug is registered.

AZ-CLCE queue hook: sibling products append `~/.az-clce/tether-queue.jsonl`. AzielTether harvests those items (scopes `az-clce` / `spre`) and reconciles via this Worker or `POST /v1/tether-ingest` on the product Worker.

## How to call (Mozilla/5.0)

```bash
curl -s -A 'Mozilla/5.0' https://azieltether-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' -X POST https://azieltether-download-tracker.vibelock.workers.dev/v1/ingest \
  -H 'content-type: application/json' \
  -d '{"scope":"azieltether","payload":"desk closed"}'
curl -s -A 'Mozilla/5.0' https://azieltether-download-tracker.vibelock.workers.dev/v1/skill
```

Grok: import the catalog OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.

## Local (after one-click install)

```bash
curl -fsSL https://azieltether-download-tracker.vibelock.workers.dev/install.sh | bash
azieltether ui
azieltether doctor
```

Then open http://127.0.0.1:8874 (this computer only).

## Honest banner

THIS IS: a central×decentral node-mesh software tether. Prefer the Worker when up. Peer-sync hash-chained work when down. Reconcile on restore. Dual-chain on same-hash conflict. Lattice tips survive across GodLock, Aziel Digital Library, and product Workers. THIS IS NOT: a VPN, MirageGrid, a kernel, a truth score, a backdoor, or a mesh on godlock.uk. Public HTTPS boards stay mesh-free. The tether lives in the downloaded software. Author Aziel Eliab.

Apache-2.0 (or the repo LICENSE). Forks are welcome and always allowed.

## Catalog + local UI

Author: **Aziel Eliab**. Honest scope: software tether, not a VPN.

- Catalog product: https://aziel-runtime.vibelock.workers.dev/p/azieltether/
- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json
- Catalog MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`
- This Worker skill: `GET https://azieltether-download-tracker.vibelock.workers.dev/v1/skill`
- This Worker OpenAPI: https://azieltether-download-tracker.vibelock.workers.dev/openapi.json
- Sample payload: `GET https://azieltether-download-tracker.vibelock.workers.dev/v1/example`

Local UI: **Import JSON file** (`type=file`) and **Export JSON**. Then `azieltether doctor`.

Counted download (gzip HTTP 200, no 302): https://azieltether-download-tracker.vibelock.workers.dev/download?asset=azieltether-0.1.0.tar.gz
GitHub: https://github.com/AzielEliab/azieltether
