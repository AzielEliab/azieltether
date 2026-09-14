# SPLIT THE WIRES

**Spec:** `SPLIT-THE-WIRES-1.0`
**Author:** Aziel Eliab only
**Product:** AzielTether

Two planes. Two sockets. Never one wire.

## Tick plane (0.5–1s)

Presence + tip hash only. Fixed-size frame (256 bytes). No body, diff,
or file. The 1s loop uses the `tick` socket.

## Payload plane (777s gate)

The receiver pulls. The sender never push-fans a body. Update is proof
(cite `prev` + lockset), not a timer. After a valid cite, dwell 777s.
Clock desync is not yes. An ambiguous tip isolates.

## Equivocation

Same peer, same prev, two tips → lock/isolate that peer. Quorum cannot
outvote a broken hash. Dual-chain DAG forks from distinct nodes stay.

## Emit / Phoenix / unsend

Emit last locally after verify. Phoenix is local to the failed node
only. No unsend of an unverified body.

## Partition

Split brain does not auto-splice. Rejoin needs cite + operator/lockset.
Heartbeat loss is not poison and does not apply the last packet.

## Sockets

The 1s loop and the 777s gate never share a socket.

Local doors: `POST /api/tick`, `POST /api/payload`.
Hosted: `GET /v1/wires`, `POST /v1/wires/tick`, `POST /v1/wires/payload`.
