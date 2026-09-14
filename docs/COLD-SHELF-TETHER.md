# COLD-SHELF TETHER

**Spec:** `COLD-SHELF-TETHER-1.0`
**Author:** Aziel Eliab only
**Product:** AzielTether
**Person @id:** https://www.azieleliab.com/#aziel
**Beside:** `COLD-COPY-SURVIVAL-1.0`, `REHEAL-1.0`, `SPLIT-THE-WIRES-1.0`
**Sister:** aziel-corpus `COLD-MULTI-SHELF-1.0` (export / verify / registry)
**Laws cited:** `CROSS-NETWORK-SURVIVAL-1.0`, `NO-LIE-NO-REWRITE-1.0`,
ingest-as-receipt, `RE-EXPAND-FROM-ARCHIVE`, `REHEAL`, `NO-FAN`

Coordinate with the corpus shelf by **citing the same lockset tip hashes**.
Do not fork Person @id `https://www.azieleliab.com/#aziel`.

## Why this exists

The counted download and hosted `/v1` live on a Cloudflare Worker. GitHub
is a source mirror. If both are yanked, hub tip/receipts must still be
on disk, on a USB, or on an operator-configured **non-Cloudflare** raw
URL. This is the tether path, not a second identity and not a VPN.

The Worker is **zero-retention**. It acknowledges hashes. It does not
store the chain. Claiming it holds durable tips after a yank is a lie.

## Operator planes

| Plane | What | Survives CF+GitHub yank? | State |
|-------|------|--------------------------|--------|
| **A** | Four product Workers on the **same** Cloudflare tunnel (`vibelock.workers.dev`): AzielTether, AZ-CLCE, TemporalLock, StaticClock | No. Same tunnel. | REAL probe + ingest-as-receipt on this product |
| **B** | Zenodo tip-pack | Yes, if a **real DOI** is set | **SLOT** until `AZIELTETHER_ZENODO_DOI` is a live `10.xxxx/zenodo.<id>`. No invented DOIs. |
| **C** | Last local cold-shelf + USB airgap | Yes | REAL. Optional non-GitHub forge *publish* is SLOT; raw HTTPS pull is REAL when the operator sets a URL |

Worker-up pulls **Plane A**. Worker-down serves last **Plane C**. Restore
reconciles by hash (never rewrite). Plane B is pulled only when a real
Zenodo DOI is LIVE **and** `AZIELTETHER_ZENODO_URL` (or `--zenodo-url`)
is a `zenodo.org` file. A URL without a live DOI stays SLOT. No invented
DOIs or CIDs.

```bash
azieltether shelf status --zenodo-doi 10.5281/zenodo.123456 \
  --zenodo-url https://zenodo.org/records/123456/files/manifest.json
azieltether shelf sync --zenodo-doi 10.5281/zenodo.123456 \
  --zenodo-url https://zenodo.org/records/123456/files/manifest.json \
  --sha256 <64 lowercase hex>
```

## Law

1. **Prefer Worker when up.** Probe `GET /v1/health`. Ingest-as-receipt
   (`POST /v1/ingest`, `POST /v1/tip`). Then seal tip + receipts into
   the local cold-shelf (`~/.azieltether/shelf/`).
2. **When Worker is dead, serve the last local cold copy.** Do not
   invent a tip. `RE-EXPAND-FROM-ARCHIVE` is that last sealed shelf.
3. **On restore, reconcile by hash.** Union merge. Dual-chain keeps both
   children of the same `prev_hash`. Never rewrite an existing item.
4. **Fetch/verify a SHA-256 manifest** from configurable URLs: local
   path, `file://`, GitLab raw, Codeberg raw, Zenodo file. Refuse on
   hash mismatch (`SHELF-HASH-MISMATCH`).
5. **No rewrite key. No lie-to-survive.** A yank does not authorize a
   historian. Votes cannot flip a broken digest. Neighbors cannot
   vote-to-fix (`REHEAL`).
6. **NO-FAN.** Unverified shelf bodies are not pushed to a crowd.
   Receiver pulls a verified shelf.

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
| HTTPS raw fetch | GET GitLab/Codeberg/Zenodo (or any https) + verify |
| USB airgap | `shelf usb` / `shelf usb-import` |
| Refuse rewrite key | `SHELF-REWRITE-REFUSED` |
| Refuse lie-to-survive | `SHELF-LIE-REFUSED` |
| Refuse hash mismatch | `SHELF-HASH-MISMATCH` |

**MOCK / SLOT (not implemented — refuse codes, never claimed live):**

| Slot | Refuse code | Honest note |
|------|-------------|-------------|
| Live multi-homed DNS | `SHELF-SLOT-MULTIHOME-DNS` | Not implemented |
| IPFS CIDs | `SHELF-SLOT-IPFS` | Do not invent a CID |
| Auto-publish to GitLab/Codeberg/Zenodo | `SHELF-SLOT-AUTO-PUBLISH` | Operator copies files |
| Anycast / geo-DNS | `SHELF-SLOT-ANYCAST` | Not implemented |
| AZ Generator | `SHELF-SLOT-AZ-GENERATOR` | MirageGrid-only; refused here |

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
azieltether shelf usb-import --src /media/usb/aziel-shelf
azieltether verify
```

Import refuses if `manifest.sha256` (or `--sha256`) does not match the
file bytes, or if the embedded canonical `sha256` does not match the
body. Existing local items are kept. Incoming verified hashes are
appended. Nothing is rewritten.

Optional non-Cloudflare pull (when those hosts are still up):

```bash
azieltether shelf pull \
  --url https://gitlab.com/<group>/<repo>/-/raw/<rev>/shelf/manifest.json \
  --sha256 <64 lowercase hex>
```

Same shape works for Codeberg raw and a Zenodo file URL. Set
`AZIELTETHER_SHELF_URLS` (comma-separated) for `shelf sync` to try
those mirrors whenever you pulse the shelf.

## Sync modes

| Mode | When | Action |
|------|------|--------|
| prefer-central | Worker `/v1/health` ok | Ingest-as-receipt, pull configured URLs, seal local |
| serve-last-local | Worker down or `AZIELTETHER_OFFLINE=1` | Serve `shelf/manifest.json`; still verify configured URLs if reachable |
| reconcile-on-restore | Worker returns after a recorded down | Hash union; seal; no rewrite |

`azieltether shelf sync` is the one command that walks that path.

## What this is not

Not a VPN. Not MirageGrid. Not AZ Generator. Not live multi-homed DNS.
Not an IPFS pinset. Not a claim that Cloudflare or GitHub will stay up.
Public HTTPS boards stay mesh-free.

Apache-2.0. Forks are welcome and always allowed.
