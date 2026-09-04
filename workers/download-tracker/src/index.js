import { handleRuntimeApi } from "./runtime.js";
import { corsHeaders, handleTetherApi, json } from "./tether.js";

/**
 * AzielTether download tracker (Cloudflare Worker).
 * Counted /download serves gzip via ASSETS.fetch (HTTP 200, no 302).
 * Tether bootstrap APIs are a directory + holding pen — not a full mesh.
 * Author: Aziel Eliab.
 */

const PROJECT = "azieltether";
const DEFAULT_ASSET = "azieltether-0.1.0.tar.gz";
const DEFAULT_OWNER = "AzielEliab";
const DEFAULT_REPO = "azieltether";
const DEFAULT_BRANCH = "main";
const HOST = "https://azieltether-download-tracker.vibelock.workers.dev";
const GITHUB_REPO = "https://github.com/AzielEliab/azieltether";
const CATALOG = "https://aziel-runtime.vibelock.workers.dev/";
const INSTALL_LINE = `curl -fsSL ${HOST}/install.sh | bash`;

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

function viewsKey() {
  return PROJECT + "|__views__";
}

function totalKey() {
  return PROJECT + "|__total__";
}

function githubCacheKey() {
  return PROJECT + "|__github__";
}

async function increment(env, dims) {
  const key = kvKey(dims);
  const n = parseInt((await env.DOWNLOADS.get(key)) || "0", 10) + 1;
  await env.DOWNLOADS.put(key, String(n));
  const total = parseInt((await env.DOWNLOADS.get(totalKey())) || "0", 10) + 1;
  await env.DOWNLOADS.put(totalKey(), String(total));
  return n;
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
      if (obj && obj.fetched_at && Date.now() - obj.fetched_at < 5 * 60 * 1000) return obj;
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
  let total = 0;
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
    total += n;
    const repoId = `${owner}/${repo}`;
    by_repo[repoId] = (by_repo[repoId] || 0) + n;
    by_branch[branch] = (by_branch[branch] || 0) + n;
    const forkFlag = fork === "1" ? "1" : "0";
    by_fork[forkFlag] = (by_fork[forkFlag] || 0) + n;
    breakdown.push({ project, owner, repo, branch, fork: forkFlag, count: n });
  }
  const totalDirect = parseInt((await env.DOWNLOADS.get(totalKey())) || "0", 10);
  const views = parseInt((await env.DOWNLOADS.get(viewsKey())) || "0", 10) || 0;
  const github = await githubStats(env);
  const shown = Number.isFinite(totalDirect) && totalDirect > 0 ? totalDirect : total;
  return {
    project: PROJECT,
    total: shown,
    views,
    downloads: shown,
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
    note: "Forks identified by GitHub owner/repo. /v1 does not increment.",
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
DIR="\$(find . -maxdepth 2 -type d -name 'azieltether-*' | head -n 1)"
if [ -n "\${DIR}" ]; then
  cd "\${DIR}"
fi
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
echo
echo "Installed AzielTether."
echo "Run: azieltether doctor"
echo "Then: azieltether serve"
echo "Open http://127.0.0.1:19740 (this computer only)"
echo "Author: Aziel Eliab."
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
  if (head) return new Response(null, { status: 200, headers });
  return new Response(assetRes.body, { status: 200, headers });
}

async function indexHtml(env) {
  const stats = await collectStats(env);
  const views = Number(stats.views) || 0;
  const downloads = Number(stats.downloads != null ? stats.downloads : stats.total) || 0;
  const v = views.toLocaleString("en-US");
  const n = downloads.toLocaleString("en-US");
  const gh = stats.github || {};
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AzielTether downloads</title>
  <style>
    :root { color-scheme: dark; }
    body { font: 16px/1.45 system-ui, sans-serif; max-width: 42rem; margin: 3rem auto; padding: 0 1.25rem 4rem; background: #0e1014; color: #e8eaef; }
    h1 { font-size: 1.75rem; margin: 0 0 .35rem; }
    .motto { color: #9aa3b2; margin: 0 0 1.5rem; }
    .card { border: 1px solid #2a3140; border-radius: 12px; padding: 1.25rem 1.35rem; background: #151922; }
    .nums { display: grid; grid-template-columns: 1fr 1fr; gap: .8rem; margin: 0 0 1rem; }
    .count { font-size: 2.2rem; font-variant-numeric: tabular-nums; font-weight: 700; margin: 0; }
    .count span { display: block; font-size: .95rem; font-weight: 500; color: #9aa3b2; }
    .btns { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; margin: 0 0 .85rem; }
    @media (max-width: 520px) { .btns { grid-template-columns: 1fr; } }
    a.btn, button.btn { display: block; width: 100%; box-sizing: border-box; text-align: center; font: inherit; font-size: 1.2rem; font-weight: 750; padding: 1rem 1.1rem; border-radius: 10px; border: 0; cursor: pointer; text-decoration: none; }
    a.btn.primary { background: #e8eaef; color: #0e1014; }
    button.btn.install { background: #c9a227; color: #14110a; }
    button.btn.install.copied { background: #7dcf9a; color: #0e1014; }
    .kid { font-size: 1.05rem; margin: 0 0 1rem; }
    .meta { margin-top: 1.1rem; color: #9aa3b2; font-size: .92rem; }
    .meta a { color: #c9d4ff; }
    .banner { border: 1px solid #5c4a1a; background: #241c0d; color: #f0d78c; padding: .85rem 1rem; border-radius: 8px; margin: 0 0 1.2rem; font-size: .92rem; }
    pre { background: #0e1014; padding: .75rem .9rem; overflow: auto; border-radius: 8px; font-size: .82rem; }
  </style>
</head>
<body>
  <h1>AzielTether</h1>
  <p class="motto">Central × decentral software tether. Author Aziel Eliab.</p>
  <p class="banner">THIS IS: a homework folder for software. If the main office is closed, classmates who already downloaded the folder can still trade work. When the office opens, everyone turns the folder in. THIS IS NOT: a VPN or secret network. Public websites stay ordinary HTTPS. This Worker is a sign-in sheet and a holding bin — not the whole mesh.</p>
  <div class="card">
    <div class="nums">
      <p class="count">${v}<span>Views</span></p>
      <p class="count">${n}<span>Downloads</span></p>
    </div>
    <p class="kid">Two big buttons. Download saves the gzip (the Downloads number goes up). One-click install copies a Terminal command. After it finishes, type <code>azieltether serve</code> and open http://127.0.0.1:19740.</p>
    <div class="btns">
      <a class="btn primary" href="/download?asset=${DEFAULT_ASSET}">Download</a>
      <button class="btn install" id="install-btn" type="button">One-click install</button>
    </div>
    <pre id="install-cmd">${INSTALL_LINE}</pre>
    <p class="meta">Then run: <code>azieltether doctor</code> and <code>azieltether serve</code>. Isolated counter: Worker azieltether-download-tracker, KV AZIELTETHER_DOWNLOADS. /v1 does not increment.</p>
    <p class="meta">GitHub: stars ${gh.stars || 0} · forks ${gh.forks || 0} · watchers ${gh.watchers || 0}</p>
    <p class="meta"><a href="${GITHUB_REPO}">GitHub</a> · <a href="${HOST}/download">${HOST}/download</a> · <a href="${CATALOG}">catalog</a> · <a href="/openapi.json">OpenAPI</a> · <a href="/v1/skill">Skill</a> · <a href="/cite.json">cite</a> · Apache-2.0 · Eliab, Aziel</p>
  </div>
  <script>
    (function () {
      var cmd = ${JSON.stringify(INSTALL_LINE)};
      var btn = document.getElementById("install-btn");
      var pre = document.getElementById("install-cmd");
      if (!btn) return;
      btn.addEventListener("click", function () {
        function done(ok) {
          btn.textContent = ok ? "Copied! Paste in Terminal, then run azieltether serve" : "Select the command, copy it, then run azieltether serve";
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
  </script>
</body>
</html>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

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

    const tether = await handleTetherApi(request, url, env);
    if (tether) return tether;

    const runtime = await handleRuntimeApi(request, url);
    if (runtime) return runtime;

    if (url.pathname === "/" && request.method === "GET") {
      await incrementViews(env);
      return new Response(await indexHtml(env), {
        headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "private, no-store", ...corsHeaders() },
      });
    }

    if (url.pathname === "/count" && request.method === "GET") {
      const stats = await collectStats(env);
      return json({ project: PROJECT, total: stats.total || 0 });
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

    return json({ error: "not found" }, 404);
  },
};
