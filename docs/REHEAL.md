# REHEAL

**Spec:** `REHEAL-1.0`
**Author:** Aziel Eliab only
**Product:** AzielTether
**Beside:** `SPLIT-THE-WIRES-1.0`, `COLD-COPY-SURVIVAL-1.0`

## Law

1. **Heal from your own last good tip.** Walk the local DAG fail-closed.
   The last item whose hash and prev hold is the tip. Poison stops the
   walk.
2. **Then a verified trusted pull, or phoenix-WAIT.** A trusted pull
   cites that own tip plus a lockset. Hash-absolute. If there is no
   such pull, wait. Do not invent. Do not apply the last packet.
3. **No neighbor vote-to-fix.** Quorum, majority, or "please adopt this
   hash" cannot reheal you. Votes are refused.
4. **Allowed chatter** is `live` / `locked` / `isolated` / `tip-hash`
   only — the same counts the suite mesh already publishes, plus a tip
   hash on the tick plane. No body on chatter.

Phoenix is local to the failed node (`phoenix-WAIT`). Neighbors do not
phoenix you.

Local: `azieltether reheal`, `POST /api/reheal`.
Hosted: `GET /v1/reheal`, `POST /v1/reheal`.
