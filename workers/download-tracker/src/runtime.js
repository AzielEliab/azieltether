/**
 * AzielTether hosted runtime.
 * Stateless: client sends items / chain JSON. /v1 never touches DOWNLOADS KV.
 * Prefer-central / peer-sync-when-down / reconcile-on-restore / dual-chain / tips.
 * Author: Aziel Eliab.
 */
const PRODUCT = "azieltether";
const VERSION = "0.1.0";
const AUTHOR = "Aziel Eliab";
const MOTTO = "Prefer central. Peer when down. Reconcile on restore.";
const ROLE = "central×decentral software tether";
const HOST = "https://azieltether-download-tracker.vibelock.workers.dev";
const CATALOG = "https://aziel-runtime.vibelock.workers.dev";
const GENESIS_PREV = "0".repeat(64);
const PROTOCOL = "2025-03-26";
const LIMITATION =
  "THIS IS: a central×decentral node-mesh software tether. Prefer the Worker when up. Peer-sync hash-chained work when down. Reconcile on restore. Dual-chain on same-hash conflict. Lattice tips survive across GodLock, Aziel Digital Library, and product Workers. THIS IS NOT: a VPN, MirageGrid, a kernel, a truth score, a backdoor, or a mesh on godlock.uk. Public HTTPS boards stay mesh-free. The tether lives in the downloaded software. Author Aziel Eliab.";

const SKILL = `---
name: AzielTether
description: Use when preferring a central Worker, peer-syncing hash-chained work while it is down, reconciling on restore, or minting lattice tips across GodLock / Aziel Digital Library / product Workers. Software tether, not a VPN. Author Aziel Eliab.
---

# AzielTether

Central × decentral node-mesh **software tether**. Prefer the central Worker when it is up. When it is down, downloaded nodes sync hash-chained work with each other when they hit the internet, then reconcile back to central on restore. Dual-chain on same-hash conflict. Hash lattice tips survive across GodLock, Aziel Digital Library, and product Workers.

Author: **Aziel Eliab**.

**THIS IS:** a software tether (prefer-central / peer-sync-when-down / reconcile-on-restore).

**THIS IS NOT:** a VPN, MirageGrid, a kernel, a truth score, or a mesh on godlock.uk. Public HTTPS boards stay mesh-free. The tether lives in the **downloaded software**. Hosted \`/v1\` does not increment downloads.

Always send \`User-Agent: Mozilla/5.0\`. Cloudflare Workers may 403 an empty agent.

## Endpoints (this Worker)

Host: \`https://azieltether-download-tracker.vibelock.workers.dev\`

| Method | Path | What |
|--------|------|------|
| GET | \`/v1/health\` | Liveness. Does not increment downloads. |
| GET | \`/v1/skill\` | This markdown. Does not increment downloads. |
| GET | \`/v1/example\` | Sample tether item. Does not increment downloads. |
| POST | \`/v1/ingest\` | Accept one hash-chained item. Zero retention. |
| POST | \`/v1/pulse\` | Prefer-central probe + unpublished-item preview. |
| POST | \`/v1/reconcile\` | Merge preview. Dual-chain on same prev_hash. |
| POST | \`/v1/dual-chain\` | Detect same-prev_hash forks. No winner. |
| POST | \`/v1/tip\` | Mint or verify a lattice tip. |
| POST | \`/v1/verify\` | Walk hashes and prev links (DAG). |
| POST | \`/v1/peer-preview\` | Peer-sync handshake preview. Stateless. |

OpenAPI: \`https://azieltether-download-tracker.vibelock.workers.dev/openapi.json\`

Catalog OpenAPI: \`https://aziel-runtime.vibelock.workers.dev/openapi.json\`

MCP: \`POST https://aziel-runtime.vibelock.workers.dev/mcp\`

Catalog aliases under \`/p/azieltether/…\` after the catalog slug is registered.

AZ-CLCE queue hook: sibling products append \`~/.az-clce/tether-queue.jsonl\`. AzielTether harvests those items (scopes \`az-clce\` / \`spre\`) and reconciles via this Worker or \`POST /v1/tether-ingest\` on the product Worker.

## How to call (Mozilla/5.0)

\`\`\`bash
curl -s -A 'Mozilla/5.0' https://azieltether-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' -X POST https://azieltether-download-tracker.vibelock.workers.dev/v1/ingest \\
  -H 'content-type: application/json' \\
  -d '{"created_at":"2026-09-04T00:00:00Z","engine_version":"0.1.0","kind":"work","node_id":"local","payload":"desk closed","prev_hash":"0000000000000000000000000000000000000000000000000000000000000000","report_hash":"abc","scope":"azieltether","hash":"..."}'
curl -s -A 'Mozilla/5.0' https://azieltether-download-tracker.vibelock.workers.dev/v1/skill
\`\`\`

Grok: import the catalog OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.

## Local (after one-click install)

\`\`\`bash
curl -fsSL https://azieltether-download-tracker.vibelock.workers.dev/install.sh | bash
azieltether ui
azieltether doctor
\`\`\`

Then open http://127.0.0.1:8874 (this computer only).

## Honest banner

${LIMITATION}

Apache-2.0 (or the repo LICENSE). Forks are welcome and always allowed.

## Catalog + local UI

Author: **Aziel Eliab**. Honest scope: software tether, not a VPN.

- Catalog product: https://aziel-runtime.vibelock.workers.dev/p/azieltether/
- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json
- Catalog MCP: \`POST https://aziel-runtime.vibelock.workers.dev/mcp\`
- This Worker skill: \`GET https://azieltether-download-tracker.vibelock.workers.dev/v1/skill\`
- This Worker OpenAPI: https://azieltether-download-tracker.vibelock.workers.dev/openapi.json
- Sample payload: \`GET https://azieltether-download-tracker.vibelock.workers.dev/v1/example\`

Local UI: **Import JSON file** (\`type=file\`) and **Export JSON**. Then \`azieltether doctor\`.

Counted download (gzip HTTP 200, no 302): https://azieltether-download-tracker.vibelock.workers.dev/download?asset=azieltether-0.1.0.tar.gz
GitHub: https://github.com/AzielEliab/azieltether
`;

const EXAMPLE_ITEM = {
  created_at: "2026-09-04T00:00:00Z",
  engine_version: VERSION,
  kind: "work",
  node_id: "example-node",
  payload: "desk closed",
  prev_hash: GENESIS_PREV,
  report_hash: "pending",
  scope: "azieltether",
};

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept, MCP-Protocol-Version, mcp-session-id",
  };
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders() },
  });
}

function html(body) {
  return new Response(body, {
    headers: { "Content-Type": "text/html; charset=utf-8", ...corsHeaders() },
  });
}

function originOf(request) {
  try {
    return new URL(request.url).origin;
  } catch {
    return HOST;
  }
}

function canonicalJson(obj) {
  const keys = Object.keys(obj).sort();
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + JSON.stringify(obj[k])).join(",") + "}";
}

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function bodyWithoutHash(item) {
  const out = {};
  for (const [k, v] of Object.entries(item || {})) {
    if (k !== "hash") out[k] = v;
  }
  return out;
}

async function digestItem(item) {
  return sha256Hex(canonicalJson(bodyWithoutHash(item)));
}

function asItems(body) {
  if (!body) return [];
  if (Array.isArray(body)) return body.filter((x) => x && typeof x === "object");
  if (typeof body === "string") {
    try {
      return asItems(JSON.parse(body));
    } catch {
      return [];
    }
  }
  if (Array.isArray(body.items)) return body.items.filter((x) => x && typeof x === "object");
  if (Array.isArray(body.chain)) return body.chain.filter((x) => x && typeof x === "object");
  if (body.hash || body.prev_hash) return [body];
  return [];
}

function detectDualChain(items) {
  const byPrev = {};
  for (const item of items) {
    const prev = String(item.prev_hash || "");
    const digest = String(item.hash || "");
    if (!prev || !digest) continue;
    if (!byPrev[prev]) byPrev[prev] = [];
    if (!byPrev[prev].includes(digest)) byPrev[prev].push(digest);
  }
  const forks = [];
  for (const [prev, children] of Object.entries(byPrev)) {
    if (children.length > 1) forks.push({ prev_hash: prev, child_hashes: children });
  }
  return forks;
}

async function verifyItems(items) {
  const errors = [];
  const known = {};
  const order = [];
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const digest = item && item.hash;
    if (!digest) {
      errors.push("item " + i + ": missing hash");
      continue;
    }
    const recomputed = await digestItem(item);
    if (recomputed !== digest) errors.push("item " + i + ": hash mismatch");
    known[digest] = item;
    order.push(digest);
  }
  for (const [digest, item] of Object.entries(known)) {
    const prev = String(item.prev_hash || "");
    if (prev && prev !== GENESIS_PREV && !known[prev]) {
      errors.push(digest.slice(0, 12) + ": prev_hash not in store");
    }
  }
  const usedAsPrev = new Set(Object.values(known).map((it) => String(it.prev_hash || "")));
  const tips = order.filter((h) => !usedAsPrev.has(h));
  return {
    ok: errors.length === 0,
    items: Object.keys(known).length,
    errors,
    first_hash: order[0] || null,
    last_hash: order.length ? order[order.length - 1] : null,
    tip_hashes: tips.length ? tips : order.slice(-1),
    dual_chain: detectDualChain(items),
    winner: null,
  };
}

async function ingestOne(item) {
  const hasHash = Boolean(item && item.hash && item.prev_hash);
  let hashOk = false;
  if (hasHash) {
    hashOk = (await digestItem(item)) === item.hash;
  }
  return {
    product: PRODUCT,
    version: VERSION,
    author: AUTHOR,
    ok: hasHash && hashOk,
    accepted: hasHash && hashOk,
    stored: false,
    kv_increment: false,
    hash: item && item.hash ? item.hash : null,
    scope: item && item.scope ? item.scope : null,
    note: "Zero retention ingest. Hash-chain item acknowledged only. Not a VPN.",
    limitation: LIMITATION,
  };
}

function openapiSpec(origin) {
  const itemBody = {
    required: true,
    content: { "application/json": { schema: { type: "object" } } },
  };
  return {
    openapi: "3.1.0",
    info: {
      title: "AzielTether runtime",
      version: VERSION,
      summary: MOTTO,
      description: LIMITATION,
      license: { name: "Apache-2.0", identifier: "Apache-2.0" },
      contact: { name: AUTHOR, url: "https://github.com/AzielEliab/azieltether" },
    },
    servers: [{ url: origin }],
    paths: {
      "/v1/health": {
        get: {
          operationId: "azieltether_health",
          summary: "Liveness. Does not increment download KV.",
          responses: { "200": { description: "ok" } },
        },
      },
      "/v1/skill": {
        get: {
          operationId: "azieltether_skill",
          summary: "Return AzielTether skill markdown. Does not increment download KV.",
          responses: { "200": { description: "markdown" } },
        },
      },
      "/v1/example": {
        get: {
          operationId: "azieltether_example",
          summary: "Sample tether item. Does not increment downloads.",
          responses: { "200": { description: "example" } },
        },
      },
      "/v1/ingest": {
        post: {
          operationId: "azieltether_ingest",
          summary: "Accept one hash-chained item. Zero retention.",
          requestBody: itemBody,
          responses: { "200": { description: "ack" } },
        },
      },
      "/v1/pulse": {
        post: {
          operationId: "azieltether_pulse",
          summary: "Prefer-central probe + unpublished-item preview.",
          requestBody: itemBody,
          responses: { "200": { description: "pulse" } },
        },
      },
      "/v1/reconcile": {
        post: {
          operationId: "azieltether_reconcile",
          summary: "Merge preview. Dual-chain on same prev_hash. No winner.",
          requestBody: itemBody,
          responses: { "200": { description: "reconcile" } },
        },
      },
      "/v1/dual-chain": {
        post: {
          operationId: "azieltether_dual-chain",
          summary: "Detect same-prev_hash forks. Does not pick a winner.",
          requestBody: itemBody,
          responses: { "200": { description: "forks" } },
        },
      },
      "/v1/tip": {
        post: {
          operationId: "azieltether_tip",
          summary: "Mint or verify a lattice tip for a survival surface.",
          requestBody: itemBody,
          responses: { "200": { description: "tip" } },
        },
      },
      "/v1/verify": {
        post: {
          operationId: "azieltether_verify",
          summary: "Walk hashes and prev links. Dual-chain is allowed.",
          requestBody: itemBody,
          responses: { "200": { description: "verify" } },
        },
      },
      "/v1/peer-preview": {
        post: {
          operationId: "azieltether_peer-preview",
          summary: "Peer-sync handshake preview. Stateless.",
          requestBody: itemBody,
          responses: { "200": { description: "peer" } },
        },
      },
    },
  };
}

function aiHtml(origin) {
  return `<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AzielTether — use with Grok, ChatGPT, Venice</title>
<style>
  :root { color-scheme: dark; }
  body { font: 16px/1.45 system-ui, sans-serif; max-width: 42rem; margin: 3rem auto; padding: 0 1.25rem; background: #0e1014; color: #e8eaef; }
  code { background: #151922; padding: .15rem .4rem; border-radius: 4px; }
  a { color: #c9d4ff; }
  .motto { color: #9aa3b2; font-style: italic; }
  .banner { border: 1px solid #5c4a1a; background: #241c0d; color: #f0d78c; padding: .85rem 1rem; border-radius: 8px; }
</style>
<body>
  <h1>AzielTether live API</h1>
  <p class="motto">${MOTTO}</p>
  <p class="banner">${LIMITATION}</p>
  <p>OpenAPI: <a href="${origin}/openapi.json">${origin}/openapi.json</a></p>
  <p>MCP: POST <code>${origin}/mcp</code> · Catalog: <a href="${CATALOG}/">${CATALOG}</a></p>
  <p>Grok: import OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.</p>
  <p><a href="/">Downloads</a> · <a href="/v1/health">health</a> · <a href="/v1/skill">skill</a></p>
</body>
</html>`;
}

function mcpTools() {
  return [
    { name: "azieltether_health", description: "Liveness. Does not increment download KV.", inputSchema: { type: "object" } },
    { name: "azieltether_skill", description: "Return AzielTether skill markdown. Does not increment download KV.", inputSchema: { type: "object" } },
    { name: "azieltether_ingest", description: "Accept one hash-chained item. Zero retention. Not a VPN.", inputSchema: { type: "object", additionalProperties: true } },
    { name: "azieltether_pulse", description: "Prefer-central probe + unpublished-item preview.", inputSchema: { type: "object", additionalProperties: true } },
    { name: "azieltether_reconcile", description: "Merge preview. Dual-chain on same prev_hash.", inputSchema: { type: "object", additionalProperties: true } },
    { name: "azieltether_dual-chain", description: "Detect same-prev_hash forks. No winner.", inputSchema: { type: "object", additionalProperties: true } },
    { name: "azieltether_tip", description: "Mint or verify a lattice tip.", inputSchema: { type: "object", additionalProperties: true } },
    { name: "azieltether_verify", description: "Walk hashes and prev links.", inputSchema: { type: "object", additionalProperties: true } },
  ];
}

async function handleMcp(request) {
  if (request.method === "GET") {
    return json({
      ok: true,
      transport: "JSON-RPC MCP-over-HTTP",
      endpoint: "POST /mcp",
      methods: ["initialize", "tools/list", "tools/call", "ping"],
      auth: "none (public)",
      limitation: LIMITATION,
    });
  }
  if (request.method !== "POST") return json({ error: "POST JSON-RPC to /mcp" }, 405);
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } });
  }
  const id = body && body.id !== undefined ? body.id : null;
  const method = body && body.method;
  const params = (body && body.params) || {};
  const result = (value) => json({ jsonrpc: "2.0", id, result: value });
  if (method === "initialize") {
    return result({
      protocolVersion: PROTOCOL,
      capabilities: { tools: { listChanged: false } },
      serverInfo: { name: PRODUCT, version: VERSION },
      instructions: LIMITATION,
    });
  }
  if (method === "notifications/initialized" || method === "initialized") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (method === "ping") return result({});
  if (method === "tools/list") return result({ tools: mcpTools() });
  if (method === "tools/call") {
    const name = params.name;
    const args = params.arguments || params.input || {};
    let payload;
    if (name === "azieltether_health") {
      payload = { ok: true, product: PRODUCT, version: VERSION, kv_increment: false, limitation: LIMITATION };
    } else if (name === "azieltether_skill") {
      payload = { markdown: SKILL, kv_increment: false, limitation: LIMITATION };
    } else if (name === "azieltether_ingest") {
      payload = await ingestOne(args);
    } else if (name === "azieltether_pulse") {
      const items = asItems(args);
      payload = { ok: true, mode: "prefer-central", items: items.length, limitation: LIMITATION };
    } else if (name === "azieltether_reconcile") {
      payload = await verifyItems(asItems(args));
      payload.mode = "reconcile-on-restore";
    } else if (name === "azieltether_dual-chain") {
      const items = asItems(args);
      payload = { ok: true, forks: detectDualChain(items), winner: null, limitation: LIMITATION };
    } else if (name === "azieltether_tip") {
      payload = { ok: true, tip: args, note: "Lattice tip only. Boards stay mesh-free.", limitation: LIMITATION };
    } else if (name === "azieltether_verify") {
      payload = await verifyItems(asItems(args));
    } else {
      payload = { error: "unknown tool", name };
    }
    return result({ content: [{ type: "text", text: JSON.stringify(payload) }], isError: Boolean(payload.error) });
  }
  return json({ jsonrpc: "2.0", id, error: { code: -32601, message: `Method not found: ${method}` } });
}

export async function handleRuntimeApi(request, url) {
  const path = url.pathname.replace(/\/+$/, "") || "/";
  if (path === "/mcp") return handleMcp(request);
  if (path === "/v1/skill" && request.method === "GET") {
    return new Response(SKILL, {
      status: 200,
      headers: {
        "Content-Type": "text/markdown; charset=utf-8",
        "Cache-Control": "private, no-store",
        ...corsHeaders(),
      },
    });
  }
  if (path === "/v1/health" && request.method === "GET") {
    return json({
      ok: true,
      product: PRODUCT,
      version: VERSION,
      author: AUTHOR,
      role: ROLE,
      motto: MOTTO,
      kv_increment: false,
      stored: false,
      prefer_central: true,
      vpn: false,
      miragegrid: false,
      mesh_on_public_boards: false,
      limitation: LIMITATION,
      catalog: CATALOG,
    });
  }
  if ((path === "/v1/example" || path === "/v1/example/") && request.method === "GET") {
    const item = { ...EXAMPLE_ITEM };
    item.report_hash = await sha256Hex(item.payload);
    item.hash = await digestItem(item);
    return json({
      ok: true,
      product: PRODUCT,
      author: AUTHOR,
      example: item,
      note: "POST this to /v1/ingest. Sample payload only. Does not increment downloads.",
    });
  }
  if (path === "/openapi.json" && request.method === "GET") {
    return json(openapiSpec(originOf(request)));
  }
  if ((path === "/ai" || url.pathname === "/ai/") && request.method === "GET") {
    return html(aiHtml(originOf(request)));
  }

  async function readBody() {
    try {
      return await request.json();
    } catch {
      return null;
    }
  }

  if (path === "/v1/ingest" && request.method === "POST") {
    const body = await readBody();
    if (!body) return json({ error: "JSON body required", limitation: LIMITATION }, 400);
    const item = asItems(body)[0] || body;
    return json(await ingestOne(item));
  }
  if (path === "/v1/pulse" && request.method === "POST") {
    const body = (await readBody()) || {};
    const items = asItems(body);
    const verified = await verifyItems(items);
    return json({
      product: PRODUCT,
      version: VERSION,
      author: AUTHOR,
      mode: "prefer-central",
      central: { ok: true, prefer_central: true },
      unpublished: items.length,
      verify: verified,
      limitation: LIMITATION,
      kv_increment: false,
      stored: false,
    });
  }
  if (path === "/v1/reconcile" && request.method === "POST") {
    const body = (await readBody()) || {};
    const items = asItems(body);
    const verified = await verifyItems(items);
    return json({
      product: PRODUCT,
      version: VERSION,
      author: AUTHOR,
      mode: "reconcile-on-restore",
      merge: { added: 0, skipped: 0, items: verified.items, dual_chain: verified.dual_chain },
      verify: verified,
      winner: null,
      stored: false,
      kv_increment: false,
      limitation: LIMITATION,
    });
  }
  if (path === "/v1/dual-chain" && request.method === "POST") {
    const body = (await readBody()) || {};
    const items = asItems(body);
    return json({
      ok: true,
      product: PRODUCT,
      author: AUTHOR,
      forks: detectDualChain(items),
      winner: null,
      note: "Dual-chain keeps both children of the same prev_hash. No winner.",
      limitation: LIMITATION,
    });
  }
  if (path === "/v1/tip" && request.method === "POST") {
    const body = (await readBody()) || {};
    const surface = body.surface || "worker";
    const tipHash = body.tip_hash || body.hash || GENESIS_PREV;
    const tip = {
      created_at: body.created_at || new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
      engine_version: VERSION,
      kind: "tip",
      node_id: body.node_id || "hosted",
      prev_hash: body.prev_hash || GENESIS_PREV,
      product: PRODUCT,
      surface,
      tip_hash: tipHash,
      note: "Lattice tip only. Not a mesh on godlock.uk. Public boards stay mesh-free.",
    };
    tip.hash = await digestItem(tip);
    return json({
      ok: true,
      product: PRODUCT,
      author: AUTHOR,
      tip,
      stored: false,
      kv_increment: false,
      mesh_on_public_boards: false,
      limitation: LIMITATION,
    });
  }
  if (path === "/v1/verify" && request.method === "POST") {
    const body = (await readBody()) || {};
    const verified = await verifyItems(asItems(body));
    return json({ product: PRODUCT, version: VERSION, author: AUTHOR, motto: MOTTO, ...verified, limitation: LIMITATION });
  }
  if (path === "/v1/peer-preview" && request.method === "POST") {
    const body = (await readBody()) || {};
    const items = asItems(body);
    const verified = await verifyItems(items);
    return json({
      ok: true,
      product: PRODUCT,
      author: AUTHOR,
      mode: "peer-sync-when-down",
      items,
      tip_hashes: verified.tip_hashes,
      dual_chain: verified.dual_chain,
      stored: false,
      kv_increment: false,
      limitation: LIMITATION,
    });
  }
  if (path.startsWith("/v1/") || path === "/v1") {
    return json(
      {
        error: "not found",
        hint: "GET /v1/health  GET /v1/skill  POST /v1/ingest  POST /v1/pulse  POST /v1/reconcile  POST /v1/dual-chain  POST /v1/tip  POST /v1/verify",
        limitation: LIMITATION,
      },
      404,
    );
  }
  return null;
}
