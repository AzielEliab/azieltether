/**
 * SPLIT THE WIRES + COLD-COPY SURVIVAL — Worker mesh law.
 * Tick plane: presence + tip hash only. Fixed-size. No body.
 * Payload plane: receiver pull. Never sender push fan-out.
 * 1s loop and 777s gate never share a socket.
 * Multiply cold copies. Refuse live body sync. Tip expensive to erase.
 * Unkillable by single-server pull. Hash-absolute fail-closed.
 * Data outlives creators.
 * REHEAL: own last good tip + verified trusted pull or phoenix-WAIT.
 * No neighbor vote-to-fix. Chatter: live/locked/isolated/tip-hash only.
 * Author: Aziel Eliab only.
 */

export const WIRES_SPEC = "SPLIT-THE-WIRES-1.0";
export const SURVIVAL_SPEC = "COLD-COPY-SURVIVAL-1.0";
export const WIRES_AUTHOR = "Aziel Eliab";
export const TICK_MIN_MS = 500;
export const TICK_MAX_MS = 1000;
export const GATE_DWELL_S = 777;
export const TICK_SOCKET = "tick";
export const GATE_SOCKET = "gate";
export const PLANE_TICK = "tick";
export const PLANE_PAYLOAD = "payload";
export const TICK_FRAME_BYTES = 256;
export const TICK_MAGIC = "ATW1";
export const MIN_COLD_COPIES = 3;
export const PUSH_FANOUT = false;
export const AUTO_SPLICE = false;
export const CLOCK_DESYNC_IS_YES = false;
export const QUORUM_OUTVOTES_HASH = false;
export const LIVE_BODY_SYNC = false;
export const TIP_ERASE_FREE = false;
export const SINGLE_SERVER_CAN_KILL = false;
export const HASH_ABSOLUTE = true;
export const OUTLIVES_CREATORS = true;
export const REHEAL_SPEC = "REHEAL-1.0";
export const SHELF_SPEC = "COLD-SHELF-TETHER-1.0";
export const SISTER_SHELF_SPEC = "COLD-MULTI-SHELF-1.0";
export const CROSS_NETWORK_SPEC = "CROSS-NETWORK-SURVIVAL-1.0";
export const NO_LIE_SPEC = "NO-LIE-NO-REWRITE-1.0";
export const PERSON_ID = "https://www.azieleliab.com/#aziel";
export const NEIGHBOR_VOTE_TO_FIX = false;
export const ALLOWED_CHATTER = Object.freeze(["live", "locked", "isolated", "tip_hash"]);
export const PHOENIX_WAIT = "phoenix-WAIT";

const TICK_FORBIDDEN = new Set([
  "body", "payload", "diff", "file", "items", "data", "blob", "content", "chain",
]);

export const WIRES_LAW =
  "SPLIT THE WIRES. Fast 0.5–1s tick: presence + tip hash only. Fixed-size. No body/diff/file on the tick plane. Payload on the second plane the receiver pulls — never sender push fan-out. Update is proof not timer: cite prev + lockset, fail-closed; 777s dwell after valid cite; clock desync is not yes; ambiguous tip isolates. Equivocation ends the peer. Quorum cannot outvote a broken hash. Emit last locally after verify. Phoenix local to the failed node only. No unsend unverified body. Split brain does not auto-splice. Heartbeat loss is not poison and does not apply the last packet. The 1s loop and the 777s gate never share a socket. Author: Aziel Eliab only.";

export const SURVIVAL_LAW =
  "COLD-COPY SURVIVAL. Multiply cold copies. Refuse live body sync across the network. A tip is expensive to erase. Unkillable by a single-server pull. Poison is hard: hash-absolute, fail-closed. Data outlives creators. Author: Aziel Eliab only.";

export const REHEAL_LAW =
  "REHEAL. Heal from your own last good tip plus a verified trusted pull, or phoenix-WAIT. No neighbor vote-to-fix. Allowed chatter is live / locked / isolated / tip-hash only. Author: Aziel Eliab only.";

export const SHELF_LAW =
  "COLD-SHELF TETHER. Prefer Worker when up: probe + ingest-as-receipt, then seal tip+receipts locally. When Worker is dead, serve the last local cold-shelf. On restore, reconcile by hash — never rewrite. Fetch/verify a SHA-256 manifest from operator URLs. Hash mismatch refuses. No rewrite key. No lie-to-survive. Multi-homed DNS, IPFS CIDs, auto-publish, anycast, and AZ Generator are MOCK/SLOT. Sister: aziel-corpus COLD-MULTI-SHELF-1.0. Person @id https://www.azieleliab.com/#aziel. Author: Aziel Eliab only.";

export const SHELF_SLOTS = Object.freeze({
  multihome_dns: "SHELF-SLOT-MULTIHOME-DNS",
  ipfs: "SHELF-SLOT-IPFS",
  auto_publish: "SHELF-SLOT-AUTO-PUBLISH",
  anycast: "SHELF-SLOT-ANYCAST",
  az_generator: "SHELF-SLOT-AZ-GENERATOR",
  zenodo_doi: "SHELF-SLOT-ZENODO-DOI",
  forge_publish: "SHELF-SLOT-FORGE-PUBLISH",
});

function hex64(name, value) {
  const text = String(value || "").trim().toLowerCase();
  if (text.length !== 64 || /[^0-9a-f]/.test(text)) {
    throw new Error(name + " must be 64 lowercase hex characters");
  }
  return text;
}

export function tickIntervalOk(ms) {
  const n = Number(ms);
  return Number.isFinite(n) && n >= TICK_MIN_MS && n <= TICK_MAX_MS;
}

export function bindSocket(plane) {
  if (plane === PLANE_TICK) return TICK_SOCKET;
  if (plane === PLANE_PAYLOAD) return GATE_SOCKET;
  throw new Error("unknown plane");
}

export function assertDistinctSockets(tickSocket, gateSocket) {
  if (!tickSocket || !gateSocket || tickSocket === gateSocket) {
    throw new Error("1s loop and 777s gate never share a socket");
  }
}

export function assertPlaneSocket(plane, socket) {
  const expected = bindSocket(plane);
  if (socket !== expected) {
    throw new Error(plane + " plane must use the " + expected + " socket");
  }
}

export function hashHolds(digestOk, votesFor = 0) {
  if (QUORUM_OUTVOTES_HASH) return Boolean(digestOk) || votesFor > 0;
  return Boolean(digestOk);
}

export function tickForbidden(body) {
  if (!body || typeof body !== "object") return [];
  return Object.keys(body).filter((k) => TICK_FORBIDDEN.has(String(k).toLowerCase()));
}

export function refusePushFanout(body) {
  const items = body && (body.items || body.payload || body.body);
  if (items && (Array.isArray(items) ? items.length : true)) {
    return {
      ok: false,
      code: "WIRES-PUSH-REFUSED",
      push_fanout: false,
      note: "Receiver pulls. Sender never push-fans a body.",
      author: WIRES_AUTHOR,
    };
  }
  return { ok: true, code: "WIRES-NO-PUSH", push_fanout: false, author: WIRES_AUTHOR };
}

export function refuseLiveBodySync(body, plane, verified = false) {
  const items = body && (body.items || body.body || body.payload);
  const has = items && (Array.isArray(items) ? items.length : true);
  if (LIVE_BODY_SYNC) return { ok: true, code: "SURVIVAL-LIVE-OK", author: WIRES_AUTHOR };
  if ((plane === "tick" && has) || (has && !verified)) {
    return {
      ok: false,
      code: "SURVIVAL-LIVE-BODY-REFUSED",
      note: "Refuse live body sync across the network. Cold copies are local.",
      author: WIRES_AUTHOR,
    };
  }
  return { ok: true, code: "SURVIVAL-COLD-ONLY", live_body_sync: false, author: WIRES_AUTHOR };
}

export function citeOk(cite, lockset) {
  try {
    hex64("cite", cite);
    hex64("lockset", lockset);
    return true;
  } catch {
    return false;
  }
}

export function dwellReady(citedAt, now, dwellS = GATE_DWELL_S) {
  if (CLOCK_DESYNC_IS_YES) return true;
  if (now < citedAt) return false;
  return (now - citedAt) >= dwellS;
}

export function applyUpdate({ cite, lockset, citedAt, now, tipHashes, digestOk = true, votesFor = 0, dwellS = GATE_DWELL_S }) {
  if (!citeOk(cite, lockset)) {
    return { ok: false, code: "WIRES-CITE-REQUIRED", applied: false, author: WIRES_AUTHOR };
  }
  if (!hashHolds(digestOk, votesFor)) {
    return { ok: false, code: "WIRES-HASH-ABSOLUTE", applied: false, author: WIRES_AUTHOR };
  }
  const tips = [...new Set((tipHashes || []).filter(Boolean))];
  if (tips.length > 1) {
    return { ok: false, code: "WIRES-AMBIGUOUS-TIP", applied: false, isolate: true, author: WIRES_AUTHOR };
  }
  if (!dwellReady(citedAt, now, dwellS)) {
    return { ok: false, code: "WIRES-DWELL", applied: false, author: WIRES_AUTHOR };
  }
  return { ok: true, code: "WIRES-APPLY", applied: true, author: WIRES_AUTHOR };
}

export function detectEquivocation(ticks) {
  const by = {};
  for (const raw of ticks || []) {
    const node = String(raw.node_id || "");
    const prev = String(raw.prev_hash || raw.cite || "");
    const tip = String(raw.tip_hash || raw.hash || "");
    if (!node || !prev || !tip) continue;
    const key = node + ":" + prev;
    if (!by[key]) by[key] = { node_id: node, prev_hash: prev, tip_hashes: [] };
    if (!by[key].tip_hashes.includes(tip)) by[key].tip_hashes.push(tip);
  }
  return Object.values(by).filter((f) => f.tip_hashes.length > 1);
}

export function onHeartbeatLoss() {
  return {
    ok: true,
    code: "WIRES-HEARTBEAT-LOSS",
    poison: false,
    apply_last_packet: false,
    isolate: false,
    author: WIRES_AUTHOR,
  };
}

export function partitionRejoin({ cite, lockset, operator }) {
  if (AUTO_SPLICE) return { ok: true, code: "WIRES-AUTO-SPLICE", author: WIRES_AUTHOR };
  if (citeOk(cite, lockset) && operator) {
    return { ok: true, code: "WIRES-REJOIN", author: WIRES_AUTHOR };
  }
  return { ok: false, code: "WIRES-NO-AUTO-SPLICE", isolate: true, author: WIRES_AUTHOR };
}

export function singleServerPull(localHashes, remoteHashes) {
  if (SINGLE_SERVER_CAN_KILL) return { ok: false, local: [], author: WIRES_AUTHOR };
  return {
    ok: true,
    code: "SURVIVAL-UNKILLABLE",
    local: [...(localHashes || [])],
    remote: [...(remoteHashes || [])],
    dropped: [],
    unkillable: true,
    author: WIRES_AUTHOR,
  };
}

export function eraseTip({ operator, lockset, cite, dwellIsReady }) {
  if (TIP_ERASE_FREE) return { ok: true, code: "SURVIVAL-TIP-ERASED", author: WIRES_AUTHOR };
  if (!(operator && citeOk(cite, lockset) && dwellIsReady)) {
    return {
      ok: false,
      code: "SURVIVAL-TIP-EXPENSIVE",
      erased: false,
      note: "tip expensive to erase: need operator + cite + lockset + 777s dwell",
      author: WIRES_AUTHOR,
    };
  }
  return { ok: true, code: "SURVIVAL-TIP-TOMBSTONE", erased: false, tombstone: true, author: WIRES_AUTHOR };
}

export function acceptTick(body, socket = TICK_SOCKET) {
  try {
    assertPlaneSocket(PLANE_TICK, socket);
  } catch (err) {
    return { ok: false, code: "WIRES-SOCKET", error: String(err.message || err), author: WIRES_AUTHOR };
  }
  if (tickForbidden(body).length) {
    return { ok: false, code: "WIRES-TICK-BODY", note: "no body/diff/file on the tick plane", author: WIRES_AUTHOR };
  }
  let nodeId;
  let tipHash;
  try {
    nodeId = hex64("node_id", body && body.node_id);
    tipHash = hex64("tip_hash", body && body.tip_hash);
  } catch {
    return { ok: false, code: "WIRES-AMBIGUOUS-TIP", isolate: true, author: WIRES_AUTHOR };
  }
  return {
    ok: true,
    code: "WIRES-TICK",
    plane: PLANE_TICK,
    socket: TICK_SOCKET,
    spec: WIRES_SPEC,
    node_id: nodeId,
    tip_hash: tipHash,
    frame_bytes: TICK_FRAME_BYTES,
    items: [],
    author: WIRES_AUTHOR,
  };
}

export function acceptPayload(body, socket = GATE_SOCKET) {
  try {
    assertPlaneSocket(PLANE_PAYLOAD, socket);
  } catch (err) {
    return { ok: false, code: "WIRES-SOCKET", error: String(err.message || err), author: WIRES_AUTHOR };
  }
  const live = refuseLiveBodySync(body, PLANE_PAYLOAD, false);
  if (body && (body.items || body.payload || body.body)) {
    return { ok: false, code: live.code || "SURVIVAL-LIVE-BODY-REFUSED", items: [], author: WIRES_AUTHOR };
  }
  if (!citeOk(body && body.cite, body && body.lockset)) {
    return { ok: false, code: "WIRES-CITE-REQUIRED", items: [], author: WIRES_AUTHOR };
  }
  return {
    ok: true,
    code: "WIRES-PULL",
    plane: PLANE_PAYLOAD,
    socket: GATE_SOCKET,
    spec: WIRES_SPEC,
    cite: String(body.cite).toLowerCase(),
    lockset: String(body.lockset).toLowerCase(),
    items: [],
    pull: true,
    push_fanout: false,
    live_body_sync: false,
    survival: singleServerPull([], body.want || []),
    author: WIRES_AUTHOR,
  };
}

export function chatterAllowed(body) {
  if (!body || typeof body !== "object") return true;
  return Object.keys(body).every((k) => {
    const name = (k === "tip-hash") ? "tip_hash" : k;
    return ALLOWED_CHATTER.includes(name);
  });
}

export function refuseVoteToFix(votesFor = 0, neighborFix) {
  if (NEIGHBOR_VOTE_TO_FIX) return { ok: true, code: "REHEAL-VOTE-OK", author: WIRES_AUTHOR };
  if (votesFor || neighborFix) {
    return {
      ok: false,
      code: "REHEAL-VOTE-REFUSED",
      applied: false,
      wait: PHOENIX_WAIT,
      note: "No neighbor vote-to-fix.",
      author: WIRES_AUTHOR,
    };
  }
  return { ok: true, code: "REHEAL-NO-VOTE", author: WIRES_AUTHOR };
}

export function decideReheal({ ownTip, cite, lockset, digestOk = false, votesFor = 0, neighborFix, chatter }) {
  if (chatter && !chatterAllowed(chatter)) {
    return { ok: false, code: "REHEAL-CHATTER", wait: PHOENIX_WAIT, author: WIRES_AUTHOR };
  }
  const vote = refuseVoteToFix(votesFor, neighborFix);
  if (!vote.ok) return vote;
  if (ownTip && citeOk(cite, lockset) && digestOk && String(cite).toLowerCase() === String(ownTip).toLowerCase()) {
    return { ok: true, code: "REHEAL-TRUSTED-PULL", applied: true, own_tip: ownTip, wait: false, author: WIRES_AUTHOR };
  }
  return {
    ok: true,
    code: "REHEAL-PHOENIX-WAIT",
    applied: false,
    own_tip: ownTip || null,
    wait: PHOENIX_WAIT,
    author: WIRES_AUTHOR,
  };
}

export function wiresCard() {
  return {
    ok: true,
    spec: WIRES_SPEC,
    survival_spec: SURVIVAL_SPEC,
    product: "azieltether",
    author: WIRES_AUTHOR,
    identity: WIRES_AUTHOR,
    tick_ms: [TICK_MIN_MS, TICK_MAX_MS],
    gate_dwell_s: GATE_DWELL_S,
    tick_frame_bytes: TICK_FRAME_BYTES,
    sockets: { tick: TICK_SOCKET, gate: GATE_SOCKET, shared: false },
    planes: [PLANE_TICK, PLANE_PAYLOAD],
    push_fanout: PUSH_FANOUT,
    auto_splice: AUTO_SPLICE,
    clock_desync_is_yes: CLOCK_DESYNC_IS_YES,
    quorum_outvotes_hash: QUORUM_OUTVOTES_HASH,
    min_cold_copies: MIN_COLD_COPIES,
    live_body_sync: LIVE_BODY_SYNC,
    tip_erase_free: TIP_ERASE_FREE,
    single_server_can_kill: SINGLE_SERVER_CAN_KILL,
    hash_absolute: HASH_ABSOLUTE,
    outlives_creators: OUTLIVES_CREATORS,
    law: WIRES_LAW,
    survival_law: SURVIVAL_LAW,
    reheal_spec: REHEAL_SPEC,
    reheal_law: REHEAL_LAW,
    shelf_spec: SHELF_SPEC,
    shelf_law: SHELF_LAW,
    sister_shelf_spec: SISTER_SHELF_SPEC,
    cross_network: CROSS_NETWORK_SPEC,
    no_lie: NO_LIE_SPEC,
    person_id: PERSON_ID,
    neighbor_vote_to_fix: NEIGHBOR_VOTE_TO_FIX,
    allowed_chatter: ALLOWED_CHATTER.slice(),
    phoenix: PHOENIX_WAIT,
  };
}

export function attachWires(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return data;
  return {
    ...data,
    wires_spec: WIRES_SPEC,
    survival_spec: SURVIVAL_SPEC,
    reheal_spec: REHEAL_SPEC,
    shelf_spec: SHELF_SPEC,
    allowed_chatter: ALLOWED_CHATTER.slice(),
    neighbor_vote_to_fix: NEIGHBOR_VOTE_TO_FIX,
    wires: {
      tick_ms: [TICK_MIN_MS, TICK_MAX_MS],
      gate_dwell_s: GATE_DWELL_S,
      sockets: { tick: TICK_SOCKET, gate: GATE_SOCKET, shared: false },
      push_fanout: PUSH_FANOUT,
      auto_splice: AUTO_SPLICE,
      live_body_sync: LIVE_BODY_SYNC,
      min_cold_copies: MIN_COLD_COPIES,
      hash_absolute: HASH_ABSOLUTE,
      outlives_creators: OUTLIVES_CREATORS,
      single_server_can_kill: SINGLE_SERVER_CAN_KILL,
      tip_erase_free: TIP_ERASE_FREE,
    },
  };
}

export function shelfCard() {
  return {
    ok: true,
    spec: SHELF_SPEC,
    sister_spec: SISTER_SHELF_SPEC,
    cross_network: CROSS_NETWORK_SPEC,
    no_lie: NO_LIE_SPEC,
    product: "azieltether",
    author: WIRES_AUTHOR,
    identity: WIRES_AUTHOR,
    person_id: PERSON_ID,
    durable_store: false,
    zero_retention: true,
    worker_holds_chain: false,
    rewrite_key: false,
    lie_to_survive: false,
    fan: false,
    multihome_dns: false,
    ipfs: false,
    auto_publish: false,
    anycast: false,
    az_generator: false,
    planes: {
      A: { plane: "A", hubs: 4, same_tunnel: true, survives_cf_yank: false, live: true },
      B: { plane: "B", name: "zenodo-tip-pack", live: false, slot: "SHELF-SLOT-ZENODO-DOI" },
      C: { plane: "C", name: "usb-local-cold-copy", live: true, survives_cf_yank: true },
    },
    slots: Object.fromEntries(Object.entries(SHELF_SLOTS).map(([k, v]) => [k, { code: v, live: false }])),
    law: SHELF_LAW,
  };
}

export function refuseShelfSlot(name) {
  const key = String(name || "").trim().toLowerCase().replace(/-/g, "_").replace(/ /g, "_");
  const aliases = { dns: "multihome_dns", ipfs_cid: "ipfs", cid: "ipfs", publish: "auto_publish", azgenerator: "az_generator" };
  const slot = aliases[key] || key;
  const code = SHELF_SLOTS[slot] || "SHELF-SLOT-UNKNOWN";
  return {
    ok: false,
    code,
    slot,
    live: false,
    mock: true,
    applied: false,
    author: WIRES_AUTHOR,
    person_id: PERSON_ID,
    note: "MOCK/SLOT. Not live. Do not invent multi-homed DNS or IPFS CIDs.",
  };
}

export function refuseRewriteKey(body) {
  const data = body && typeof body === "object" ? body : {};
  const keys = ["rewrite_key", "rewrite", "replace_hash", "historian_key", "lie_key", "survive_key"];
  const hit = keys.filter((k) => data[k]);
  if (hit.length) {
    return {
      ok: false,
      code: "SHELF-REWRITE-REFUSED",
      keys: hit,
      applied: false,
      author: WIRES_AUTHOR,
      law: NO_LIE_SPEC,
      note: "No rewrite key. Corrections are new items.",
    };
  }
  return { ok: true, code: "SHELF-NO-REWRITE", rewrite_key: false, author: WIRES_AUTHOR };
}

export function refuseLieToSurvive(body) {
  const data = body && typeof body === "object" ? body : {};
  if (data.rewrite_to_survive || data.worker_holds_chain || data.ipfs_live || data.multihome_dns || data.anycast) {
    return {
      ok: false,
      code: "SHELF-LIE-REFUSED",
      applied: false,
      author: WIRES_AUTHOR,
      law: NO_LIE_SPEC,
      note: "No lie-to-survive. Worker is zero-retention. Slots stay MOCK.",
    };
  }
  if (data.worker_up === true && data.worker_actually_up === false) {
    return {
      ok: false,
      code: "SHELF-LIE-REFUSED",
      applied: false,
      author: WIRES_AUTHOR,
      note: "Cannot claim Worker is up when the probe failed.",
    };
  }
  return { ok: true, code: "SHELF-HONEST", author: WIRES_AUTHOR, law: NO_LIE_SPEC };
}
