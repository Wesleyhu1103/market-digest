const MD_API_ORIGIN = 'https://market-digest-liart.vercel.app';
function mdUsesRemoteApi() {
  const h = location.hostname;
  return /\.github\.io$/i.test(h) || h === 'localhost' || h === '127.0.0.1';
}
function mdApiUrl(path) {
  return mdUsesRemoteApi() ? MD_API_ORIGIN + path : path;
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
