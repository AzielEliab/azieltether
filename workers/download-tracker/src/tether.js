/**
 * AzielTether bootstrap APIs.
 * Peer directory + batch holding pen. Not a full mesh.
 * Author: Aziel Eliab.
 */

const SCOPES = new Set(["godlock", "aziel-corpus", "aziel-runtime", "lattice", "precedent"]);
const FORBIDDEN_KINDS = new Set([
  "library_operator",
  "operator_record",
  "aziel_library_write",
  "operator_write",
]);
const PEER_TTL_MS = 72 * 60 * 60 * 1000;
const BATCH_LIMIT = 400;
const GENESIS = "0".repeat(64);

export function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

export function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders() },
  });
}

function canonicalJson(value) {
  if (value === null) return "null";
  const t = typeof value;
  if (t === "boolean") return value ? "true" : "false";
  if (t === "number") return Number.isFinite(value) ? JSON.stringify(value) : "null";
  if (t === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonicalJson).join(",") + "]";
  if (t === "object") {
    const keys = Object.keys(value).sort();
    return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalJson(value[k])).join(",") + "}";
  }
  throw new Error("cannot canonicalize");
}

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function requireHex64(name, value) {
  if (typeof value !== "string") throw new Error(`${name} must be a string`);
  const text = value.trim().toLowerCase();
  if (text.length !== 64 || /[^0-9a-f]/.test(text)) {
    throw new Error(`${name} must be 64 lowercase hex characters`);
  }
  return text;
}

function b64ToBytes(text) {
  const bin = atob(text);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i);
  return out;
}

function signingBody(batch) {
  return {
    batch_id: batch.batch_id,
    created_at: batch.created_at,
    kind: batch.kind,
    node_id: batch.node_id,
    payload: batch.payload == null ? {} : batch.payload,
    prev_hash: batch.prev_hash,
    product: batch.product || "azieltether",
    pubkey: batch.pubkey,
    scope: batch.scope,
    version: batch.version || "0.1.0",
  };
}

function isOperatorLibraryWrite(batch) {
  if (FORBIDDEN_KINDS.has(String(batch.kind || ""))) return true;
  if (batch.scope !== "aziel-corpus") return false;
  const payload = batch.payload && typeof batch.payload === "object" ? batch.payload : {};
  if (payload.operator === true || payload.operator_record === true) return true;
  const role = String(payload.library_role || payload.role || "").toLowerCase();
  return role === "operator" || role === "aziel_library_operator" || role === "library_operator";
}

async function verifyBatch(batch) {
  if (!batch || typeof batch !== "object") throw new Error("batch must be an object");
  if (!SCOPES.has(batch.scope)) throw new Error("unknown scope");
  const kinds = {
    godlock: "receipt",
    "aziel-corpus": "ingest_envelope",
    "aziel-runtime": "catalog_event",
    lattice: "anchor",
    precedent: "conflict_receipt",
  };
  if (batch.kind !== kinds[batch.scope]) throw new Error("kind is not allowed for scope");
  if (isOperatorLibraryWrite(batch)) {
    throw new Error("refused: Aziel Library operator records are not allowed on the peer/tether path");
  }
  requireHex64("prev_hash", batch.prev_hash);
  const digest = await sha256Hex(canonicalJson(signingBody(batch)));
  if (String(batch.hash || "").toLowerCase() !== digest) throw new Error("hash mismatch");
  if (typeof batch.pubkey !== "string" || typeof batch.signature !== "string") {
    throw new Error("pubkey and signature are required");
  }
  const key = await crypto.subtle.importKey("raw", b64ToBytes(batch.pubkey), { name: "Ed25519" }, false, ["verify"]);
  const ok = await crypto.subtle.verify(
    "Ed25519",
    key,
    b64ToBytes(batch.signature),
    new TextEncoder().encode(digest),
  );
  if (!ok) throw new Error("Ed25519 signature failed");
  return batch;
}

function peerKey(product, nodeId) {
  return `tether:peer:${product}:${nodeId}`;
}

function indexKey(scope) {
  return `tether:index:${scope}`;
}

function batchKey(scope, digest) {
  return `tether:batch:${scope}:${digest}`;
}

async function readJson(env, key, fallback) {
  const raw = await env.TETHER.get(key);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

async function listRecentPeers(env, product) {
  const products = product && product !== "*" ? [product] : [...SCOPES];
  const now = Date.now();
  const out = [];
  for (const scope of products) {
    const prefix = `tether:peer:${scope}:`;
    let cursor;
    do {
      const page = await env.TETHER.list(cursor ? { prefix, cursor } : { prefix });
      for (const item of page.keys) {
        const rec = await readJson(env, item.name, null);
        if (!rec || !rec.seen_at) continue;
        if (now - Number(rec.seen_at) > PEER_TTL_MS) continue;
        out.push(rec);
      }
      cursor = page.list_complete ? undefined : page.cursor;
    } while (cursor);
  }
  out.sort((a, b) => Number(b.seen_at) - Number(a.seen_at));
  return out.slice(0, 100);
}

export async function handleTetherApi(request, url, env) {
  const path = url.pathname.replace(/\/+$/, "") || "/";
  if (!path.startsWith("/v1/tether")) return null;

  if (!env.TETHER) {
    return json({ error: "TETHER KV binding missing", note: "bootstrap only, not a full mesh" }, 500);
  }

  try {
    if (path === "/v1/tether/health" && request.method === "GET") {
      return json({
        ok: true,
        product: "azieltether",
        version: "0.1.0",
        author: "Aziel Eliab",
        role: "tether bootstrap",
        note: "Peer directory and batch holding. This Worker is not a full mesh. Live public HTTPS boards stay mesh-free.",
        scopes: [...SCOPES],
        lattice: "cross-product survival anchors",
        precedent: "chain B; chain A is never rewritten",
        genesis_prev_hash: GENESIS,
      });
    }

    if (path === "/v1/tether/announce" && request.method === "POST") {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: "JSON body required" }, 400);
      }
      const nodeId = String(body.node_id || "").trim();
      const pubkey = String(body.pubkey || "").trim();
      const product = String(body.product || body.scope || "").trim();
      if (!nodeId || !pubkey) return json({ error: "node_id and pubkey are required" }, 400);
      if (product !== "*" && !SCOPES.has(product)) {
        return json({ error: "product must be godlock, aziel-corpus, aziel-runtime, or *" }, 400);
      }
      const record = {
        node_id: nodeId,
        pubkey,
        endpoint: String(body.endpoint || ""),
        product: product === "*" ? "azieltether" : product,
        seen_at: Date.now(),
        healthy: true,
      };
      const scopes = product === "*" ? [...SCOPES] : [product];
      for (const scope of scopes) {
        await env.TETHER.put(peerKey(scope, nodeId), JSON.stringify(record), { expirationTtl: 72 * 60 * 60 });
      }
      return json({ ok: true, via: "tether-bootstrap", node_id: nodeId, stored: scopes, note: "directory only; not a full mesh" });
    }

    if (path === "/v1/tether/peers" && request.method === "GET") {
      const product = url.searchParams.get("product") || "*";
      if (product !== "*" && !SCOPES.has(product)) {
        return json({ error: "product must be godlock, aziel-corpus, aziel-runtime, or *" }, 400);
      }
      const peers = await listRecentPeers(env, product);
      return json({
        ok: true,
        product,
        peers,
        count: peers.length,
        note: "Recent healthy peer hints. Loopback endpoints are not globally reachable. Not a VPN.",
      });
    }

    if (path === "/v1/tether/batch" && request.method === "POST") {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: "JSON body required" }, 400);
      }
      const batch = await verifyBatch(body);
      const scope = batch.scope;
      const digest = String(batch.hash).toLowerCase();
      await env.TETHER.put(batchKey(scope, digest), JSON.stringify({ batch, held_at: Date.now() }));
      const index = await readJson(env, indexKey(scope), []);
      const next = [{ hash: digest, held_at: Date.now(), created_at: batch.created_at }, ...index.filter((x) => x.hash !== digest)];
      await env.TETHER.put(indexKey(scope), JSON.stringify(next.slice(0, BATCH_LIMIT)));
      return json({
        ok: true,
        via: "tether-bootstrap",
        hash: digest,
        scope,
        note: "Held until a product central pulls. This Worker is not a full mesh.",
      });
    }

    if (path === "/v1/tether/batch" && request.method === "GET") {
      const since = url.searchParams.get("since") || "";
      const product = url.searchParams.get("product") || url.searchParams.get("scope") || "*";
      const scopes = product === "*" ? [...SCOPES] : SCOPES.has(product) ? [product] : null;
      if (!scopes) return json({ error: "product must be godlock, aziel-corpus, aziel-runtime, or *" }, 400);
      const batches = [];
      for (const scope of scopes) {
        const index = await readJson(env, indexKey(scope), []);
        for (const item of index) {
          if (since && String(item.created_at || "") < since) continue;
          const held = await readJson(env, batchKey(scope, item.hash), null);
          if (held && held.batch) batches.push(held.batch);
        }
      }
      return json({ ok: true, batches, count: batches.length, since: since || null });
    }

    return json({ error: "not found" }, 404);
  } catch (err) {
    return json({ error: String(err.message || err) }, 400);
  }
}
