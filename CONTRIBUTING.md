# Contributing to AzielTether

**Forks are first-class.** This project is Apache-2.0; you do not need
permission to fork, patch, or redistribute. Pull requests are welcome
if you want a change upstream.

**Forks are welcome and always allowed.**

Dual-chain forks are the same idea: two children of one `prev_hash` are
valid and detectable. Do not add code that picks a winner.

## How to run tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

Python 3.10+. Core is stdlib only. pytest is the dev extra.

## Ground rules

1. Public identity is **Aziel Eliab** only.
2. Do not add a VPN, onion routing, or claims that godlock.uk is meshed.
3. Do not allow edits of hashed items. Corrections are new items.
4. Dual-chain must keep both children. No consensus, mining, or tokens.
5. Hosted `/v1` must not increment DOWNLOADS KV and must not store chains.
6. **Door vs local op.** `/v1/mesh/*` PROXY to aziel-runtime. Local ops are `/v1/{op}` only.
   Suite mesh default OFF; QNM rollup live|locked|isolated; QNS-CD-1.0 is a
   hub cite / Worker mesh cross-map only (no public qnsd proxy; not a
   Softwares-tab product); no Node Gate; no auto-heal; not anonymity.
7. New behavior needs a test that fails without the change.
8. **SPLIT THE WIRES.** Tick plane is presence + tip only. Payload is
   receiver-pull on a distinct 777s gate socket. No shared socket.
   Equivocation isolates. Quorum cannot outvote a broken hash.
9. **COLD-COPY SURVIVAL.** Multiply cold copies. Refuse live body sync.
   Tips are expensive to erase. Single-server pull cannot kill local
   copies. Hash-absolute. Data outlives creators.
10. **REHEAL.** Own last good tip + verified trusted pull or
    phoenix-WAIT. No neighbor vote-to-fix. Chatter is
    live/locked/isolated/tip-hash only.
11. **COLD-SHELF TETHER.** Worker-up pulls Plane A. Worker-down serves
    last Plane C local shelf. Restore is hash reconcile — never rewrite.
    Plane B SLOT until hash-verify on Codeberg / archive.org / GitFlic
    (not Zenodo; do not invent a DOI). Plane C USB tip-pack LIVE only
    after `sha256sum -c` plus operator attest (`CNS-OPERATOR-ATTEST`
    until then). No rewrite key. No lie-to-survive. Do not claim live
    multi-homed DNS or invent IPFS CIDs. Person @id stays
    https://www.azieleliab.com/#aziel.

## Where to change things

- Isolated counter: `workers/download-tracker/`
- Suite mesh / QNM Live Nodes + QNS-CD-1.0 cross-map: `workers/download-tracker/src/mesh.js` (`/v1/mesh/*` PROXY to aziel-runtime).
- SPLIT THE WIRES + COLD-COPY SURVIVAL: `azieltether/wires.py`, `azieltether/survival.py`, `workers/download-tracker/src/wires.js`.
- REHEAL: `azieltether/reheal.py` (own tip + trusted pull or phoenix-WAIT).
- COLD-SHELF TETHER: `azieltether/shelf.py` (local seal, HTTPS+SHA-256
  fetch, USB airgap). Worker law card: `GET /v1/shelf`.

## License of contributions

By submitting a change you agree it is licensed under Apache-2.0.
