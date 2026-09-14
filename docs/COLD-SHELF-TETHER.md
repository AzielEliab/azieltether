# COLD-SHELF TETHER

**Spec:** `COLD-SHELF-TETHER-1.0`
**Author:** Aziel Eliab only
**Product:** AzielTether
**Person @id:** https://www.azieleliab.com/#aziel
**Beside:** `COLD-COPY-SURVIVAL-1.0`, `REHEAL-1.0`, `SPLIT-THE-WIRES-1.0`
**Sister:** aziel-corpus `COLD-MULTI-SHELF-1.0` (export / verify / registry)
**Laws cited:** `CROSS-NETWORK-SURVIVAL-1.0`, `NO-LIE-NO-REWRITE-1.0`,
ingest-as-receipt, `RE-EXPAND-FROM-ARCHIVE`, `REHEAL`, `NO-FAN`
**Lamb Lens:** Service→Clarity→Peace

Coordinate with the corpus shelf by **citing the same lockset tip hashes**.
Do not fork Person @id `https://www.azieleliab.com/#aziel`.

## Why this exists

The counted download and hosted `/v1` live on a Cloudflare Worker. GitHub
is a source mirror. If both are yanked, hub tip/receipts must still be
on disk, on a USB, or on an operator-configured **non-Cloudflare** raw
URL. This is the tether path, not a second identity and not a VPN.

The Worker is **zero-retention**. It acknowledges hashes. It does not
store the chain. Claiming it holds durable tips after a yank is a lie.

## Operator planes (2026-09-14)

| Plane | What | Survives CF+GitHub yank? | State |
|-------|------|--------------------------|--------|
| **A** | Four product Workers on the **same** Cloudflare tunnel (`vibelock.workers.dev`): AzielTether, AZ-CLCE, TemporalLock, StaticClock | No. Same tunnel. | REAL probe + ingest-as-receipt on this product. **Worker-up pulls Plane A.** |
| **B** | Independent shelves: **Codeberg**, **archive.org**, **GitFlic** | Yes, after SHA-256 verify | **SLOT** until hash-verify on those hosts. **Zenodo is IP-banned.** Do not invent a DOI. |
| **C** | Last local cold-shelf + USB airgap | Yes | Last local seal is the Worker-down archive. **USB tip-pack goes LIVE only after `sha256sum -c` plus operator attest.** Refuse `CNS-OPERATOR-ATTEST` until then. |

**Worker-up** pulls **Plane A**. **Worker-down** serves last **Plane C**
local cold-shelf. **Restore** reconciles by hash (never rewrite).
Plane B is pulled only after a SHA-256 check on Codeberg, archive.org,
or GitFlic. A URL without a matching digest stays SLOT. No invented
DOIs or CIDs.

Operator tip-pack cite (2026-09-14) — not a DOI:

- lockset tip `c831429befc221bd41caeb0a6d1c5361602db5684abab7af6d39714084b6b245`
- pack_sha256 `b549362c0736ddb54ddc488812327c464e0da1167281f92fd1a4263eedf5df37`

```bash
azieltether shelf status --plane-b-url https://codeberg.org/<group>/<repo>/raw/<rev>/shelf/manifest.json \
  --sha256 <64 lowercase hex>
azieltether shelf sync --plane-b-url https://archive.org/download/<item>/manifest.json \
  --sha256 <64 lowercase hex>
azieltether shelf attest --src /media/usb/aziel-shelf \
  --sha256 b549362c0736ddb54ddc488812327c464e0da1167281f92fd1a4263eedf5df37 \
  --lockset-tip c831429befc221bd41caeb0a6d1c5361602db5684abab7af6d39714084b6b245
```

`--zenodo-doi` / `--zenodo-url` refuse (`SHELF-DOI-REFUSED` /
`SHELF-SLOT-ZENODO-DOI`). Zenodo is dead on this path.

## Law

1. **Prefer Worker when up.** Probe `GET /v1/health`. Ingest-as-receipt
   (`POST /v1/ingest`, `POST /v1/tip`). Then seal tip + receipts into
   the local cold-shelf (`~/.azieltether/shelf/`).
2. **When Worker is dead, serve the last local cold copy.** Do not
   invent a tip. `RE-EXPAND-FROM-ARCHIVE` is that last sealed shelf.
3. **On restore, reconcile by hash.** Union merge. Dual-chain keeps both
   children of the same `prev_hash`. Never rewrite an existing item.
4. **Fetch/verify a SHA-256 manifest** from configurable URLs: local
   path, `file://`, Codeberg raw, archive.org, GitFlic. Refuse on
   hash mismatch (`SHELF-HASH-MISMATCH`).
5. **No rewrite key. No lie-to-survive.** A yank does not authorize a
   historian. Votes cannot flip a broken digest. Neighbors cannot
   vote-to-fix (`REHEAL`).
6. **NO-FAN.** Unverified shelf bodies are not pushed to a crowd.
   Receiver pulls a verified shelf.
7. **Plane B stays SLOT** until hash-verify on an independent shelf
   (not Zenodo). Do not invent a DOI.
8. **Plane C USB tip-pack** is not LIVE until the operator runs
   `sha256sum -c` and `azieltether shelf attest`. Until then refuse
   `CNS-OPERATOR-ATTEST`.

`azieltether shelf` prints the law card and last local shelf.
`GET /v1/shelf` returns the same honest card (no durable store).

## REAL vs MOCK

**REAL (implemented in this tree):**

| Capability | What it does |
|------------|----------------|
| Worker probe | `GET /v1/health` decides up / down |
| ingest-as-receipt | Worker ack hashes recorded on the shelf |
| Local seal | `shelf/manifest.json` + `queue.jsonl` + `manifest.sha256` |
| Serve last local | When Worker is down, that file is the archive |
| Hash reconcile | Restore merges by hash; no rewrite |
| Manifest SHA-256 | Canonical JSON digest + raw-bytes digest |
| Local / file:// fetch | Read and verify |
| HTTPS raw fetch | GET Codeberg / archive.org / GitFlic (or any https) + verify |
| USB airgap | `shelf usb` / `shelf usb-import` |
| Operator attest | `shelf attest` after `sha256sum -c` → USB tip-pack LIVE |
| Refuse rewrite key | `SHELF-REWRITE-REFUSED` |
| Refuse lie-to-survive | `SHELF-LIE-REFUSED` |
| Refuse hash mismatch | `SHELF-HASH-MISMATCH` |
| Refuse invented DOI | `SHELF-DOI-REFUSED` |
| Refuse USB LIVE without attest | `CNS-OPERATOR-ATTEST` |

**MOCK / SLOT (not implemented — refuse codes, never claimed live):**

| Slot | Refuse code | Honest note |
|------|-------------|-------------|
| Live multi-homed DNS | `SHELF-SLOT-MULTIHOME-DNS` | Not implemented |
| IPFS CIDs | `SHELF-SLOT-IPFS` | Do not invent a CID |
| Auto-publish to Codeberg/archive.org/GitFlic | `SHELF-SLOT-AUTO-PUBLISH` | Operator copies files |
| Anycast / geo-DNS | `SHELF-SLOT-ANYCAST` | Not implemented |
| AZ Generator | `SHELF-SLOT-AZ-GENERATOR` | MirageGrid-only; refused here |
| Zenodo DOI | `SHELF-SLOT-ZENODO-DOI` | IP-banned. Do not invent a DOI |
| Plane B until hash-verify | `SHELF-SLOT-ALT-SHELF` | Codeberg / archive.org / GitFlic only |

## Operator: airgap a USB shelf tonight

On the live machine (Worker may be up or down):

```bash
azieltether init
azieltether genesis --payload "desk closed"   # if the DAG is empty
azieltether shelf seal
azieltether shelf usb --dest /media/usb/aziel-shelf
```

That writes:

```
/media/usb/aziel-shelf/manifest.json
/media/usb/aziel-shelf/manifest.sha256
/media/usb/aziel-shelf/queue.jsonl
/media/usb/aziel-shelf/tips.json
/media/usb/aziel-shelf/lockset.json
/media/usb/aziel-shelf/README.txt
```

Unplug the USB. On the airgapped machine:

```bash
sha256sum -c /media/usb/aziel-shelf/manifest.sha256
azieltether shelf usb-import --src /media/usb/aziel-shelf
azieltether shelf attest --src /media/usb/aziel-shelf
azieltether verify
```

Import merges verified hashes (never rewrite). **Attest** is what
marks the USB tip-pack LIVE. Claiming LIVE without that step refuses
`CNS-OPERATOR-ATTEST`. Import refuses if `manifest.sha256` (or
`--sha256`) does not match the file bytes, or if the embedded
canonical `sha256` does not match the body. Existing local items are
kept. Incoming verified hashes are appended. Nothing is rewritten.

Optional non-Cloudflare pull (when those hosts are still up):

```bash
azieltether shelf pull \
  --url https://codeberg.org/<group>/<repo>/raw/<rev>/shelf/manifest.json \
  --sha256 <64 lowercase hex>
```

Same shape works for archive.org and GitFlic. Set
`AZIELTETHER_SHELF_URLS` (comma-separated) for `shelf sync` to try
those mirrors whenever you pulse the shelf. Plane B goes LIVE only
when the host is allowlisted **and** the SHA-256 check passes.

## Sync modes

| Mode | When | Action |
|------|------|--------|
| prefer-central | Worker `/v1/health` ok | Ingest-as-receipt, pull configured URLs, seal local. Active plane **A**. |
| serve-last-local | Worker down or `AZIELTETHER_OFFLINE=1` | Serve `shelf/manifest.json`; still verify configured URLs if reachable. Active plane **C**. |
| reconcile-on-restore | Worker returns after a recorded down | Hash union; seal; no rewrite. Active plane **A**. |

`azieltether shelf sync` is the one command that walks that path.

## What this is not

Not a VPN. Not MirageGrid. Not AZ Generator. Not live multi-homed DNS.
Not an IPFS pinset. Not a claim that Cloudflare or GitHub will stay up.
Not a Zenodo DOI. Public HTTPS boards stay mesh-free.

Apache-2.0. Forks are welcome and always allowed.
