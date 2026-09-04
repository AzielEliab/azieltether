# AzielTether

Central × decentral node-mesh **software tether** by **Aziel Eliab**.

Prefer the central Worker when it is up. When it is down, downloaded nodes sync hash-chained work with each other when they hit the internet, then reconcile back to central on restore.

Apache-2.0. Forks welcome and always allowed.

Live public HTTPS boards (for example `godlock.uk` and the Corpus library UI) stay **mesh-free**. The tether lives in the **downloaded software** plus optional Worker bootstrap APIs. This is **not** a VPN or anonymity network.

Version **0.1.0**.

## Cites

| What | URL |
|------|-----|
| GitHub | https://github.com/AzielEliab/azieltether |
| Counted `/download` | https://azieltether-download-tracker.vibelock.workers.dev/download |
| Catalog | https://aziel-runtime.vibelock.workers.dev/ |
| OpenAPI | https://azieltether-download-tracker.vibelock.workers.dev/openapi.json |
| Skill | https://azieltether-download-tracker.vibelock.workers.dev/v1/skill |
| Cite | https://azieltether-download-tracker.vibelock.workers.dev/cite.json |

One-click install (counted):

```bash
curl -fsSL https://azieltether-download-tracker.vibelock.workers.dev/install.sh | bash
```

## Install locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
azieltether doctor
azieltether serve
```

Then open http://127.0.0.1:19740 (this computer only). The page says whether the main office is open, how many friend nodes you know, and how much work is waiting.

## CLI

| Command | What |
|---------|------|
| `azieltether doctor` | Central health + peer store + local chain |
| `azieltether serve` | Loopback node HTTP (default `127.0.0.1:19740`) |
| `azieltether announce` | Register with central if up, else peer gossip |
| `azieltether push` | Exchange / mint a signed hash-chained batch |
| `azieltether pull` | Fetch batches from central or peers |
| `azieltether reconcile` | Push local backlog to central when it returns |
| `azieltether batch` | Mint a local batch without sending |
| `azieltether anchor` | Post lattice survival anchors for local product tips |
| `azieltether lattice-status` | Tips that can rehydrate GodLock / corpus / others |
| `azieltether conflict-status` | Chain-B precedent receipts (chain A is never rewritten) |

```bash
azieltether push --scope godlock --kind receipt --payload '{"note":"desk closed"}'
azieltether pull --scope godlock
azieltether reconcile
```

`User-Agent: Mozilla/5.0` on every hosted call.

## How it works (short)

1. Each downloaded node has an **Ed25519** keypair (local only).
2. Work is packed as a **hash-chained batch**. Each batch links `prev_hash`. Receivers verify hash + signature before accept.
3. If the central Worker is healthy, announce and push there.
4. If it is not, use the last peer list and `serve`. Peers exchange batches over HTTP(S) when they are online.
5. When central returns, `reconcile` drains the backlog.

Full rules: [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Scopes

| Scope | Kind | Meaning |
|-------|------|---------|
| `godlock` | `receipt` | GodLock receipts from downloaded software — not a mesh on godlock.uk |
| `aziel-corpus` | `ingest_envelope` | Public Corpus ingest envelopes. **Never** Aziel Library operator writes |
| `aziel-runtime` | `catalog_event` | Catalog events |
| `lattice` | `anchor` | Cross-product survival bookmarks. Any surviving product tip rehydrates the others |
| `precedent` | `conflict_receipt` | Second immutable chain when two users hit the same tip. Never rewrite chain A |

The peer path cannot write Aziel Library operator records.

**Mutual survival.** If GodLock survives, corpus can survive (and vice versa). If any downloaded product node survives (FoldLock, AZ-CLCE, TemporalLock, StaticClock, MirageGrid, AZOS, …), GodLock and corpus rehydrate from lattice anchors.

**Conflicts.** Same-hash / fork collisions do not silently merge. Chain B records both parent tips and sets precedent.

**Hooks.** Every upload or download runs `azieltether.hooks.on_transfer(event)` after a whole-structure verify so SPRE / AZ-CLCE can rescore.

## Worker bootstrap (not a full mesh)

`workers/download-tracker/` follows the usual counted-download pattern:

- `/download` — gzip HTTP 200 (no 302), isolated KV
- `/install.sh`
- `/v1/health`, `/v1/skill`, `/openapi.json`, `/cite.json`, `/llms.txt`, `/ai.txt`, `/robots.txt`, `/sitemap.xml`
- Open crawl: `robots.txt` allows GPTBot and common AI bots
- Tether APIs: `/v1/tether/health`, `/v1/tether/announce`, `/v1/tether/peers`, `/v1/tether/batch`

`wrangler.toml` uses account `ac575a9b822bea2bed97d0ab73aed238` (same pattern as sibling products under `*.vibelock.workers.dev`).

Pack the counted tarball:

```bash
bash scripts/pack.sh
```

## Tests

```bash
python -m pytest -q
```

Covers hash-chain, prefer-central, peer-fallback, and reconcile.

## Honest banner

THIS IS: a software tether so downloaded Aziel Eliab products can keep exchanging receipts, public Corpus envelopes, and catalog events when a central host is down.

THIS IS NOT: a VPN, a rewrite of godlock.uk, or a way for peers to write operator Aziel Library records.

Author: **Aziel Eliab**.
