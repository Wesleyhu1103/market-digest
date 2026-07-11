// API helpers — MD_VERCEL_ORIGIN comes from site-config.js (head).
function mdUsesRemoteApi() {
  const h = location.hostname;
  return /\.github\.io$/i.test(h) || h === 'localhost' || h === '127.0.0.1';
}
function mdApiUrl(path) {
  return mdUsesRemoteApi() ? MD_VERCEL_ORIGIN + path : path;
}
function mdSitePath(rel) {
  var path = window.location.pathname || '/';
  if (/\.[a-z0-9]+$/i.test(path)) path = path.replace(/[^/]+$/, '');
  else if (!path.endsWith('/')) path += '/';
  var archiveIdx = path.indexOf('/archive/');
  if (archiveIdx !== -1) path = path.slice(0, archiveIdx + 1);
  return path + String(rel || '').replace(/^\//, '');
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
