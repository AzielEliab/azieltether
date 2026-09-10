# azieltether download tracker

Isolated Worker `azieltether-download-tracker`. Project `azieltether`.
v0.1.0 serves the central×decentral software tether runtime.
KV namespace `AZIELTETHER_DOWNLOADS` bound as `DOWNLOADS`.
Does **not** 302 to GitHub on `/download`. Serves gzip via `ASSETS.fetch`,
`Cache-Control: private, no-store`.

GET `/` increments a **page-view** counter (separate from downloads).
GET `/download` increments **downloads**.
`/v1` never increments DOWNLOADS KV.
GET `/install.sh` one-click install (does not increment; script curls `/download`).
GET `/v1/skill` returns skill markdown (`text/markdown`). Does not increment views or downloads.
`/v1/mesh/*` PROXY to aziel-runtime suite mesh (`AZIEL_RUNTIME` / `https://aziel-runtime.vibelock.workers.dev`). Default OFF. QNM-BUILD-1.0 live|locked|isolated. No Node Gate. No auto-heal. Not anonymity. Human UI Live Nodes strip polls `GET /v1/mesh`.

Verify: `curl -sS -A 'Mozilla/5.0' https://azieltether-download-tracker.vibelock.workers.dev/v1/mesh/status` returns MESH-OK style JSON with `enabled: false` by default.

Host (after first deploy): https://azieltether-download-tracker.vibelock.workers.dev

## First deploy (Cloudflare account)

This tree cannot create the KV namespace or publish the Worker without
the AzielEliab vibelock-account token (account
`ac575a9b822bea2bed97d0ab73aed238`, the same account as sibling *Lock
Workers). From a machine that is logged into that account:

```bash
cd workers/download-tracker
npm install
npx wrangler kv namespace create AZIELTETHER_DOWNLOADS
# paste the id into wrangler.toml [[kv_namespaces]].id
npx wrangler deploy
```

Then add the slug `azieltether` to [aziel-runtime](https://github.com/AzielEliab/aziel-runtime)
(`/p/azieltether/{op}` proxies to this Worker `/v1/{op}`).
