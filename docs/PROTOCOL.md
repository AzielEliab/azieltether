# AzielTether protocol 0.1.0

Author: **Aziel Eliab**. License: Apache-2.0. Forks always allowed.

AzielTether is a **content/work tether**. It is not a VPN, Tor overlay, or anonymity network. Live public HTTPS sites (`godlock.uk`, the Corpus library UI) stay **mesh-free**. The mesh lives in **downloaded software** plus optional Worker bootstrap APIs.

The download-tracker Worker is a **peer directory and holding pen**. It is not a full mesh.

## Prefer-central

Each node tries destinations in this order:

1. **Product ingest** (optional env URL that already speaks this protocol). Never the public board UI.
2. **Tether bootstrap Worker** — `https://azieltether-download-tracker.vibelock.workers.dev`
3. **Last known peers** from the local store (and gossip from those peers)
4. **Local only** — keep a backlog until something comes back

`godlock.uk`, `www.azielcorpuslibrary.net`, and the catalog HTML stay ordinary HTTPS. Doctor may ping them for a status light. Nodes do **not** POST mesh batches at those boards.

## On central failure

1. Keep working locally (`azieltether batch` / product embed).
2. `azieltether serve` on loopback (`127.0.0.1:19740`) so nearby downloaded nodes can pull.
3. `azieltether announce` writes the node into the last peer list and gossips if any peer is online.
4. `azieltether push` / `pull` exchange signed batches over HTTP(S) when a peer is reachable.
5. When the bootstrap Worker or a product ingest returns, `azieltether reconcile` drains the local backlog.

Loopback endpoint hints are stored as hints. They are not globally reachable. That is expected for MVP.

## Hash-chain

Each batch is a JSON object. Hash and signature cover every field except `hash` and `signature`.

Canonical form: UTF-8 JSON, sorted keys, no extra spaces (`separators=(",", ":")`).

```
hash = SHA-256(canonical_json(signing_body)) as 64 lowercase hex
signature = Ed25519(private_key, ascii(hash)) as standard Base64
prev_hash = previous batch hash, or 64 zeros for a genesis
```

A receiver **must** verify, in order:

1. `scope` is `godlock`, `aziel-corpus`, or `aziel-runtime`
2. `kind` matches the scope table below
3. the batch is not an Aziel Library operator write
4. `prev_hash` is 64 hex
5. recomputed hash equals `hash`
6. Ed25519 verify(`pubkey`, `hash`, `signature`) succeeds
7. if the node already has a tip for that scope, `prev_hash` equals that tip (or the batch is a duplicate)
8. a **same-hash collision** or **fork** does **not** silently merge — see Dual-chain conflict

Broken links are refused. Identical duplicates (same hash and same signing body) are idempotent sync. That is not a silent merge.

## Ed25519 node keypair

First run writes `~/.azieltether/node.json` (or `$AZIELTETHER_HOME`):

- raw 32-byte private key, Base64
- raw 32-byte public key, Base64
- `node_id` = SHA-256(public raw bytes) as hex

The private key never leaves the machine and must not be committed. Rotate by deleting `node.json`.

## Scopes

| Scope | Kind | What it carries | Forbidden |
|-------|------|-----------------|-----------|
| `godlock` | `receipt` | GodLock receipts / challenge records from **downloaded** GodLock | Writing the public `godlock.uk` board as a mesh |
| `aziel-corpus` | `ingest_envelope` | Public Corpus ingest envelopes | Operator Aziel Library writes (`operator: true`, `library_role=operator`, or kinds `library_operator` / `operator_record` / `aziel_library_write`) |
| `aziel-runtime` | `catalog_event` | Catalog events for aziel-runtime | Treating the catalog HTML as a mesh peer |
| `lattice` | `anchor` | Cross-product survival anchors | Claiming the Worker is the lattice itself |
| `precedent` | `conflict_receipt` | Chain B conflict precedent | Rewriting chain A |

The peer path **cannot** write Aziel Library operator records. Public Corpus envelopes only.

## Cross-product survival lattice

Every Aziel software node participates in **one** lattice. Scope `lattice`, kind `anchor`.

Anchor payload (also signed as a normal batch):

```json
{
  "product": "foldlock",
  "tip_hash": "64-hex of that product's work tip",
  "prev_anchor": "previous lattice hash or 64 zeros",
  "timestamp": "2026-09-04T00:00:00Z",
  "node_id": "64-hex",
  "cross_links": {
    "godlock": "…",
    "aziel-corpus": "…",
    "foldlock": "…"
  }
}
```

Mutual survival:

- If GodLock survives, corpus can survive (and vice versa) because each anchor carries both tips in `cross_links`.
- If **any** product software node survives (FoldLock, AZ-CLCE, TemporalLock, StaticClock, MirageGrid, AZOS, …), GodLock and corpus **rehydrate** from those anchored cross-links.
- Any surviving tip bootstraps verification of the others: walk the lattice, verify signatures, read `cross_links`.

`azieltether anchor` posts one anchor per local work tip. `azieltether lattice-status` prints rehydratable tips.

This is still a **content/work** lattice. Not a VPN. Public HTTPS boards stay mesh-free.

## Dual-chain conflict (precedent)

If two online users converge on the **same hash-chain tip** (fork collision or accidental identity):

1. Do **not** silently merge as if nothing happened.
2. Keep **chain A** exactly as it is (append-only; never rewrite).
3. Spawn **chain B** (`scope=precedent`, kind `conflict_receipt`) that records:
   - both parent tips
   - collision detection receipt (`fork`, `same_hash_collision`, or `accidental_identity`)
   - which peer set first observed the collision (`observed_by`)
   - tether link back to chain A (`chain_a_tip` / `tether_link`)
4. Chain B **sets precedent** for conflict resolution going forward.

Identical duplicate sync (same hash **and** same body) is not a conflict.

`azieltether conflict-status` lists chain-B receipts.

## Structure verify hooks

On every sensed **upload** or **download** (push, pull, reconcile, local serve POST), the node runs a whole-structure verify and then `on_transfer(event)`.

Sibling engines register without being imported:

```python
import azieltether.hooks as hooks

def clce_rescore(event: dict) -> dict:
    # event["structure"] already verified the local chains
    return {"ok": True}

hooks.register("az-clce", clce_rescore)
```

The event includes `direction` (`upload`|`download`), `via`, `offline`, `batch`, and `structure` (tips + errors). SPRE / AZ-CLCE / others rescore here.

Offline still works: local mint, queue, hash-chain, and hooks fire with `offline: true`. Online still prefers central → peer mesh → reconcile.

## Batch shape

```json
{
  "product": "azieltether",
  "version": "0.1.0",
  "scope": "godlock",
  "kind": "receipt",
  "batch_id": "uuid",
  "node_id": "64-hex",
  "pubkey": "base64",
  "created_at": "2026-09-04T00:00:00Z",
  "prev_hash": "0000…",
  "payload": {},
  "hash": "64-hex",
  "signature": "base64"
}
```

## Worker bootstrap APIs

These are **not** a claim that the Worker is the mesh.

| Method | Path | Role |
|--------|------|------|
| GET | `/v1/tether/health` | Bootstrap liveness |
| POST | `/v1/tether/announce` | Store node id, pubkey, endpoint hint, product scope in KV |
| GET | `/v1/tether/peers?product=` | Recent healthy peer directory (`godlock`, `aziel-corpus`, `aziel-runtime`, or `*`) |
| POST | `/v1/tether/batch` | Hold a verified batch until a product central pulls |
| GET | `/v1/tether/batch?since=` | Pull held batches |

Peer records expire after 72 hours. Held batches keep a per-scope index (newest first, capped).

## Local node HTTP

`azieltether serve` binds **loopback only**.

| Method | Path |
|--------|------|
| GET | `/` status page (plain language) |
| GET | `/v1/health` `/v1/status` `/v1/skill` `/v1/peers` `/v1/batch` |
| POST | `/v1/announce` `/v1/batch` |

## Embed notes (GodLock / aziel-corpus / aziel-runtime)

A sibling product should:

1. Mint a batch with the correct scope/kind when local work happens.
2. Call `Router.push` (or the CLI) instead of assuming the product host is up.
3. On startup, `announce` + `pull` + `reconcile`.
4. Never attach a mesh to the public HTTPS board.

MVP is enough: durable peer directory on the Worker + signed hash-chained batches + local `serve`.
