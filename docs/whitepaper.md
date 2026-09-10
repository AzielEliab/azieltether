# AzielTether

**A central × decentral software tether**

Aziel Eliab
September 2026
License: Apache-2.0
Version: 0.1.0
Spec: `azieltether-v0`

> Prefer central. Peer when down. Reconcile on restore.

## Abstract

AzielTether is open-source node-mesh **software** that prefers a central
Cloudflare Worker when that Worker is healthy, syncs hash-chained work
between downloaded nodes when the Worker is down, and reconciles both
sides when the Worker returns. Same-`prev_hash` conflicts become a
**dual-chain**: both children are kept. No winner is elected.

Lattice tips (last-known hashes) can be carried across GodLock, the
Aziel Digital Library, and product Workers so a node that loses one
surface still has a surviving tip. Public HTTPS boards stay mesh-free.
The tether lives in the downloaded software.

This is not a VPN. It is not MirageGrid. It is not a kernel.

## 1. Purpose

Sibling Aziel Eliab products already write hash-chained queue items
when they cannot reach their Worker (AZ-CLCE:
`~/.az-clce/tether-queue.jsonl`). AzielTether is the product that
**batches, peers, and reconciles** those items — plus its own work
items — under one protocol.

Design goals:

1. **Prefer central.** `GET /v1/health` decides the mode.
2. **Do not drop work.** Offline append is always allowed.
3. **Do not pick a winner.** Dual-chain on same-hash-parent conflict.
4. **Do not mesh the public boards.** godlock.uk and the library stay
   ordinary HTTPS. Tips are receipts a downloaded node can carry.
5. **Do not build a VPN.** Routing and anonymity belong to MirageGrid.

## 2. Item

Canonical encoding: UTF-8 JSON, sorted keys, no extra whitespace.
`hash` is SHA-256 of that encoding **excluding** `hash` itself.
Genesis `prev_hash` is 64 zero hex characters.

Native fields: `created_at`, `engine_version`, `kind`, `node_id`,
`payload`, `prev_hash`, `report_hash`, `scope`.

AZ-CLCE / SPRE items (`scope` `az-clce` or `spre`) verify under the
same hash contract and are harvested, not rewritten.

## 3. Modes

| Mode | When | Action |
|------|------|--------|
| prefer-central | Worker `/v1/health` ok | POST unpublished items to `/v1/ingest` |
| peer-sync-when-down | health fail or `AZIELTETHER_OFFLINE=1` | Exchange items with peer URLs |
| reconcile-on-restore | central returns | Merge DAG, push unpublished, refresh tips |

Hosted `/v1` is **stateless** and **zero-retention**. It acknowledges
hashes. It does not store chains. It does not increment download KV.

The Worker homepage shows a suite Live Nodes strip. `/v1/mesh/*` PROXY
to aziel-runtime. Suite mesh default OFF. QNM rollup is
live|locked|isolated counts only. No Node Gate. No auto-heal. Not an
anonymity network. Anon-broadcast is not a publish path. AzielTether
remains a software tether. Public HTTPS boards stay mesh-free.

## 4. Dual-chain

If item A and item B share `prev_hash` and differ in `hash`, both stay.
Verification walks a DAG. Linear sibling queues remain valid when stored
separately. Combined views report the fork and do not elect a historian.

## 5. Lattice tips

A tip is `{surface, tip_hash, prev_hash, node_id, created_at, hash}`.
Surfaces: `worker`, `godlock`, `corpus`, `az-clce`, `temporallock`,
`staticclock`, `peer`. Publishing a tip is not meshing the surface.

## 6. What this is not

Not a VPN. Not MirageGrid. Not a kernel. Not a truth score. Not a
backdoor onto godlock.uk or the library. Not Horton. Not Altman.
Author: Aziel Eliab.

Forks are welcome and always allowed.
