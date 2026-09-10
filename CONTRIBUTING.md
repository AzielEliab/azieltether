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

## Where to change things

- Isolated counter: `workers/download-tracker/`
- Suite mesh / QNM Live Nodes + QNS-CD-1.0 cross-map: `workers/download-tracker/src/mesh.js` (`/v1/mesh/*` PROXY to aziel-runtime).

## License of contributions

By submitting a change you agree it is licensed under Apache-2.0.
