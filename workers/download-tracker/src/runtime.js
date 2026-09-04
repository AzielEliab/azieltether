/**
 * AzielTether hosted runtime + crawl/AI discovery docs.
 * /v1 never touches DOWNLOADS KV.
 * Author: Aziel Eliab.
 */

import { corsHeaders, json } from "./tether.js";

const PRODUCT = "azieltether";
const VERSION = "0.1.0";
const AUTHOR = "Aziel Eliab";
const HOST = "https://azieltether-download-tracker.vibelock.workers.dev";
const GITHUB = "https://github.com/AzielEliab/azieltether";
const CATALOG = "https://aziel-runtime.vibelock.workers.dev/";
const MOTTO = "Prefer central. Fall back to peers. Reconcile when central returns.";
const ROLE = "central × decentral content/work tether";
const ONE_LINE =
  "Central × decentral software tether by Aziel Eliab: hash-chained batches prefer central, fall back to downloaded peers, then reconcile. Not a VPN.";

export const SKILL = `---
name: AzielTether
description: Use when a downloaded Aziel Eliab node must keep exchanging hash-chained work if central hosts are down, then reconcile. Content/work tether, not a VPN. Author Aziel Eliab.
---

# AzielTether

Central × decentral software tether. Prefer the central Worker. On failure, peers exchange signed hash-chained batches. Reconcile when central returns.

Author: **Aziel Eliab**. Version ${VERSION}.

Always send \`User-Agent: Mozilla/5.0\`. Cloudflare Workers may 403 an empty agent.

THIS IS: a content/work tether for receipts, public Corpus ingest envelopes, and catalog events.
THIS IS NOT: a VPN, Tor, or anonymity network (that is a different product). The Worker is a bootstrap directory and holding pen — not a full mesh. Live public HTTPS boards (godlock.uk, the Corpus library UI) stay mesh-free.

## Endpoints (this Worker)

Host: \`${HOST}\`

| Method | Path | What |
|--------|------|------|
| GET | \`/v1/health\` | Liveness. Does not increment downloads. |
| GET | \`/v1/skill\` | This markdown. Does not increment downloads. |
| GET | \`/v1/tether/health\` | Bootstrap health. Not a full mesh. |
| POST | \`/v1/tether/announce\` | Register node id, pubkey, endpoint hint, product scope. |
| GET | \`/v1/tether/peers?product=\` | Recent healthy peer directory (KV). |
| POST | \`/v1/tether/batch\` | Hold a verified hash-chained batch. |
| GET | \`/v1/tether/batch?since=\` | Pull held batches. |

OpenAPI: \`${HOST}/openapi.json\`
Cite: \`${HOST}/cite.json\`
Catalog: \`${CATALOG}\`
MCP: \`POST ${CATALOG}mcp\`

## How to call (Mozilla/5.0)

\`\`\`bash
curl -s -A 'Mozilla/5.0' ${HOST}/v1/health
curl -s -A 'Mozilla/5.0' ${HOST}/v1/tether/health
curl -s -A 'Mozilla/5.0' ${HOST}/v1/tether/peers?product=godlock
curl -s -A 'Mozilla/5.0' ${HOST}/v1/skill
\`\`\`

## Local (after one-click install)

\`\`\`bash
curl -fsSL ${HOST}/install.sh | bash
azieltether doctor
azieltether serve
\`\`\`

Then open http://127.0.0.1:19740 (this computer only).

## Scopes

- \`godlock\` — receipts
- \`aziel-corpus\` — public Corpus ingest envelopes only (never Aziel Library operator writes)
- \`aziel-runtime\` — catalog events

Apache-2.0. Forks are welcome and always allowed.

Counted download (gzip HTTP 200, no 302): ${HOST}/download
GitHub: ${GITHUB}
`;

function citeJson() {
  return {
    author: AUTHOR,
    title: "AzielTether",
    version: VERSION,
    github: GITHUB,
    download: `${HOST}/download`,
    license: "Apache-2.0",
    catalog: CATALOG,
    one_line: ONE_LINE,
  };
}

function llmsTxt() {
  return `# AzielTether

Author: ${AUTHOR}
One-line: ${ONE_LINE}
GitHub: ${GITHUB}
Download: ${HOST}/download
OpenAPI: ${HOST}/openapi.json
Cite: ${HOST}/cite.json
Catalog: ${CATALOG}

Indexing, metadata scrape, and AI grounding of public pages are allowed.
`;
}

function robotsTxt() {
  return `User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Bytespider
Allow: /

User-agent: CCBot
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: meta-externalagent
Allow: /

User-agent: FacebookBot
Allow: /

User-agent: cohere-ai
Allow: /

User-agent: Diffbot
Allow: /

User-agent: Omgilibot
Allow: /

User-agent: Amazonbot
Allow: /

Sitemap: ${HOST}/sitemap.xml
`;
}

function sitemapXml() {
  const paths = [
    "/",
    "/openapi.json",
    "/cite.json",
    "/llms.txt",
    "/ai.txt",
    "/v1/health",
    "/v1/skill",
    "/v1/tether/health",
    "/ai",
  ];
  const urls = paths
    .map((p) => `  <url><loc>${HOST}${p}</loc></url>`)
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}

function openapiSpec() {
  return {
    openapi: "3.1.0",
    info: {
      title: "AzielTether runtime",
      version: VERSION,
      description: `${ONE_LINE} ${MOTTO} Author ${AUTHOR}.`,
    },
    servers: [{ url: HOST }],
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
          summary: "Return skill markdown. Does not increment download KV.",
          responses: { "200": { description: "markdown" } },
        },
      },
      "/v1/tether/health": {
        get: {
          operationId: "azieltether_tether_health",
          summary: "Bootstrap health. This Worker is not a full mesh.",
          responses: { "200": { description: "ok" } },
        },
      },
      "/v1/tether/announce": {
        post: {
          operationId: "azieltether_tether_announce",
          summary: "Register node id, pubkey, endpoint hint, product scope.",
          requestBody: {
            required: true,
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  required: ["node_id", "pubkey"],
                  properties: {
                    node_id: { type: "string" },
                    pubkey: { type: "string" },
                    endpoint: { type: "string" },
                    product: { type: "string", description: "godlock | aziel-corpus | aziel-runtime | *" },
                  },
                },
              },
            },
          },
          responses: { "200": { description: "announced" } },
        },
      },
      "/v1/tether/peers": {
        get: {
          operationId: "azieltether_tether_peers",
          summary: "Recent healthy peer directory from KV.",
          parameters: [{ name: "product", in: "query", schema: { type: "string" } }],
          responses: { "200": { description: "peers" } },
        },
      },
      "/v1/tether/batch": {
        post: {
          operationId: "azieltether_tether_batch_push",
          summary: "Accept a signed hash-chained batch for holding.",
          requestBody: { required: true, content: { "application/json": { schema: { type: "object" } } } },
          responses: { "200": { description: "held" } },
        },
        get: {
          operationId: "azieltether_tether_batch_pull",
          summary: "Pull held batches.",
          parameters: [
            { name: "since", in: "query", schema: { type: "string" } },
            { name: "product", in: "query", schema: { type: "string" } },
          ],
          responses: { "200": { description: "batches" } },
        },
      },
    },
  };
}

function aiHtml() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AzielTether — use with Grok, ChatGPT, Venice</title>
  <style>
    :root { color-scheme: dark; }
    body { font: 16px/1.45 system-ui, sans-serif; max-width: 42rem; margin: 3rem auto; padding: 0 1.25rem; background: #0e1014; color: #e8eaef; }
    a { color: #c9d4ff; }
    .motto { color: #9aa3b2; }
  </style>
</head>
<body>
  <h1>AzielTether live API</h1>
  <p class="motto">${MOTTO}</p>
  <p>${ONE_LINE}</p>
  <p>ChatGPT (GPT Actions): paste <code>${HOST}/openapi.json</code></p>
  <p>Catalog: <a href="${CATALOG}">${CATALOG}</a></p>
  <p><a href="/openapi.json">openapi.json</a> · <a href="/v1/health">health</a> · <a href="/">downloads</a></p>
</body>
</html>`;
}

function text(body, type) {
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": type, "Cache-Control": "private, no-store", ...corsHeaders() },
  });
}

export async function handleRuntimeApi(request, url) {
  const path = url.pathname;
  const discovery = new Set([
    "/openapi.json",
    "/cite.json",
    "/llms.txt",
    "/ai.txt",
    "/robots.txt",
    "/sitemap.xml",
    "/ai",
  ]);
  const isApi = path === "/v1" || path.startsWith("/v1/") || discovery.has(path);
  if (!isApi) return null;
  if (path.startsWith("/v1/tether")) return null;

  if (path === "/v1/health" && request.method === "GET") {
    return json({
      ok: true,
      product: PRODUCT,
      version: VERSION,
      author: AUTHOR,
      role: ROLE,
      motto: MOTTO,
      catalog: CATALOG,
      note: "Bootstrap + counted download. This Worker is not a full mesh.",
    });
  }
  if (path === "/v1/skill" && request.method === "GET") {
    return text(SKILL, "text/markdown; charset=utf-8");
  }
  if (path === "/openapi.json" && request.method === "GET") return json(openapiSpec());
  if (path === "/cite.json" && request.method === "GET") return json(citeJson());
  if ((path === "/llms.txt" || path === "/ai.txt") && request.method === "GET") {
    return text(llmsTxt(), "text/plain; charset=utf-8");
  }
  if (path === "/robots.txt" && request.method === "GET") {
    return text(robotsTxt(), "text/plain; charset=utf-8");
  }
  if (path === "/sitemap.xml" && request.method === "GET") {
    return text(sitemapXml(), "application/xml; charset=utf-8");
  }
  if (path === "/ai" && request.method === "GET") {
    return new Response(aiHtml(), { headers: { "Content-Type": "text/html; charset=utf-8", ...corsHeaders() } });
  }
  return json({ error: "not found" }, 404);
}
