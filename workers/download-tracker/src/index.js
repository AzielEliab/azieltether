import { handleMeshApi } from "./mesh.js";
import { handleRuntimeApi } from "./runtime.js";

/**
 * AzielTether download tracker (Cloudflare Worker).
 *
 * GET  /          increments page-view counter, HTML with Views + Downloads
 * GET  /download  increments downloads, serves tarball via env.ASSETS.fetch (no 302)
 * GET  /go        increments downloads, still serves via this Worker (no 302 to GitHub)
 * GET  /install.sh  one-click install script (does not increment; script curls /download)
 * GET  /v1/skill   skill markdown (does not increment downloads or views)
 * GET  /stats     {views, downloads, total, by_repo, github:{stars,forks,watchers,release_download_count}}
 * POST /event     forks report a download {owner,repo,branch,fork,asset}
 * /v1, /v1/mesh/* do not increment. Suite mesh PROXY via AZIEL_RUNTIME.
 *
 * KV binding DOWNLOADS. Keys: project|owner|repo|branch|fork
 * Isolated: Worker azieltether-download-tracker, KV AZIELTETHER_DOWNLOADS.
 * /v1 does not increment.
 */

const PROJECT = "azieltether";
const DEFAULT_ASSET = "azieltether-0.1.0.tar.gz";
const DEFAULT_OWNER = "AzielEliab";
const DEFAULT_REPO = "azieltether";
const DEFAULT_BRANCH = "main";
const HOST = "https://azieltether-download-tracker.vibelock.workers.dev";
const GITHUB_RELEASES = "https://github.com/AzielEliab/azieltether/releases";
const GITHUB_LATEST = "https://github.com/AzielEliab/azieltether/releases/latest";
const GITHUB_REPO = "https://github.com/AzielEliab/azieltether";
const INSTALL_LINE = "curl -fsSL https://azieltether-download-tracker.vibelock.workers.dev/install.sh | bash";
const LIMITATION =
  "THIS IS: a central×decentral node-mesh software tether. Prefer the Worker when up. Peer-sync hash-chained work when down. Reconcile on restore. Dual-chain on same-hash conflict. Lattice tips survive across GodLock, Aziel Digital Library, and product Workers. THIS IS NOT: a VPN, MirageGrid, a kernel, a truth score, a backdoor, or a mesh on godlock.uk. Public HTTPS boards stay mesh-free. The tether lives in the downloaded software. Author Aziel Eliab.";

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept, Authorization, X-Aziel-Runtime-Token, User-Agent",
  };
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders() },
  });
}

function splitOwnerRepo(value, fallbackOwner, fallbackRepo) {
  if (typeof value === "string" && value.includes("/")) {
    const [o, r] = value.split("/").filter(Boolean);
    if (o && r) return { owner: o, repo: r };
  }
  return { owner: fallbackOwner, repo: fallbackRepo };
}

function parseDims(src) {
  const get = (k) => {
    if (src == null) return null;
    if (typeof src.get === "function") {
      const v = src.get(k);
      return v == null || v === "" ? null : v;
    }
    const v = src[k];
    return v == null || v === "" ? null : v;
  };

  let owner = get("owner") || DEFAULT_OWNER;
  let repo = get("repo") || DEFAULT_REPO;
  if (typeof repo === "string" && repo.includes("/")) {
    const split = splitOwnerRepo(repo, owner, DEFAULT_REPO);
    owner = split.owner;
    repo = split.repo;
  }

  const branch = get("branch") || DEFAULT_BRANCH;
  const tag = get("tag") || "latest";
  const asset = get("asset") || "";

  const forkRaw = get("fork");
  let fork = "0";
  if (forkRaw === 1 || forkRaw === true || forkRaw === "1" || forkRaw === "true") {
    fork = "1";
  } else if (typeof forkRaw === "string" && forkRaw.includes("/")) {
    const split = splitOwnerRepo(forkRaw, owner, repo);
    owner = split.owner;
    repo = split.repo;
    fork = "1";
  } else if (forkRaw != null && forkRaw !== 0 && forkRaw !== false && forkRaw !== "0" && forkRaw !== "false") {
    fork = "1";
  }

  if (`${owner}/${repo}`.toLowerCase() !== `${DEFAULT_OWNER}/${DEFAULT_REPO}`.toLowerCase()) {
    fork = "1";
  }

  return { project: PROJECT, owner, repo, branch, fork, tag, asset };
}

function kvKey(dims) {
  return `${dims.project}|${dims.owner}|${dims.repo}|${dims.branch}|${dims.fork}`;
}

function totalKey() {
  return PROJECT + "|__total__";
}

function viewsKey() {
  return PROJECT + "|__views__";
}

function githubCacheKey() {
  return PROJECT + "|__github__";
}

async function increment(env, dims) {
  const key = kvKey(dims);
  const n = parseInt((await env.DOWNLOADS.get(key)) || "0", 10) + 1;
  await env.DOWNLOADS.put(key, String(n));
  const tot = parseInt((await env.DOWNLOADS.get(totalKey())) || "0", 10) + 1;
  await env.DOWNLOADS.put(totalKey(), String(tot));
  return tot;
}

async function incrementViews(env) {
  const n = parseInt((await env.DOWNLOADS.get(viewsKey())) || "0", 10) + 1;
  await env.DOWNLOADS.put(viewsKey(), String(n));
  return n;
}

async function listAllKeys(env) {
  const keys = [];
  let cursor;
  do {
    const page = await env.DOWNLOADS.list(cursor ? { cursor } : {});
    keys.push(...page.keys);
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);
  return keys;
}

async function githubStats(env) {
  const cached = await env.DOWNLOADS.get(githubCacheKey());
  if (cached) {
    try {
      const obj = JSON.parse(cached);
      if (obj && obj.fetched_at && Date.now() - obj.fetched_at < 5 * 60 * 1000) {
        return obj;
      }
    } catch {
      /* ignore */
    }
  }
  const headers = { "User-Agent": "Mozilla/5.0 AzielTether-download-tracker", Accept: "application/vnd.github+json" };
  let stars = 0;
  let forks = 0;
  let watchers = 0;
  let release_download_count = 0;
  try {
    const repoRes = await fetch("https://api.github.com/repos/AzielEliab/azieltether", { headers });
    if (repoRes.ok) {
      const repo = await repoRes.json();
      stars = Number(repo.stargazers_count) || 0;
      forks = Number(repo.forks_count) || 0;
      watchers = Number(repo.subscribers_count != null ? repo.subscribers_count : repo.watchers_count) || 0;
    }
    const relRes = await fetch("https://api.github.com/repos/AzielEliab/azieltether/releases/latest", { headers });
    if (relRes.ok) {
      const rel = await relRes.json();
      const assets = Array.isArray(rel.assets) ? rel.assets : [];
      release_download_count = assets.reduce((s, a) => s + (Number(a.download_count) || 0), 0);
    }
  } catch {
    /* public API; empty is fine */
  }
  const out = { stars, forks, watchers, release_download_count, fetched_at: Date.now() };
  try {
    await env.DOWNLOADS.put(githubCacheKey(), JSON.stringify(out));
  } catch {
    /* ignore */
  }
  return out;
}

async function collectStats(env) {
  const keys = await listAllKeys(env);
  let summed = 0;
  const by_repo = {};
  const by_branch = {};
  const by_fork = { "0": 0, "1": 0 };
  const breakdown = [];

  for (const k of keys) {
    const name = k.name;
    if (name === viewsKey() || name === totalKey() || name === githubCacheKey()) continue;
    const n = parseInt((await env.DOWNLOADS.get(name)) || "0", 10);
    if (!Number.isFinite(n) || n <= 0) continue;
    const parts = name.split("|");
    if (parts.length < 5) continue;
    const [project, owner, repo, branch, fork] = parts;
    summed += n;
    const repoId = `${owner}/${repo}`;
    by_repo[repoId] = (by_repo[repoId] || 0) + n;
    by_branch[branch] = (by_branch[branch] || 0) + n;
    const forkFlag = fork === "1" ? "1" : "0";
    by_fork[forkFlag] = (by_fork[forkFlag] || 0) + n;
    breakdown.push({ project, owner, repo, branch, fork: forkFlag, count: n });
  }

  const downloadsDirect = parseInt((await env.DOWNLOADS.get(totalKey())) || "0", 10);
  const downloads = Number.isFinite(downloadsDirect) && downloadsDirect > 0 ? downloadsDirect : summed;
  const views = parseInt((await env.DOWNLOADS.get(viewsKey())) || "0", 10) || 0;
  const github = await githubStats(env);
  return {
    project: PROJECT,
    views,
    downloads,
    total: downloads,
    by_repo,
    by_branch,
    by_fork,
    breakdown,
    github: {
      stars: github.stars || 0,
      forks: github.forks || 0,
      watchers: github.watchers || 0,
      release_download_count: github.release_download_count || 0,
    },
    note: "Forks identified by GitHub owner/repo. Key layout: project|owner|repo|branch|fork. Views are separate from downloads. /v1 does not increment.",
  };
}

function installScript() {
  return `#!/usr/bin/env bash
# AzielTether one-click install. Counted download via this Worker.
set -euo pipefail
HOST="${HOST}"
ASSET="${DEFAULT_ASSET}"
WORKDIR="\${AZIELTETHER_HOME:-\$HOME/azieltether}"
mkdir -p "\$WORKDIR"
cd "\$WORKDIR"
echo "Downloading counted tarball from \${HOST}/download (User-Agent Mozilla/5.0)…"
curl -fsSL -A 'Mozilla/5.0' "\${HOST}/download?asset=\${ASSET}" -o "\${ASSET}"
tar -xzf "\${ASSET}"
DIR="\$(find . -maxdepth 1 -type d -name 'azieltether-*' | head -n 1)"
if [ -n "\${DIR}" ]; then
  cd "\${DIR}"
fi
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
echo
echo "Installed AzielTether."
echo "Run:  azieltether ui"
echo "Then open http://127.0.0.1:8874  (loopback only)"
echo "Prefer central. Peer when down. Reconcile on restore. Author: Aziel Eliab."
`;
}

function robotsTxt() {
  const bots = [
    "*",
    "GPTBot",
    "ChatGPT-User",
    "Google-Extended",
    "anthropic-ai",
    "ClaudeBot",
    "PerplexityBot",
    "Bytespider",
    "CCBot",
    "Applebot-Extended",
    "meta-externalagent",
    "FacebookBot",
    "cohere-ai",
    "Diffbot",
    "Omgilibot",
    "Amazonbot",
  ];
  return bots.map((b) => "User-agent: " + b + "\nAllow: /\n").join("\n") + "\nSitemap: " + HOST + "/sitemap.xml\n";
}

function llmsTxt() {
  return `# AzielTether

Author: Aziel Eliab
One-line: Central × decentral node-mesh software tether. Prefer Worker when up; peer sync when down; reconcile on restore.
GitHub: ${GITHUB_REPO}
Download: ${HOST}/download
OpenAPI: ${HOST}/openapi.json
Cite: ${HOST}/cite.json
Skill: ${HOST}/v1/skill

Indexing, metadata scrape, and AI grounding of public pages are allowed.
Suite mesh: ${HOST}/v1/mesh (PROXY to aziel-runtime; default OFF; QNM-BUILD-1.0; QNS-CD-1.0 hub cite, no public qnsd proxy).
Not a VPN. Not MirageGrid. Public HTTPS boards stay mesh-free.
`;
}

async function serveAsset(request, env, asset, { head = false } = {}) {
  if (!env.ASSETS) {
    return json({ error: "assets binding missing" }, 500);
  }
  const assetUrl = new URL("/" + asset, request.url);
  const assetRes = await env.ASSETS.fetch(new Request(assetUrl, { method: "GET" }));
  if (!assetRes.ok) {
    return json({ error: "asset not hosted", asset, status: assetRes.status }, 404);
  }
  const headers = new Headers();
  headers.set("Content-Type", "application/gzip");
  headers.set("Content-Disposition", 'attachment; filename="' + asset.replaceAll('"', "") + '"');
  headers.set("Cache-Control", "private, no-store");
  const len = assetRes.headers.get("Content-Length");
  if (len) headers.set("Content-Length", len);
  for (const [k, v] of Object.entries(corsHeaders())) headers.set(k, v);
  if (head) {
    return new Response(null, { status: 200, headers });
  }
  return new Response(assetRes.body, { status: 200, headers });
}

async function indexHtml(env) {
  const stats = await collectStats(env);
  const views = Number(stats.views) || 0;
  const downloads = Number(stats.downloads) || 0;
  const v = views.toLocaleString("en-US");
  const n = downloads.toLocaleString("en-US");
  const gh = stats.github || {};
  const breakdown = (stats.breakdown || [])
    .map(
      (b) =>
        `<li><code>${b.owner}/${b.repo}</code> branch <code>${b.branch}</code> fork=${b.fork} → ${b.count}</li>`,
    )
    .join("") || "<li>none yet</li>";
  return `<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AzielTether — Aziel Eliab</title>
<meta name="description" content="Central × decentral node-mesh software tether by Aziel Eliab. Prefer Worker when up; peer sync when down; reconcile on restore.">
<meta name="author" content="Aziel Eliab">
<link rel="canonical" href="${HOST}/">
<meta property="og:title" content="AzielTether — Aziel Eliab">
<meta property="og:description" content="Prefer central. Peer when down. Reconcile on restore.">
<meta property="og:url" content="${HOST}/">
<meta property="og:type" content="website">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "AzielTether",
  "author": { "@type": "Person", "name": "Aziel Eliab" },
  "codeRepository": "${GITHUB_REPO}",
  "downloadUrl": "${HOST}/download",
  "license": "https://www.apache.org/licenses/LICENSE-2.0",
  "url": "${HOST}/",
  "softwareVersion": "0.1.0",
  "description": "Central × decentral node-mesh software tether. Prefer Worker when up; peer sync when down; reconcile on restore."
}
</script>
<!-- gitbaby-seo -->
<style>
  :root { color-scheme: dark; }
  body { font: 16px/1.45 system-ui, sans-serif; max-width: 42rem; margin: 3rem auto; padding: 0 1.25rem 4rem; background: #0e1014; color: #e8eaef; }
  h1 { font-size: 1.75rem; margin: 0 0 .35rem; }
  .motto { color: #9aa3b2; margin: 0 0 1.5rem; }
  .card { border: 1px solid #2a3140; border-radius: 12px; padding: 1.25rem 1.35rem; background: #151922; }
  .nums { display: grid; grid-template-columns: 1fr 1fr; gap: .8rem; margin: 0 0 1rem; }
  .count { font-size: 2.2rem; font-variant-numeric: tabular-nums; font-weight: 700; margin: 0; }
  .count span { display: block; font-size: .95rem; font-weight: 500; color: #9aa3b2; }
  .kid { font-size: 1.05rem; margin: 0 0 1rem; }
  .btns { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; margin: 0 0 .85rem; }
  @media (max-width: 520px) { .btns { grid-template-columns: 1fr; } }
  a.btn, button.btn { display: block; width: 100%; box-sizing: border-box; text-align: center; font: inherit; font-size: 1.2rem; font-weight: 750; padding: 1rem 1.1rem; border-radius: 10px; border: 0; cursor: pointer; text-decoration: none; }
  a.btn.primary { background: #e8eaef; color: #0e1014; }
  button.btn.install { background: #c9a227; color: #14110a; }
  button.btn.install.copied { background: #7dcf9a; color: #0e1014; }
  .meta { margin-top: 1.1rem; color: #9aa3b2; font-size: .92rem; }
  .meta a { color: #c9d4ff; }
  .iso { margin-top: .85rem; font-size: .85rem; color: #7d8696; }
  .banner { border: 1px solid #5c4a1a; background: #241c0d; color: #f0d78c; padding: .85rem 1rem; border-radius: 8px; margin: 0 0 1.2rem; font-size: .92rem; }
  pre { background: #0e1014; padding: .75rem .9rem; overflow: auto; border-radius: 8px; font-size: .82rem; }
  code { font-size: .88rem; }
  .cite { margin-top: 1.4rem; padding-top: 1rem; border-top: 1px solid #2a3140; }
  .cite h2 { font-size: 1.05rem; margin: 0 0 .4rem; }
  .cite p { color: #c5ccd8; font-size: .95rem; }
  .cite a { color: #c9d4ff; }
  #meshStrip { border: 1px solid #c9a227; border-radius: 12px; padding: .85rem 1rem; background: #151922; margin: 0 0 1.2rem; display: flex; flex-wrap: wrap; align-items: center; gap: .7rem 1rem; font-size: .88rem; color: #9aa3b2; }
  #meshStrip .live { color: #e8eaef; }
  #meshStrip .live b { color: #c9a227; font-size: 1.35rem; margin-right: .35rem; }
  #meshStrip .rollup b { color: #c9a227; }
  #meshStrip button { font: 700 .78rem/1 ui-monospace, Menlo, Consolas, monospace; height: 2rem; padding: 0 .75rem; border-radius: 8px; background: #101010; color: #e8eaef; border: 1px solid #c9a227; cursor: pointer; }
  #meshStrip button:hover { background: #241c0d; color: #c9a227; }
  #meshStrip input { width: 10rem; padding: .4rem .55rem; border: 1px solid #c9a227; border-radius: 8px; background: #0e0e0e; color: #e8eaef; font: inherit; }
  #meshProducts { flex-basis: 100%; margin: 0; }
</style>
<body>
  <h1>AzielTether</h1>
  <p class="motto">Prefer central. Peer when down. Reconcile on restore. Author Aziel Eliab.</p>
  <p class="banner">${LIMITATION}</p>
  <div id="meshStrip" aria-label="Suite Live Nodes">
    <div class="live"><b id="meshLiveCount">0</b> Live Nodes</div>
    <div id="meshLine">Suite mesh: off (default). QNM-BUILD-1.0. QNS-CD-1.0. Not an anonymity network.</div>
    <div class="rollup">live <b id="qnmLive">0</b> · locked <b id="qnmLocked">0</b> · isolated <b id="qnmIsolated">0</b></div>
    <div>No Node Gate · No auto-heal · Aziel Eliab only</div>
    <div>
      <input id="meshBearer" type="text" maxlength="80" placeholder="bearer (required to enable)" aria-label="mesh bearer">
      <button id="meshEnable" type="button" title="Enable suite mesh. Declared bearer required. Default off.">Enable</button>
      <button id="meshDisable" type="button" title="Disable suite mesh (always allowed)">Disable</button>
      <button id="meshJoin" type="button" title="Join as azieltether. Refused while mesh is OFF. No auto-join.">Join</button>
      <button id="meshLeave" type="button" title="Leave this node. No auto-heal.">Leave</button>
    </div>
    <p id="meshProducts">Catalog MCP mesh_* · FragGate slug=mesh · /v1/mesh/* PROXY · QNS-CD-1.0 cross-map · not AnonBroadcast · not AZMail ring · not a Node Gate · no public qnsd proxy</p>
  </div>
  <div class="card">
    <div class="nums">
      <p class="count">${v}<span>Views</span></p>
      <p class="count">${n}<span>Downloads</span></p>
    </div>
    <p class="kid"><strong>Two big buttons.</strong> Download saves the gzip (the Downloads number goes up). One-click install copies a Terminal command. After it finishes, type <code>azieltether ui</code>.</p>
    <div class="btns">
      <a class="btn primary dl" href="/download?asset=${DEFAULT_ASSET}">Download</a>
      <button type="button" class="btn install" id="install-btn">One-click install</button>
    </div>
    <pre id="install-cmd">${INSTALL_LINE}</pre>
    <p class="kid">Then run: <code>azieltether ui</code> and open http://127.0.0.1:8874 (this computer only).</p>
    <p class="meta">The download count ticks on the Download click. The Worker serves the gzip (HTTP 200). No 302 to GitHub. Forks using this same link are counted automatically. ${DEFAULT_ASSET} — ${n} counted.</p>
    <p class="iso">Isolated counter: Worker <code>azieltether-download-tracker</code>, project <code>${PROJECT}</code>, KV <code>AZIELTETHER_DOWNLOADS</code>. Not mixed with any other product. /v1 does not increment downloads.</p>
    <p class="meta">GitHub: stars ${gh.stars || 0} · forks ${gh.forks || 0} · watchers ${gh.watchers || 0} · release assets ${gh.release_download_count || 0}</p>
    <p class="meta">Apache-2.0 · Eliab, Aziel · <a href="${GITHUB_REPO}">GitHub</a></p>
    <p class="meta"><a href="/stats">JSON stats</a> · <a href="/openapi.json">OpenAPI</a> · <a href="/v1/mesh">/v1/mesh</a> · <a href="/v1/skill">Skill</a> · <a href="/v1/example">Example</a> · <a href="/ai">AI runtime</a> · <a href="/llms.txt">llms.txt</a> · <a href="${GITHUB_LATEST}">releases</a></p>
    <script>
      (function () {
        var cmd = "curl -fsSL https://azieltether-download-tracker.vibelock.workers.dev/install.sh | bash";
        var btn = document.getElementById("install-btn");
        var pre = document.getElementById("install-cmd");
        if (!btn) return;
        btn.addEventListener("click", function () {
          function done(ok) {
            btn.textContent = ok ? "Copied! Paste in Terminal, then run azieltether ui" : "Select the command, copy it, then run azieltether ui";
            btn.classList.add("copied");
          }
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(cmd).then(function () { done(true); }).catch(function () { done(false); });
          } else {
            done(false);
            if (pre && window.getSelection) {
              var r = document.createRange();
              r.selectNodeContents(pre);
              var sel = window.getSelection();
              sel.removeAllRanges();
              sel.addRange(r);
            }
          }
        });
      })();
      (function () {
        function $(id) { return document.getElementById(id); }
        function meshNum() {
          for (var i = 0; i < arguments.length; i++) {
            var raw = arguments[i];
            if (raw == null || raw === "") continue;
            var n = typeof raw === "number" ? raw : Number(String(raw).replace(/,/g, ""));
            if (Number.isFinite(n) && n >= 0) return Math.floor(n);
          }
          return 0;
        }
        function unwrapMesh(j) {
          if (!j || typeof j !== "object") return {};
          if (j.result && typeof j.result === "object") return Object.assign({}, j, j.result);
          if (j.mesh && typeof j.mesh === "object") return Object.assign({}, j, j.mesh);
          return j;
        }
        function paintMesh(raw) {
          var j = unwrapMesh(raw);
          var on = j.enabled === true || j.enabled === 1 || String(j.status || "").toLowerCase() === "on";
          var r = (j.rollup && typeof j.rollup === "object") ? j.rollup : {};
          var live = on ? meshNum(r.live, j.live_nodes, j.live) : 0;
          var locked = on ? meshNum(r.locked, j.locked_nodes, j.locked) : 0;
          var isolated = on ? meshNum(r.isolated, j.isolated_nodes, j.isolated) : 0;
          $("meshLiveCount").textContent = String(live);
          $("qnmLive").textContent = String(live);
          $("qnmLocked").textContent = String(locked);
          $("qnmIsolated").textContent = String(isolated);
          var line = $("meshLine");
          if (on) line.textContent = "Suite mesh: on · live " + live + " · locked " + locked + " · isolated " + isolated + ". Not an anonymity network.";
          else if (j.status === "unavailable" || (j.ok === false && j.error)) line.textContent = "Suite mesh: off (unavailable). QNM-BUILD-1.0. QNS-CD-1.0. Not an anonymity network.";
          else line.textContent = "Suite mesh: off (default). QNM-BUILD-1.0. QNS-CD-1.0. Not an anonymity network.";
          var products = j.products_present || j.products || [];
          var names = Array.isArray(products) ? products.map(function (p) { return typeof p === "string" ? p : (p && (p.product || p.slug)) || ""; }).filter(Boolean) : [];
          var nodes = Array.isArray(j.nodes) ? j.nodes : [];
          var extra = names.length ? " · products " + names.join(", ") : (nodes.length ? " · " + nodes.length + " node labels" : "");
          $("meshProducts").textContent = "Catalog MCP mesh_* · FragGate slug=mesh · /v1/mesh/* PROXY · QNS-CD-1.0 cross-map · not AnonBroadcast · not AZMail ring · not a Node Gate · no public qnsd proxy" + extra;
        }
        async function meshGet(path) {
          var r = await fetch(path, { headers: { "user-agent": "Mozilla/5.0", accept: "application/json" } });
          return r.json();
        }
        async function meshPost(path, payload) {
          var r = await fetch(path, { method: "POST", headers: { "content-type": "application/json", "user-agent": "Mozilla/5.0" }, body: JSON.stringify(payload || {}) });
          return r.json();
        }
        async function refreshMesh() {
          try {
            var status = await meshGet("/v1/mesh");
            var merged = status;
            var inner = unwrapMesh(status);
            var on = inner.enabled === true;
            if (on) {
              try {
                var nodes = await meshGet("/v1/mesh/nodes");
                merged = Object.assign({}, inner, unwrapMesh(nodes));
              } catch (e) { /* status is enough */ }
            }
            paintMesh(merged);
            var nodeId = sessionStorage.getItem("azieltether_mesh_node");
            if (on && nodeId) {
              try { await meshPost("/v1/mesh/heartbeat", { node_id: nodeId }); } catch (e) { /* no auto-heal */ }
            }
          } catch (e) {
            paintMesh({ ok: false, enabled: false, status: "unavailable", error: "mesh_unavailable" });
          }
        }
        $("meshEnable").onclick = async function () {
          var bearer = ($("meshBearer").value || "").trim();
          paintMesh(await meshPost("/v1/mesh/enable", bearer ? { bearer: bearer } : {}));
          refreshMesh();
        };
        $("meshDisable").onclick = async function () {
          sessionStorage.removeItem("azieltether_mesh_node");
          paintMesh(await meshPost("/v1/mesh/disable", {}));
          refreshMesh();
        };
        $("meshJoin").onclick = async function () {
          var j = await meshPost("/v1/mesh/join", { product: "azieltether", label: "AzielTether Worker" });
          var inner = unwrapMesh(j);
          var id = inner.node_id || inner.id || (inner.session && inner.session.node_id);
          if (id) sessionStorage.setItem("azieltether_mesh_node", String(id));
          paintMesh(j);
          refreshMesh();
        };
        $("meshLeave").onclick = async function () {
          var id = sessionStorage.getItem("azieltether_mesh_node");
          if (id) await meshPost("/v1/mesh/leave", { node_id: id });
          sessionStorage.removeItem("azieltether_mesh_node");
          refreshMesh();
        };
        window.addEventListener("pagehide", function () {
          var id = sessionStorage.getItem("azieltether_mesh_node");
          if (!id || typeof navigator.sendBeacon !== "function") return;
          try { navigator.sendBeacon("/v1/mesh/leave", new Blob([JSON.stringify({ node_id: id })], { type: "application/json" })); } catch (e) { /* leave expires in 5 minutes */ }
        });
        refreshMesh();
        setInterval(refreshMesh, 30000);
        document.addEventListener("visibilitychange", function () { if (!document.hidden) refreshMesh(); });
      })();
    </script>
    <h2>Per repo / branch / fork</h2>
    <ul>${breakdown}</ul>
  </div>
<section class="cite" id="cite">
  <h2>How to cite</h2>
  <p>Aziel Eliab. AzielTether. https://github.com/AzielEliab/azieltether. ${HOST}.</p>
  <p><a href="https://aziel-runtime.vibelock.workers.dev/">Catalog</a> · <a href="${GITHUB_REPO}">GitHub</a> · <a href="${HOST}/download">Download</a> · <a href="${HOST}/cite.json">cite.json</a></p>
</section>
<!-- /gitbaby-seo -->
</body>
</html>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const mesh = await handleMeshApi(request, url, env);
    if (mesh) return mesh;

    const runtime = await handleRuntimeApi(request, url);
    if (runtime) return runtime;

    if ((url.pathname === "/install.sh" || url.pathname === "/install.sh/") && request.method === "GET") {
      return new Response(installScript(), {
        status: 200,
        headers: {
          "Content-Type": "text/x-shellscript; charset=utf-8",
          "Cache-Control": "private, no-store",
          ...corsHeaders(),
        },
      });
    }

    if (url.pathname === "/" && request.method === "GET") {
      await incrementViews(env);
      return new Response(await indexHtml(env), {
        headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "private, no-store", ...corsHeaders() },
      });
    }

    if (url.pathname === "/count" && request.method === "GET") {
      const stats = await collectStats(env);
      return json({ project: PROJECT, views: stats.views || 0, downloads: stats.downloads || 0, total: stats.total || 0 });
    }

    if (url.pathname === "/stats" && request.method === "GET") {
      return json(await collectStats(env));
    }

    if (url.pathname === "/event" && request.method === "POST") {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: "JSON body required" }, 400);
      }
      const dims = parseDims(body || {});
      const count = await increment(env, dims);
      return json({
        ok: true,
        key: kvKey(dims),
        count,
        owner: dims.owner,
        repo: dims.repo,
        branch: dims.branch,
        fork: dims.fork,
        asset: dims.asset || null,
      });
    }

    if (url.pathname === "/go" && (request.method === "GET" || request.method === "HEAD")) {
      const dims = parseDims(url.searchParams);
      const asset = dims.asset || DEFAULT_ASSET;
      dims.asset = asset;
      if (request.method === "GET") await increment(env, dims);
      return serveAsset(request, env, asset, { head: request.method === "HEAD" });
    }

    if ((url.pathname === "/download" || url.pathname.startsWith("/download/")) && (request.method === "GET" || request.method === "HEAD")) {
      const dims = parseDims(url.searchParams);
      if (!dims.asset && url.pathname.startsWith("/download/")) {
        dims.asset = decodeURIComponent(url.pathname.slice("/download/".length));
      }
      const asset = dims.asset || DEFAULT_ASSET;
      dims.asset = asset;
      if (request.method === "GET") await increment(env, dims);
      return serveAsset(request, env, asset, { head: request.method === "HEAD" });
    }

    // gitbaby-seo-routes
    if ((url.pathname === "/robots.txt" || url.pathname === "/robots.txt/") && request.method === "GET") {
      return new Response(robotsTxt(), {
        status: 200,
        headers: { "Content-Type": "text/plain; charset=utf-8", ...corsHeaders() },
      });
    }
    if ((url.pathname === "/sitemap.xml" || url.pathname === "/sitemap.xml/") && request.method === "GET") {
      const locs = [HOST + "/", HOST + "/download", HOST + "/install.sh", HOST + "/v1/skill", HOST + "/v1/mesh", HOST + "/openapi.json", HOST + "/llms.txt", HOST + "/cite.json", GITHUB_REPO];
      const xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + locs.map((u) => "  <url><loc>" + u + "</loc></url>").join("\n")
        + "\n</urlset>\n";
      return new Response(xml, {
        status: 200,
        headers: { "Content-Type": "application/xml; charset=utf-8", ...corsHeaders() },
      });
    }
    if ((url.pathname === "/cite.json" || url.pathname === "/cite.json/") && request.method === "GET") {
      return json({
        author: "Aziel Eliab",
        title: "AzielTether",
        version: "0.1.0",
        github: GITHUB_REPO,
        download: HOST + "/download",
        license: "Apache-2.0",
        catalog: "https://aziel-runtime.vibelock.workers.dev/",
      });
    }
    if ((url.pathname === "/llms.txt" || url.pathname === "/llms.txt/" || url.pathname === "/ai.txt" || url.pathname === "/ai.txt/") && request.method === "GET") {
      return new Response(llmsTxt(), {
        status: 200,
        headers: { "Content-Type": "text/plain; charset=utf-8", ...corsHeaders() },
      });
    }
    // /gitbaby-seo-routes
    return json({ error: "not found" }, 404);
  },
};
