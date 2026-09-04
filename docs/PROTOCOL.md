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

Broken links are refused. Duplicates (same `hash`) are ignored.

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

The peer path **cannot** write Aziel Library operator records. Public Corpus envelopes only.

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
