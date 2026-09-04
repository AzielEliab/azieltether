# Contributing to AzielTether

**Forks are first-class.** This project is Apache-2.0; you do not need
permission to fork, patch, or redistribute.

**Forks are welcome and always allowed.**

Author credit stays **Aziel Eliab**.

## How to run tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

Python 3.10+. Core needs `cryptography` for Ed25519. pytest is the dev extra.

## Ground rules

1. **This is a content/work tether, not a VPN.** Do not add onion routing, SOCKS, or anonymity features.
2. **Public HTTPS boards stay mesh-free.** Do not POST mesh batches at `godlock.uk` or the Corpus library UI.
3. **The Worker is a bootstrap directory + holding pen**, not a full mesh. Do not claim otherwise.
4. **`aziel-corpus` is public ingest envelopes only.** Refuse operator Aziel Library writes on the peer path.
5. **Verify hash-chain + Ed25519 on accept.** Never store a batch that fails verify.
6. **UI / serve bind loopback only** (`127.0.0.1`). Do not listen on `0.0.0.0`.
7. **Keep `/download` HTTP 200 gzip** (no 302 to GitHub). Isolated KV `AZIELTETHER_DOWNLOADS`.
8. **No secrets in git.** Node private keys stay in `$AZIELTETHER_HOME` / `~/.azieltether`.
9. New behavior needs a test that fails without the change.

## Where to change things

- Hash-chain / Ed25519: `azieltether/chain.py`, `azieltether/crypto.py`
- Prefer-central / fallback / reconcile: `azieltether/router.py`
- Local store: `azieltether/store.py`
- CLI: `azieltether/cli.py`
- Loopback UI: `azieltether/serve.py`
- Protocol: `docs/PROTOCOL.md`
- Worker: `workers/download-tracker/`

## License of contributions

By submitting a change you agree it is licensed under Apache-2.0, the
same license as the rest of the tree.
