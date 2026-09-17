// API helpers — MD_VERCEL_ORIGIN comes from site-config.js (head).
function mdSitePath(rel) {
  var path = window.location.pathname || '/';
  var marker = '/archive/';
  var root;
  var archiveAt = path.indexOf(marker);
  if (archiveAt >= 0) {
    root = path.slice(0, archiveAt + 1);
  } else {
    root = path;
    if (/\.[a-z0-9]+$/i.test(root)) root = root.replace(/[^/]+$/, '');
    else if (!root.endsWith('/')) root += '/';
  }
  return root + String(rel || '').replace(/^\//, '');
}
window.mdSitePath = mdSitePath;

function mdUsesRemoteApi() {
  const h = location.hostname;
  return /\.github\.io$/i.test(h) || h === 'localhost' || h === '127.0.0.1';
}
function mdApiUrl(path) {
  return mdUsesRemoteApi() ? MD_VERCEL_ORIGIN + path : path;
}
function mdMacroFredUrl() {
  if (/\.github\.io$/i.test(location.hostname)) return mdSitePath('fred-data.json');
  return '/api/fred-data';
}
function mdPost(path, body) {
  return fetch(mdApiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    keepalive: true,
  });
}
function mdGet(path) {
  return fetch(mdApiUrl(path));
}

function mdVoterId() {
  const key = 'marketDigest_voterId';
  try {
    let id = localStorage.getItem(key);
    if (!id) {
      id = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now()) + Math.random().toString(36).slice(2);
      localStorage.setItem(key, id);
    }
    return id;
  } catch (_) {
    return 'anon';
  }
}

function mdVotesKey() {
  return 'marketDigest_proposalVotes';
}

function mdGetLocalVotes() {
  try { return JSON.parse(localStorage.getItem(mdVotesKey()) || '{}'); } catch (_) { return {}; }
}

function mdSetLocalVote(proposalId, voted) {
  const map = mdGetLocalVotes();
  if (voted) map[String(proposalId)] = true;
  else delete map[String(proposalId)];
  try { localStorage.setItem(mdVotesKey(), JSON.stringify(map)); } catch (_) {}
}
