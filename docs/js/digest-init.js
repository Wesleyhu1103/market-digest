// Verdict feedback save
function saveVerdictFeedback() {
  const txt = document.getElementById('verdictFb').value.trim();
  if (!txt) return;
  const log = JSON.parse(localStorage.getItem('verdictFeedback') || '[]');
  log.push({ ts: new Date().toISOString(), date: mdEditionIso(), text: txt });
  localStorage.setItem('verdictFeedback', JSON.stringify(log));
  mdPost('/api/verdict-note', { date: mdEditionIso(), note: txt }).catch(function () {});
  document.getElementById('verdictFb').value = '';
  const sav = document.getElementById('vfSaved');
  if (sav) { sav.style.display = 'inline'; setTimeout(() => sav.style.display = 'none', 2200); }
}

// Theme toggle — re-applies tc() colors across all charts after a theme switch
(function() {
  const root = document.documentElement;
  const saved = localStorage.getItem('mktdig_theme') || 'light';
  // Fully rebuild every chart with fresh theme colors. This is more robust than
  // patching individual color props: it regenerates series, ticks, legend swatches,
  // axis labels and datalabels from the active theme's CSS tokens, so nothing is
  // left in a stale color that blends into the new background.
  const recolorCharts = () => {
    if (typeof _initAllCharts === 'function') _initAllCharts();
    (window._liveChartReloaders || []).forEach(function(fn) { try { fn(); } catch (_) {} });
  };
  const setTheme = (t) => {
    if (t === 'light') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', t);
    document.querySelectorAll('.theme-toggle button').forEach(b => b.classList.toggle('active', b.dataset.th === t));
    try { localStorage.setItem('mktdig_theme', t); } catch(_) {}
    requestAnimationFrame(() => requestAnimationFrame(recolorCharts));
  };
  setTheme(saved);
  document.querySelectorAll('.theme-toggle button').forEach(b => {
    b.addEventListener('click', () => setTheme(b.dataset.th));
  });
})();

// ── Cross-source consensus meters (rendered under each narrative) ────
(function renderConsensus() {
  const tag = document.getElementById('consensusData');
  if (!tag) return;
  let data; try { data = JSON.parse(tag.textContent); } catch (_) { return; }
  const leanLabel = l => l === 'neutral' ? 'Mixed' : (l.charAt(0).toUpperCase() + l.slice(1));
  const extSvg = '<svg class="ext" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8"/></svg>';
  Object.keys(data).forEach(key => {
    const nar = document.querySelector('.narrative[data-nar="' + key + '"]');
    if (!nar || nar.querySelector('.consensus')) return;
    const srcs = data[key].sources;
    const n = srcs.length;
    const bull = srcs.filter(s => s.lean === 'bull').length;
    const bear = srcs.filter(s => s.lean === 'bear').length;
    const neu = n - bull - bear;
    const pct = c => n ? Math.round(c / n * 100) : 0;
    const det = document.createElement('details');
    det.className = 'consensus';
    det.innerHTML =
      '<summary>' +
        '<span class="cs-label">Cross-source read</span>' +
        '<span class="cs-bar" role="img" aria-label="' + bull + ' bullish, ' + neu + ' mixed, ' + bear + ' bearish of ' + n + ' outlets">' +
          '<i class="bull" style="width:0%" data-w="' + pct(bull) + '"></i>' +
          '<i class="neu" style="width:0%" data-w="' + pct(neu) + '"></i>' +
          '<i class="bear" style="width:0%" data-w="' + pct(bear) + '"></i>' +
        '</span>' +
        '<span class="cs-counts">' + bull + 'B / ' + neu + 'M / ' + bear + 'Br</span>' +
      '</summary>' +
      '<div class="cs-body">' +
        '<div class="cs-scale"><span class="b">' + bull + ' bullish</span><span>' + neu + ' mixed</span><span class="r">' + bear + ' bearish</span></div>' +
        '<div class="cs-grid">' +
          srcs.map(s => '<a class="cs-src" href="' + s.url + '" target="_blank" rel="noopener noreferrer">' +
            '<div class="cs-src-top"><span class="cs-src-name">' + s.name + extSvg + '</span><span class="cs-lean ' + s.lean + '">' + leanLabel(s.lean) + '</span></div>' +
            '<div class="cs-src-take">' + s.take + '</div></a>').join('') +
        '</div>' +
        '<div class="cs-diverge">Where they diverge: ' + data[key].diverge + '</div>' +
      '</div>';
    const toggles = nar.querySelector('.toggles');
    if (toggles) nar.insertBefore(det, toggles); else nar.appendChild(det);
    det.addEventListener('toggle', () => {
      if (det.open) det.querySelectorAll('.cs-bar i').forEach(i => { i.style.width = i.dataset.w + '%'; });
    });
  });
})();

// ── Narrative Threads tracker + expandable timeline ──────────────────
(function narrativeThreads() {
  // Map sidebar threads to Week Scoreboard columns (1-indexed cell after Day)
  const THREADS = [
    { key: 'bonds', name: 'Stagflation / Rates', col: 1,
      blurb: { bull: 'Energy base effects seen rolling off; Treasury rally builds.', bear: 'Hot PPI/CPI confirmed; stagflation read hardens.', neu: 'Hot prices vs softening labor — no clean signal.' } },
    { key: 'iran', name: 'Iran / Oil', col: 2,
      blurb: { bull: 'De-escalation tape; crude drains its war premium.', bear: 'Disruption priced in — rerouting, Hormuz risk persist.', neu: 'On-again-off-again conflict; neither side resolved.' } },
    { key: 'aicapex', name: 'AI Capex / IPO', col: 3,
      blurb: { bull: 'SpaceX book swells; FOMO lifts the whole complex.', bear: 'Capex without proof of profit; software reversal.', neu: 'Split tape — euphoria meets the profitability test.' } }
  ];
  const todayLabel = (window.DigestDate && DigestDate.editionDayLabel()) || '';

  // Parse the Week Scoreboard table into per-thread day arrays
  function readScoreboard() {
    const rows = [...document.querySelectorAll('#weekTbody tr')];
    const days = rows.map(r => {
      const cells = [...r.children];
      const day = cells[0].textContent.trim();
      const reads = cells.slice(1).map(c => {
        const t = c.textContent.toLowerCase();
        if (t.includes('bull')) return 'bull';
        if (t.includes('bear')) return 'bear';
        return 'neu';
      });
      return { day, reads };
    });
    // Append today (live verdicts from the stacks, fall back to mixed)
    const liveMap = { bonds: 'bonds', iran: 'iran-oil', aicapex: 'ai-capex' };
    const liveRead = nk => {
      const stack = document.querySelector('.narrative-stack[data-narrative="' + liveMap[nk] + '"] .ns-verdict');
      if (!stack) return 'neu';
      const t = stack.textContent.toLowerCase();
      if (t.includes('bull')) return 'bull';
      if (t.includes('bear')) return 'bear';
      return 'neu';
    };
    days.push({ day: todayLabel, reads: THREADS.map(t => liveRead(t.key)), live: true });
    return days;
  }

  function leanClass(r) { return r; }
  function verdictText(r) { return r === 'bull' ? 'Bull confirmed' : r === 'bear' ? 'Bear confirmed' : 'Mixed'; }

  const days = readScoreboard();

  // Render compact rail
  const list = document.getElementById('trList');
  if (list) {
    list.innerHTML = THREADS.map((th, ti) => {
      const dots = days.map((d, di) =>
        '<span class="tr-dot ' + leanClass(d.reads[ti]) + (di === days.length - 1 ? ' today' : '') + '" title="' + d.day + ': ' + verdictText(d.reads[ti]) + '"></span>'
      ).join('');
      return '<button class="tr-thread" type="button" data-thread="' + ti + '">' +
        '<div class="tr-name">' + th.name + '</div><div class="tr-dots">' + dots + '</div></button>';
    }).join('');
  }

  // Drawer — scrim and panel are siblings (iOS fixed-position touch quirk)
  const scrim = document.getElementById('tlScrim');
  const drawer = document.getElementById('tlDrawer');
  const tabs = document.getElementById('tlTabs');
  const track = document.getElementById('tlTrack');
  let activeThread = 0;
  let scrollLockY = 0;
  function lockBodyScroll() {
    scrollLockY = window.scrollY;
    document.body.style.position = 'fixed';
    document.body.style.top = '-' + scrollLockY + 'px';
    document.body.style.left = '0';
    document.body.style.right = '0';
  }
  function unlockBodyScroll() {
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.left = '';
    document.body.style.right = '';
    window.scrollTo(0, scrollLockY);
  }

  function renderTimeline(ti) {
    activeThread = ti;
    tabs.querySelectorAll('.tl-tab').forEach((b, i) => b.classList.toggle('active', i === ti));
    const th = THREADS[ti];
    track.innerHTML = days.map(d => {
      const r = d.reads[ti];
      return '<div class="tl-node ' + r + (d.live ? ' today' : '') + '">' +
        '<span class="tl-day">' + d.day + (d.live ? ' · Today' : '') + '</span>' +
        '<span class="tl-verdict ' + r + '">' + verdictText(r) + '</span>' +
        '<h4>' + th.name + '</h4>' +
        '<p>' + th.blurb[r] + '</p></div>';
    }).join('');
    requestAnimationFrame(() => {
      track.querySelectorAll('.tl-node').forEach((n, i) => setTimeout(() => n.classList.add('in'), i * 80));
    });
  }

  if (tabs) tabs.innerHTML = THREADS.map((th, i) => '<button class="tl-tab" type="button" data-tab="' + i + '">' + th.name + '</button>').join('');

  function openDrawer(ti) {
    if (scrim.hidden) { scrim.hidden = false; drawer.hidden = false; scrim.setAttribute('aria-hidden', 'false'); }
    requestAnimationFrame(function() { scrim.classList.add('open'); drawer.classList.add('open'); });
    renderTimeline(ti != null ? ti : activeThread);
    lockBodyScroll();
  }
  function closeDrawer() {
    scrim.classList.remove('open');
    drawer.classList.remove('open');
    scrim.setAttribute('aria-hidden', 'true');
    unlockBodyScroll();
    setTimeout(function() { scrim.hidden = true; drawer.hidden = true; }, 280);
  }

  document.getElementById('trExpand') && document.getElementById('trExpand').addEventListener('click', () => openDrawer(0));
  list && list.addEventListener('click', e => {
    const btn = e.target.closest('.tr-thread');
    if (btn) openDrawer(parseInt(btn.dataset.thread, 10));
  });
  tabs && tabs.addEventListener('click', e => {
    const b = e.target.closest('.tl-tab');
    if (b) renderTimeline(parseInt(b.dataset.tab, 10));
  });
  document.getElementById('tlClose') && document.getElementById('tlClose').addEventListener('click', closeDrawer);
  scrim && scrim.addEventListener('click', closeDrawer);
  drawer && drawer.addEventListener('click', function(e) { e.stopPropagation(); });
  document.addEventListener('keydown', function(e) { if (e.key === 'Escape' && drawer && !drawer.hidden) closeDrawer(); });
})();

// ── Reader-facing freshness indicator ──────────────────────────────────
// The edition date is baked at generation. Show a live ET clock in the
// header so the page never looks frozen between builds, and flag clearly
// when the edition is behind today (weekend / late or failed publish)
// instead of presenting stale content as current. Lives in the static
// script, so the daily <main> regeneration never touches it.
(function () {
  var head = document.querySelector('header.head');
  var kicker = head && head.querySelector('.kicker');
  if (!head || !kicker || !window.DigestDate) return;
  var edition = DigestDate.headerEdition();
  if (!edition || !edition.iso) return;

  function etNow() {
    var now = new Date(), y = now.getFullYear();
    var dstStart = new Date(y, 2, 8 - new Date(y, 2, 1).getDay());
    var dstEnd = new Date(y, 10, 1 + (7 - new Date(y, 10, 1).getDay()) % 7);
    var off = (now >= dstStart && now < dstEnd) ? -4 : -5;
    return new Date(Date.now() + new Date().getTimezoneOffset() * 60000 + off * 3600000);
  }
  function num(y, mo, d) { return y * 10000 + mo * 100 + d; }

  var et = etNow();
  var isoParts = edition.iso.split('-');
  var editionNum = num(+isoParts[0], +isoParts[1], +isoParts[2]);
  var today = num(et.getFullYear(), et.getMonth() + 1, et.getDate());

  if (editionNum < today) {
    var banner = document.createElement('div');
    banner.className = 'stale-banner';
    banner.textContent = "You're reading the " + edition.weekday + ', ' + edition.month + ' ' + edition.day + ', ' + edition.year +
      " edition — today's digest hasn't published yet. Live prices and charts below are still current.";
    head.parentNode.insertBefore(banner, head);
  } else {
    var chip = document.createElement('span');
    chip.className = 'fresh-chip live';
    kicker.appendChild(chip);
    var tick = function () {
      chip.textContent = ' · Live ' +
        etNow().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) + ' ET';
    };
    tick();
    setInterval(tick, 30000);
  }
})();
