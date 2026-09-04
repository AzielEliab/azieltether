---
name: AzielTether
description: Use when a downloaded Aziel Eliab node must keep exchanging hash-chained work if central hosts are down, then reconcile. Content/work tether, not a VPN. Author Aziel Eliab.
---

# AzielTether

Central × decentral software tether. Prefer the central Worker. On failure, peers exchange signed hash-chained batches. Reconcile when central returns.

Author: **Aziel Eliab**. Version 0.1.0.

Always send `User-Agent: Mozilla/5.0`. Cloudflare Workers may 403 an empty agent.

THIS IS: a content/work tether for receipts, public Corpus ingest envelopes, and catalog events.
THIS IS NOT: a VPN, Tor, or anonymity network. The Worker is a bootstrap directory and holding pen — not a full mesh. Live public HTTPS boards stay mesh-free.

## Endpoints (this Worker)

Host: `https://azieltether-download-tracker.vibelock.workers.dev`

| Method | Path | What |
|--------|------|------|
| GET | `/v1/health` | Liveness. Does not increment downloads. |
| GET | `/v1/skill` | This markdown. Does not increment downloads. |
| GET | `/v1/tether/health` | Bootstrap health. Not a full mesh. |
| POST | `/v1/tether/announce` | Register node id, pubkey, endpoint hint, product scope. |
| GET | `/v1/tether/peers?product=` | Recent healthy peer directory (KV). |
| POST | `/v1/tether/batch` | Hold a verified hash-chained batch. |
| GET | `/v1/tether/batch?since=` | Pull held batches. |

OpenAPI: `https://azieltether-download-tracker.vibelock.workers.dev/openapi.json`

Cite: `https://azieltether-download-tracker.vibelock.workers.dev/cite.json`

Catalog: `https://aziel-runtime.vibelock.workers.dev/`

MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`

## How to call (Mozilla/5.0)

```bash
curl -s -A 'Mozilla/5.0' https://azieltether-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' https://azieltether-download-tracker.vibelock.workers.dev/v1/tether/health
curl -s -A 'Mozilla/5.0' https://azieltether-download-tracker.vibelock.workers.dev/v1/tether/peers?product=godlock
curl -s -A 'Mozilla/5.0' https://azieltether-download-tracker.vibelock.workers.dev/v1/skill
```

Grok: import the catalog or Worker OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.

## Local (after one-click install)

```bash
curl -fsSL https://azieltether-download-tracker.vibelock.workers.dev/install.sh | bash
azieltether doctor
azieltether serve
```

Then open http://127.0.0.1:19740 (this computer only).

| Command | What |
|---------|------|
| `azieltether doctor` | Central health + peer store + chain |
| `azieltether serve` | Loopback node HTTP + status page |
| `azieltether announce` | Central register, else peer gossip |
| `azieltether push` | Send a signed hash-chained batch |
| `azieltether pull` | Fetch batches |
| `azieltether reconcile` | Drain backlog when central returns |

## Scopes

- `godlock` — receipts
- `aziel-corpus` — public Corpus ingest envelopes only (never Aziel Library operator writes)
- `aziel-runtime` — catalog events

Protocol: `docs/PROTOCOL.md`.

Apache-2.0 (or the repo LICENSE). Forks are welcome and always allowed.

Counted download (gzip HTTP 200, no 302): https://azieltether-download-tracker.vibelock.workers.dev/download
GitHub: https://github.com/AzielEliab/azieltether
