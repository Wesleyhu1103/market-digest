// API helpers — MD_VERCEL_ORIGIN comes from site-config.js (head).
function mdUsesRemoteApi() {
  const h = location.hostname;
  return /\.github\.io$/i.test(h) || h === 'localhost' || h === '127.0.0.1';
}
function mdApiUrl(path) {
  return mdUsesRemoteApi() ? MD_VERCEL_ORIGIN + path : path;
}
function mdSitePath(rel) {
  var raw = String(rel || '');
  if (/^(https?:)?\/\//i.test(raw)) return raw;
  var clean = raw.replace(/^\//, '');
  var path = (window.location && window.location.pathname) || '/';
  var archiveAt = path.indexOf('/archive/');
  if (archiveAt >= 0) {
    return path.slice(0, archiveAt + 1) + clean;
  }
  if (/\.[a-z0-9]+$/i.test(path)) path = path.replace(/[^/]+$/, '');
  else if (!path.endsWith('/')) path += '/';
  return path + clean;
}
function mdEtTodayIso() {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
}
function mdEditionIso() {
  var ed = window.DigestDate && DigestDate.headerEdition && DigestDate.headerEdition();
  return ed && ed.iso ? ed.iso : '';
}
function mdScoreboardAnchorIso() {
  var editionIso = mdEditionIso();
  var todayIso = mdEtTodayIso();
  return editionIso && editionIso < todayIso ? editionIso : todayIso;
}
function mdScoreboardRowIso(dayText, editionIso) {
  var m = String(dayText || '').match(/(\d+)\/(\d+)/);
  if (!m) return '';
  var month = Number(m[1]);
  var day = Number(m[2]);
  var anchor = editionIso || mdEditionIso() || mdEtTodayIso();
  var year = Number(anchor.slice(0, 4));
  var anchorMonth = Number(anchor.slice(5, 7));
  if (year && anchorMonth) {
    if (month - anchorMonth > 6) year -= 1;
    else if (anchorMonth - month > 6) year += 1;
  }
  return year + '-' + String(month).padStart(2, '0') + '-' + String(day).padStart(2, '0');
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
