# COLD-COPY SURVIVAL

**Spec:** `COLD-COPY-SURVIVAL-1.0`
**Author:** Aziel Eliab only
**Product:** AzielTether
**Beside:** `SPLIT-THE-WIRES-1.0`

## Law

1. **Multiply cold copies.** After verify, write the sealed item to at
   least three local copy slots (`copies/0`, `copies/1`, `copies/2`).
2. **Refuse live body sync across the network.** The tick plane never
   carries a body. The gate plane is a cite/lockset pull of already
   verified hashes — not a live stream.
3. **A tip is expensive to erase.** No free delete. A tombstone needs
   operator + cite + lockset + 777s dwell. Bytes stay.
4. **Unkillable by a single-server pull.** An empty or hostile remote
   cannot drop local copies.
5. **Poison is hard.** Hash-absolute, fail-closed. Votes cannot flip a
   broken digest to yes.
6. **Data outlives creators.** Copies remain usable when the minting
   node is gone. No creator-keyed kill switch.

`azieltether survival` multiplies the local DAG into cold-copy slots.
`GET /v1/survival` returns the law card.
