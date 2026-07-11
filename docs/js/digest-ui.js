// Sticky nav active-section
const tocLinks = document.querySelectorAll('nav.toc a');
function navSections() {
  return document.querySelectorAll('main section, #archive');
}
function onScroll() {
  const sections = navSections();
  if (!sections.length) return;
  let cur = sections[0].id;
  for (const s of sections) {
    if (s.getBoundingClientRect().top < 120) cur = s.id;
  }
  tocLinks.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + cur));
}
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();
document.querySelector('nav.toc a[href="#archive"]')?.addEventListener('click', function(e) {
  const target = document.getElementById('archive');
  if (!target) return;
  e.preventDefault();
  target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  history.replaceState(null, '', '#archive');
  onScroll();
});

function mdEditionIso() {
  return (window.DigestDate && DigestDate.editionIso && DigestDate.editionIso()) || '';
}

// Bull/Bear toggle — delegated so taps work reliably on mobile
document.addEventListener('click', function(e) {
  const btn = e.target.closest('.narrative .toggles button, .buyside-summary .toggles button');
  if (!btn) return;
  const n = btn.closest('.narrative, .buyside-summary');
  const bb = n && n.querySelector('.bullbear');
  if (!bb) return;
  n.querySelectorAll('.toggles button').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  bb.classList.remove('show-bull', 'show-bear');
  const side = btn.dataset.side;
  if (side === 'bull') bb.classList.add('show-bull');
  if (side === 'bear') bb.classList.add('show-bear');
});

// Quiz (case-insensitive; accepts data-opt or mistaken data-val on .opt only)
document.querySelectorAll('.quiz .q').forEach((q, qi) => {
  const correct = String(q.dataset.correct || '').toLowerCase();
  q.querySelectorAll('.opt').forEach(opt => {
    opt.addEventListener('click', () => {
      if (q.classList.contains('answered')) return;
      q.classList.add('answered');
      const pick = String(opt.dataset.opt || opt.dataset.val || '').toLowerCase();
      const isRight = !!pick && pick === correct;
      if (isRight) opt.classList.add('correct');
      else {
        opt.classList.add('wrong');
        const right = q.querySelector('.opt[data-opt="' + correct + '"], .opt[data-val="' + correct + '"]');
        if (right) right.classList.add('correct');
      }
      mdPost('/api/quiz', { date: mdEditionIso(), questionIndex: qi, picked: pick, correct: correct, isCorrect: isRight }).catch(function () {});
    });
  });
});

// Feedback form: button toggles
document.querySelectorAll('form.fb .opts').forEach(group => {
  const multi = group.dataset.multi === '1';
  group.querySelectorAll('button').forEach(b => {
    b.addEventListener('click', () => {
      if (!multi) group.querySelectorAll('button').forEach(x => x.classList.remove('on'));
      b.classList.toggle('on');
    });
  });
});

function gatherFeedback() {
  const out = { date: mdEditionIso(), submittedAt: new Date().toISOString() };
  document.querySelectorAll('form.fb .opts').forEach(group => {
    const key = group.dataset.group;
    const multi = group.dataset.multi === '1';
    const sel = Array.from(group.querySelectorAll('button.on')).map(b => b.dataset.val);
    out[key] = multi ? sel : (sel[0] || null);
  });
  out.missing = document.getElementById('fb-missing').value;
  out.open = document.getElementById('fb-open').value;
  return out;
}

async function submitFeedback(e) {
  e.preventDefault();
  const data = gatherFeedback();
  const el = document.getElementById('fb-success');
  if (!String(data.missing || '').trim() && !String(data.open || '').trim()) return false;
  el.classList.remove('fb-error');
  try { localStorage.setItem('marketDigest_feedback_' + (data.date || 'unknown'), JSON.stringify(data)); } catch(_) {}
  let ok = false;
  try {
    const res = await mdPost('/api/feedback', data);
    ok = res && (res.ok || res.status === 204);
  } catch (_) {}
  el.textContent = ok ? 'Thanks -- feedback saved!' : 'Could not save — check your connection and try again.';
  el.classList.toggle('fb-error', !ok);
  el.style.display = 'block';
  return false;
}

// Bind the submit handler. Without this the form did a native GET submission
// (dumping the fields into the URL), so nothing was ever saved.
document.getElementById('fb-form')?.addEventListener('submit', submitFeedback);

// Community votes board
(function initCommunityVotes() {
  const board = document.getElementById('cv-board');
  if (!board) return;

  function render(data) {
    const localVotes = mdGetLocalVotes();
    const cats = data.categories || [];
    const labels = data.labels || {};
    const proposals = data.proposals || {};
    let total = 0;
    cats.forEach(c => { total += (proposals[c] || []).length; });
    if (!total) {
      board.innerHTML = '<p class="cv-empty">No open votes yet — check back soon.</p>';
      return;
    }
    let html = '';
    cats.forEach(cat => {
      const items = proposals[cat] || [];
      if (!items.length) return;
      html += '<div class="cv-group"><div class="cv-group-h">' + (labels[cat] || cat) + '</div>';
      items.forEach(p => {
        const voted = !!localVotes[String(p.id)];
        html += '<div class="cv-card" data-id="' + p.id + '">'
          + '<div class="cv-vote"><button type="button" class="cv-up' + (voted ? ' on' : '') + '" aria-label="Upvote" title="Upvote">▲</button>'
          + '<span class="cv-count">' + (p.voteCount || 0) + '</span></div>'
          + '<div class="cv-body"><div class="cv-title">' + escapeHtml(p.title) + '</div>'
          + (p.summary ? '<p class="cv-summary">' + escapeHtml(p.summary) + '</p>' : '')
          + '</div></div>';
      });
      html += '</div>';
    });
    board.innerHTML = html;
    board.querySelectorAll('.cv-up').forEach(btn => {
      btn.addEventListener('click', async function() {
        const card = btn.closest('.cv-card');
        const id = Number(card && card.dataset.id);
        if (!id) return;
        const wasOn = btn.classList.contains('on');
        const action = wasOn ? 'remove' : 'upvote';
        btn.disabled = true;
        try {
          const res = await mdPost('/api/proposals-vote', { proposalId: id, action, voterId: mdVoterId() });
          if (!res.ok) throw new Error('vote failed');
          const out = await res.json();
          btn.classList.toggle('on', !wasOn);
          mdSetLocalVote(id, !wasOn);
          const countEl = card.querySelector('.cv-count');
          if (countEl && out.voteCount != null) countEl.textContent = out.voteCount;
          else if (countEl) {
            const n = parseInt(countEl.textContent, 10) || 0;
            countEl.textContent = Math.max(0, n + (wasOn ? -1 : 1));
          }
        } catch (_) {
          /* keep UI unchanged on failure */
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  mdGet('/api/proposals').then(r => r.ok ? r.json() : null).then(data => {
    if (data) render(data);
    else board.innerHTML = '<p class="cv-empty">Could not load votes — try again later.</p>';
  }).catch(() => {
    board.innerHTML = '<p class="cv-empty">Could not load votes — try again later.</p>';
  });
})();
