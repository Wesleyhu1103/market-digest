// ============================================================
// NARRATIVE VERDICT LIVE UPDATER — uses window.MarketFeed for quotes
// Tier 1  -  Direction + Magnitude:  every 60 seconds
// Tier 2  -  Cross-asset:            every 5 minutes
// Tier 3  -  Sectors + Volatility:   every 15 minutes
// ============================================================
(function() {
  'use strict';

  if (!window.MarketFeed) return;

  var MF = window.MarketFeed;
  var cache = {};
  // Scorers read from `active` so the same 5-layer engine can score either
  // the live quote cache (verdict cards) or a historical day snapshot
  // (week scoreboard). Always reset to `cache` after use.
  var active = cache;
  var proxyFailures = 0;

  function fetchTicker(sym) {
    return MF.quote(sym)
      .then(function(q) {
        cache[sym] = q;
        proxyFailures = 0;
      })
      .catch(function(e) {
        proxyFailures++;
        console.warn('[verdict]', sym, e.message);
        if (proxyFailures >= 3 && document.getElementById('vaSub')) {
          document.getElementById('vaSub').textContent = 'Quote feed unavailable — retrying (' + MF.etStr() + ')';
        }
      });
  }

  function pctChg(sym)  { var d = active[sym]; if (!d || !d.prevClose) return null; return (d.price - d.prevClose) / d.prevClose * 100; }
  function bpsChg(sym)  { var d = active[sym]; if (!d || !d.prevClose) return null; return (d.price - d.prevClose) * 100; }
  function ptChg(sym)   { var d = active[sym]; if (!d || !d.prevClose) return null; return d.price - d.prevClose; }
  function px(sym)      { return active[sym] ? active[sym].price : null; }
  function scoreAllFrom(snapshot) {
    active = snapshot;
    try {
      return { bonds: scoreBonds(), oil: scoreOil(), ai: scoreAI() };
    } finally {
      active = cache;
    }
  }
  function sgn(v)       { return v > 0 ? '+' : ''; }
  function mkCell(n,s,v){ return { name: n, state: s, val: v }; }

  // BONDS: bull = yields cap/fall, bear = yields keep rising
  function scoreBonds() {
    var cells = [], bull = 0, bear = 0, mixed = 0;
    var tnxBps = bpsChg('^TNX'), tyxBps = bpsChg('^TYX');

    if (tnxBps === null) { cells.push(mkCell('1 · Direction','pending','loading…')); }
    else if (tnxBps > 0.5)  { cells.push(mkCell('1 · Direction','bear','+'+tnxBps.toFixed(0)+'bps 10Y')); bear++; }
    else if (tnxBps < -0.5) { cells.push(mkCell('1 · Direction','bull',tnxBps.toFixed(0)+'bps 10Y')); bull++; }
    else                    { cells.push(mkCell('1 · Direction','mixed','~flat 10Y')); mixed++; }

    if (tnxBps === null) { cells.push(mkCell('2 · Magnitude','pending','loading…')); }
    else {
      var abs2 = Math.abs(tnxBps), xtra2 = tyxBps !== null ? ' / 30Y:'+sgn(tyxBps)+tyxBps.toFixed(0)+'bps' : '';
      if (abs2 >= 3) { var d2 = tnxBps > 0 ? 'bear' : 'bull'; cells.push(mkCell('2 · Magnitude',d2,abs2.toFixed(0)+'bps move'+xtra2)); d2==='bear'?bear++:bull++; }
      else           { cells.push(mkCell('2 · Magnitude','mixed',abs2.toFixed(0)+'bps sub-threshold'+xtra2)); mixed++; }
    }

    var tltChg = pctChg('TLT');
    if (tltChg === null)    { cells.push(mkCell('3 · Cross-asset','pending','loading…')); }
    else if (tltChg < -0.4) { cells.push(mkCell('3 · Cross-asset','bear','TLT '+tltChg.toFixed(2)+'%')); bear++; }
    else if (tltChg > 0.4)  { cells.push(mkCell('3 · Cross-asset','bull','TLT +'+tltChg.toFixed(2)+'%')); bull++; }
    else                    { cells.push(mkCell('3 · Cross-asset','mixed','TLT ~flat '+sgn(tltChg)+tltChg.toFixed(2)+'%')); mixed++; }

    var xlkChg = pctChg('XLK'), xluChg = pctChg('XLU');
    if (xlkChg === null || xluChg === null) { cells.push(mkCell('4 · Sectors','pending','loading…')); }
    else if (xlkChg < -0.5 && xluChg > 0) { cells.push(mkCell('4 · Sectors','bear','XLK '+xlkChg.toFixed(1)+'% XLU +'+xluChg.toFixed(1)+'%')); bear++; }
    else if (xlkChg > 0.5  && xluChg < 0) { cells.push(mkCell('4 · Sectors','bull','XLK +'+xlkChg.toFixed(1)+'% growth bid')); bull++; }
    else                                   { cells.push(mkCell('4 · Sectors','mixed','XLK '+sgn(xlkChg)+xlkChg.toFixed(1)+'% XLU '+sgn(xluChg)+xluChg.toFixed(1)+'%')); mixed++; }

    var vPt = ptChg('^VIX'), vNow = px('^VIX');
    if (vPt === null)  { cells.push(mkCell('5 · Volatility','pending','loading…')); }
    else if (vPt > 1)  { cells.push(mkCell('5 · Volatility','bear','VIX +'+vPt.toFixed(1)+' → '+vNow.toFixed(1))); bear++; }
    else if (vPt < -1) { cells.push(mkCell('5 · Volatility','bull','VIX '+vPt.toFixed(1)+' → '+vNow.toFixed(1))); bull++; }
    else               { cells.push(mkCell('5 · Volatility','mixed','VIX ~flat '+vNow.toFixed(1))); mixed++; }

    return { cells: cells, bull: bull, bear: bear, mixed: mixed };
  }

  // IRAN/OIL: bull = oil rolls over (waiver), bear = oil stays high (blockade)
  function scoreOil() {
    var cells = [], bull = 0, bear = 0, mixed = 0;
    var bzChg = pctChg('BZ=F'), bzPx = px('BZ=F'), clChg = pctChg('CL=F');
    var spyChg = pctChg('SPY'), gldChg = pctChg('GLD'), xleChg = pctChg('XLE');

    if (bzChg === null)    { cells.push(mkCell('1 · Direction','pending','loading…')); }
    else if (bzChg > 0.3)  { cells.push(mkCell('1 · Direction','bear','Brent +'+bzChg.toFixed(2)+'% ($'+(bzPx?bzPx.toFixed(0):' - ')+')')); bear++; }
    else if (bzChg < -0.3) { cells.push(mkCell('1 · Direction','bull','Brent '+bzChg.toFixed(2)+'% ($'+(bzPx?bzPx.toFixed(0):' - ')+')')); bull++; }
    else                   { cells.push(mkCell('1 · Direction','mixed','Brent ~flat ($'+(bzPx?bzPx.toFixed(0):' - ')+')')); mixed++; }

    if (bzChg === null) { cells.push(mkCell('2 · Magnitude','pending','loading…')); }
    else {
      var abs3 = Math.abs(bzChg), xtra3 = clChg !== null ? ' WTI:'+sgn(clChg)+clChg.toFixed(1)+'%' : '';
      if (abs3 >= 2) { var d3 = bzChg > 0 ? 'bear' : 'bull'; cells.push(mkCell('2 · Magnitude',d3,abs3.toFixed(1)+'% move'+xtra3)); d3==='bear'?bear++:bull++; }
      else           { cells.push(mkCell('2 · Magnitude','mixed',abs3.toFixed(1)+'% sub-threshold'+xtra3)); mixed++; }
    }

    if (gldChg === null || spyChg === null) { cells.push(mkCell('3 · Cross-asset','pending','loading…')); }
    else if (bzChg !== null && bzChg > 0.5 && spyChg < -0.5 && gldChg > 0) { cells.push(mkCell('3 · Cross-asset','bear','SPY '+spyChg.toFixed(1)+'% GLD +'+gldChg.toFixed(1)+'%')); bear++; }
    else if (bzChg !== null && bzChg < -0.5 && spyChg > 0.3)                { cells.push(mkCell('3 · Cross-asset','bull','SPY +'+spyChg.toFixed(1)+'% oil softening')); bull++; }
    else                                                                      { cells.push(mkCell('3 · Cross-asset','mixed','SPY '+sgn(spyChg)+spyChg.toFixed(1)+'% GLD '+sgn(gldChg)+gldChg.toFixed(1)+'%')); mixed++; }

    if (xleChg === null || spyChg === null) { cells.push(mkCell('4 · Sectors','pending','loading…')); }
    else {
      var rel4 = xleChg - (spyChg || 0);
      if (rel4 > 0.75)      { cells.push(mkCell('4 · Sectors','bear','XLE outperforms SPY +'+rel4.toFixed(1)+'%')); bear++; }
      else if (rel4 < -0.75){ cells.push(mkCell('4 · Sectors','bull','XLE lags SPY '+rel4.toFixed(1)+'% (oil losing)')); bull++; }
      else                  { cells.push(mkCell('4 · Sectors','mixed','XLE vs SPY: '+sgn(rel4)+rel4.toFixed(1)+'%')); mixed++; }
    }

    var vPt = ptChg('^VIX'), vNow = px('^VIX');
    if (vPt === null)  { cells.push(mkCell('5 · Volatility','pending','loading…')); }
    else if (vPt > 1)  { cells.push(mkCell('5 · Volatility','bear','VIX +'+vPt.toFixed(1)+' → '+vNow.toFixed(1))); bear++; }
    else if (vPt < -1) { cells.push(mkCell('5 · Volatility','bull','VIX '+vPt.toFixed(1)+' → '+vNow.toFixed(1))); bull++; }
    else               { cells.push(mkCell('5 · Volatility','mixed','VIX ~flat '+vNow.toFixed(1))); mixed++; }

    return { cells: cells, bull: bull, bear: bear, mixed: mixed };
  }

  // AI CAPEX: bull = NVDA/QQQ up (structural), bear = rates kill multiples
  function scoreAI() {
    var cells = [], bull = 0, bear = 0, mixed = 0;
    var nvdaChg = pctChg('NVDA'), nvdaPx = px('NVDA'), qqqChg = pctChg('QQQ');
    var tnxBps = bpsChg('^TNX'), spyChg = pctChg('SPY'), smhChg = pctChg('SMH'), neeChg = pctChg('NEE');

    if (nvdaChg === null)    { cells.push(mkCell('1 · Direction','pending','loading…')); }
    else if (nvdaChg > 0.3)  { cells.push(mkCell('1 · Direction','bull','NVDA +'+nvdaChg.toFixed(2)+'% ($'+(nvdaPx?nvdaPx.toFixed(0):' - ')+')')); bull++; }
    else if (nvdaChg < -0.3) { cells.push(mkCell('1 · Direction','bear','NVDA '+nvdaChg.toFixed(2)+'% ($'+(nvdaPx?nvdaPx.toFixed(0):' - ')+')')); bear++; }
    else                     { cells.push(mkCell('1 · Direction','mixed','NVDA ~flat ($'+(nvdaPx?nvdaPx.toFixed(0):' - ')+')')); mixed++; }

    if (nvdaChg === null) { cells.push(mkCell('2 · Magnitude','pending','loading…')); }
    else {
      var abs5 = Math.abs(nvdaChg), xtra5 = qqqChg !== null ? ' QQQ:'+sgn(qqqChg)+qqqChg.toFixed(1)+'%' : '';
      if (abs5 >= 1) { var d5 = nvdaChg > 0 ? 'bull' : 'bear'; cells.push(mkCell('2 · Magnitude',d5,abs5.toFixed(1)+'% NVDA move'+xtra5)); d5==='bull'?bull++:bear++; }
      else           { cells.push(mkCell('2 · Magnitude','mixed','sub-1%'+xtra5)); mixed++; }
    }

    if (tnxBps === null || spyChg === null) { cells.push(mkCell('3 · Cross-asset','pending','loading…')); }
    else if (nvdaChg !== null && nvdaChg > 0 && tnxBps > 4)  { cells.push(mkCell('3 · Cross-asset','mixed','NVDA up but 10Y +'+tnxBps.toFixed(0)+'bps (fragile)')); mixed++; }
    else if (nvdaChg !== null && nvdaChg > 0 && tnxBps <= 2) { cells.push(mkCell('3 · Cross-asset','bull','NVDA up + rates stable')); bull++; }
    else if (nvdaChg !== null && nvdaChg < -0.5 && tnxBps > 3){ cells.push(mkCell('3 · Cross-asset','bear','Rates squeeze: 10Y +'+tnxBps.toFixed(0)+'bps')); bear++; }
    else                                                        { cells.push(mkCell('3 · Cross-asset','mixed','10Y '+sgn(tnxBps)+tnxBps.toFixed(0)+'bps SPY '+sgn(spyChg)+spyChg.toFixed(1)+'%')); mixed++; }

    if (smhChg === null || neeChg === null) { cells.push(mkCell('4 · Sectors','pending','loading…')); }
    else if (smhChg > 0.5  && neeChg > 0) { cells.push(mkCell('4 · Sectors','bull','SMH +'+smhChg.toFixed(1)+'% NEE +'+neeChg.toFixed(1)+'%')); bull++; }
    else if (smhChg < -0.5 && neeChg < 0) { cells.push(mkCell('4 · Sectors','bear','SMH '+smhChg.toFixed(1)+'% NEE '+neeChg.toFixed(1)+'%')); bear++; }
    else                                   { cells.push(mkCell('4 · Sectors','mixed','SMH '+sgn(smhChg)+smhChg.toFixed(1)+'% NEE '+sgn(neeChg)+neeChg.toFixed(1)+'%')); mixed++; }

    var vPt = ptChg('^VIX'), vNow = px('^VIX');
    if (vPt === null)  { cells.push(mkCell('5 · Volatility','pending','loading…')); }
    else if (vPt > 1)  { cells.push(mkCell('5 · Volatility','bear','VIX +'+vPt.toFixed(1)+' → '+vNow.toFixed(1))); bear++; }
    else if (vPt < -1) { cells.push(mkCell('5 · Volatility','bull','VIX '+vPt.toFixed(1)+' → '+vNow.toFixed(1))); bull++; }
    else               { cells.push(mkCell('5 · Volatility','mixed','VIX ~flat '+vNow.toFixed(1))); mixed++; }

    return { cells: cells, bull: bull, bear: bear, mixed: mixed };
  }

  // Verdict rules (shared framing with cellVerdict below):
  //   confirmed  = supermajority (4+ of 5) OR unopposed majority (3+ with zero
  //                dissenting layers) — layers 4-5 abstain to mixed most days,
  //                so demanding 4/5 alone made confirmation near-unreachable.
  //   lean       = net conviction of 2 layers (3v1, or 2v0 with abstentions).
  //   mixed      = |net| <= 1: genuinely contested (2v2) or thin signal.
  //                A single net layer never moves the verdict.
  // `lean` is stamped as data-lean for the Narrative Threads rail.
  function toVerdict(bull, bear, mixed) {
    var p = 5 - bull - bear - mixed;
    if (p >= 3) return { cls: 'pending', lean: 'pending', txt: 'Pending  -  awaiting data' };
    var net = bull - bear;
    if (bull >= 4 || (bull >= 3 && bear === 0))
      return { cls: 'confirmed', lean: 'bull', txt: '✓ Confirmed  -  ' + bull + ' green' + (bear ? ', ' + bear + ' red' : ', unopposed') };
    if (bear >= 4 || (bear >= 3 && bull === 0))
      return { cls: 'failed', lean: 'bear', txt: '✗ Failed  -  ' + bear + ' red' + (bull ? ', ' + bull + ' green' : ', unopposed') };
    if (net >= 2)  return { cls: 'tracking', lean: 'lean-bull', txt: 'Leaning bull  -  ' + bull + ' green vs ' + bear + ' red' };
    if (net <= -2) return { cls: 'tracking', lean: 'lean-bear', txt: 'Leaning bear  -  ' + bear + ' red vs ' + bull + ' green' };
    return { cls: 'fragile', lean: 'neu', txt: 'Mixed  -  contested (' + bull + 'G/' + bear + 'R/' + mixed + 'M)' };
  }

  // Tell listeners (Narrative Threads rail) that verdicts were repainted.
  function announce() {
    try { document.dispatchEvent(new CustomEvent('mktdig:verdicts-updated')); } catch (_) {}
  }

  function updateStack(key, score) {
    var stack = document.querySelector('.narrative-stack[data-narrative="' + key + '"]');
    if (!stack) return score;
    var cellEls = stack.querySelectorAll('.stack-cell');
    score.cells.forEach(function(c, i) {
      var el = cellEls[i]; if (!el) return;
      el.className = 'stack-cell ' + c.state;
      el.querySelector('.cell-name').textContent = c.name;
      el.querySelector('.cell-val').textContent  = c.val;
    });
    var v = toVerdict(score.bull, score.bear, score.mixed);
    var vEl = stack.querySelector('.ns-verdict');
    vEl.className = 'ns-verdict ' + v.cls;
    vEl.dataset.lean = v.lean;
    vEl.innerHTML = '<div class="v-label">Verdict</div>' + v.txt +
      ' <small style="opacity:.5;font-size:10px;font-style:normal">' + MF.asOfStr() + '</small>';
    return score;
  }

  function updateAggregate(scores) {
    var hEl = document.getElementById('vaHeadline'), sEl = document.getElementById('vaSub');
    if (!hEl || !sEl) return;
    var B = scores.reduce(function(s,r){return s+(r?r.bull:0);},0);
    var R = scores.reduce(function(s,r){return s+(r?r.bear:0);},0);
    var M = scores.reduce(function(s,r){return s+(r?r.mixed:0);},0);
    if (B+R+M < 3) return;
    var delta = B - R, h, s;
    if      (delta >=  6) { h = '<span class="bull">Broad risk-on</span>  -  bull layers dominant';  s = B+'/15 green. '+R+' red. '+MF.asOfStr(); }
    else if (delta <= -6) { h = '<span class="bear">Broad risk-off</span>  -  bear layers dominant'; s = R+'/15 red. '+B+' green. '+MF.asOfStr(); }
    else if (delta >   0) { h = '<span class="bull">Mild risk-on</span>  -  bull layers lead';       s = B+' bull / '+R+' bear / '+M+' mixed. '+MF.asOfStr(); }
    else if (delta <   0) { h = '<span class="bear">Mild risk-off</span>  -  bear layers lead';      s = R+' bear / '+B+' bull / '+M+' mixed. '+MF.asOfStr(); }
    else                  { h = 'Contested regime  -  no clear signal';                               s = B+' bull / '+R+' bear / '+M+' mixed. '+MF.asOfStr(); }
    hEl.innerHTML = h; sEl.textContent = s;
  }

  // ============================================================
  // WEEK SCOREBOARD — resolves the #weekTbody "Pending" cells at runtime.
  // Past days: scored from Yahoo daily close-to-close bars through the same
  // 5-layer engine, tagged with that day's press lean parsed from the
  // archived digest's consensusData (the morning pipeline's scraped-feed
  // read). Today: tracks the live quote cache during the session and
  // finalizes from the daily bar after the close. Future days stay Pending.
  // ============================================================
  var WeekBoard = (function() {
    var hist = {};        // sym -> [{d:'YYYY-MM-DD', v:close}, ...]
    var press = {};       // iso -> {bonds:'bull|bear|mixed', oil:..., ai:...} | null
    var rows = null;      // [{iso, tds:[td,td,td]}]
    var NARR = ['bonds', 'oil', 'ai'];
    var PRESS_KEYS = { bonds: ['bonds'], oil: ['iran', 'iran-oil'], ai: ['aicapex', 'ai-capex'] };

    function etToday() {
      return typeof mdEtTodayIso === 'function'
        ? mdEtTodayIso()
        : new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
    }
    function etHour() {
      return Number(new Date().toLocaleString('en-US', { timeZone: 'America/New_York', hour: 'numeric', hour12: false }));
    }
    function parseRows() {
      var tbody = document.getElementById('weekTbody');
      if (!tbody) return null;
      var out = [];
      var trs = tbody.querySelectorAll('tr');
      for (var i = 0; i < trs.length; i++) {
        var tds = trs[i].querySelectorAll('td');
        if (tds.length < 4) continue;
        var m = tds[0].textContent.match(/(\d+)\/(\d+)/);
        if (!m) continue;
        var iso = typeof mdScoreboardRowIso === 'function'
          ? mdScoreboardRowIso(tds[0].textContent)
          : etToday().slice(0, 4) + '-' + String(m[1]).padStart(2, '0') + '-' + String(m[2]).padStart(2, '0');
        out.push({
          iso: iso,
          tds: [tds[1], tds[2], tds[3]]
        });
      }
      return out.length ? out : null;
    }

    function majorityLean(sources) {
      var bull = 0, bear = 0, n = 0;
      (sources || []).forEach(function(s) {
        n++;
        if (s.lean === 'bull') bull++;
        else if (s.lean === 'bear') bear++;
      });
      if (!n) return null;
      if (bull > n / 2) return 'bull';
      if (bear > n / 2) return 'bear';
      return 'mixed';
    }
    function parseConsensus(html) {
      var m = html && html.match(/<script type="application\/json" id="consensusData">([\s\S]*?)<\/script>/);
      if (!m) return null;
      var data;
      try { data = JSON.parse(m[1]); } catch (_) { return null; }
      var out = {};
      NARR.forEach(function(k) {
        var keys = PRESS_KEYS[k];
        for (var i = 0; i < keys.length; i++) {
          if (data[keys[i]]) { out[k] = majorityLean(data[keys[i]].sources); return; }
        }
        out[k] = null;
      });
      return out;
    }
    function loadPress(iso) {
      if (iso in press) return Promise.resolve(press[iso]);
      var p;
      if (iso === etToday() || (window.DigestDate && (DigestDate.headerEdition() || {}).iso === iso)) {
        var el = document.getElementById('consensusData');
        p = Promise.resolve(el ? parseConsensus('<script type="application/json" id="consensusData">' + el.textContent + '</script>') : null);
      } else {
        var url = typeof mdSitePath === 'function' ? mdSitePath('archive/' + iso + '.html') : 'archive/' + iso + '.html';
        p = fetch(url, { cache: 'force-cache' })
          .then(function(r) { return r.ok ? r.text() : null; })
          .then(function(html) { return html ? parseConsensus(html) : null; })
          .catch(function() { return null; });
      }
      return p.then(function(v) { press[iso] = v; return v; });
    }

    function loadHistory() {
      var syms = TIER1.concat(TIER2, TIER3);
      return Promise.all(syms.map(function(sym) {
        return MF.series(sym, '1mo', '1d')
          .then(function(s) { hist[sym] = s; })
          .catch(function() { /* keep any previous history for this sym */ });
      }));
    }
    // Close-to-close snapshot for one ET day, built from the daily bars.
    function daySnapshot(iso) {
      var snap = {}, found = 0;
      var syms = TIER1.concat(TIER2, TIER3);
      syms.forEach(function(sym) {
        var bars = hist[sym];
        if (!bars) return;
        for (var i = 0; i < bars.length; i++) {
          if (bars[i].d === iso) {
            if (i > 0) { snap[sym] = { price: bars[i].v, prevClose: bars[i - 1].v }; found++; }
            return;
          }
        }
      });
      return found ? snap : null;
    }

    // Label from raw layer counts — same framing as toVerdict:
    // confirmed = supermajority or unopposed majority; lean = net 2 layers;
    // mixed = |net| <= 1 (contested or thin signal), not "anything short
    // of supermajority" as before.
    function cellVerdict(score) {
      var resolved = score.bull + score.bear + score.mixed;
      if (resolved < 3) return null;
      var net = score.bull - score.bear;
      if (score.bull >= 4 || (score.bull >= 3 && score.bear === 0)) return { key: 'bull', word: '✓ Bull', color: 'var(--bull)' };
      if (score.bear >= 4 || (score.bear >= 3 && score.bull === 0)) return { key: 'bear', word: '✗ Bear', color: 'var(--bear)' };
      if (net >= 2)  return { key: 'lean-bull', word: 'Bull lean', color: 'var(--bull)' };
      if (net <= -2) return { key: 'lean-bear', word: 'Bear lean', color: 'var(--bear)' };
      return { key: 'mixed', word: 'Mixed', color: 'var(--muted)' };
    }
    function paintCell(td, score, pressLean, liveTag) {
      var v = cellVerdict(score);
      if (!v) { td.dataset.verdict = 'pending'; return null; }
      td.dataset.verdict = v.key;
      var detail = score.bull + 'G/' + score.bear + 'R';
      if (pressLean) detail += ' · press ' + pressLean;
      if (liveTag) detail += ' · live';
      td.innerHTML = '<span style="color:' + v.color + ';font-weight:700;">' + v.word + '</span>'
        + ' <small style="color:var(--muted);">' + detail + '</small>';
      td.title = score.bull + ' bull / ' + score.bear + ' bear / ' + score.mixed + ' mixed layers'
        + (pressLean ? ' · morning press read: ' + pressLean : '')
        + (liveTag ? ' · live, finalizes at 4pm ET' : '');
      return v.key;
    }
    function paintSummary(finalKeys) {
      var bull = 0, bear = 0, mixed = 0;
      finalKeys.forEach(function(k) {
        if (k === 'bull') bull++;
        else if (k === 'bear') bear++;
        else mixed++;
      });
      var total = bull + bear + mixed;
      var set = function(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; };
      set('ssRight', bull);
      set('ssWrong', bear);
      set('ssMixed', mixed);
      set('ssRate', total ? Math.round(bear / total * 100) + '%' : '0%');
    }

    function dayState(iso) {
      var today = etToday();
      var anchor = typeof mdScoreboardAnchorIso === 'function' ? mdScoreboardAnchorIso() : today;
      if (anchor < today) {
        return iso <= anchor ? 'final' : 'future';
      }
      if (iso < today) return 'final';
      if (iso > today) return 'future';
      var phase = MF.sessionPhase();
      if (phase === 'live') return 'live';
      if (phase === 'after-hours' || (phase === 'closed' && etHour() >= 16) || phase === 'weekend') return 'final';
      return 'future'; // pre-market / overnight before today's open
    }

    function render() {
      if (!rows) rows = parseRows();
      if (!rows) return;
      var finalKeys = [];
      var chain = Promise.resolve();
      rows.forEach(function(row) {
        var state = dayState(row.iso);
        if (state === 'future') return;
        var snap = state === 'live' ? cache : daySnapshot(row.iso);
        if (!snap) return;
        chain = chain.then(function() { return loadPress(row.iso); }).then(function(pr) {
          var scores = scoreAllFrom(snap);
          NARR.forEach(function(k, i) {
            var key = paintCell(row.tds[i], scores[k], pr && pr[k], state === 'live');
            if (key && state === 'final') finalKeys.push(key);
          });
          if (state === 'final') paintSummary(finalKeys);
        });
      });
      return chain.then(announce);
    }

    function boot() {
      rows = parseRows();
      if (!rows) return;
      loadHistory().then(render);
      // Re-pull daily bars every 15 min: catches today's bar finalizing
      // after the close and keeps the board honest after hours too.
      setInterval(function() {
        if (document.hidden) return;
        loadHistory().then(render);
      }, 15 * 60 * 1000);
    }

    return { boot: boot, render: render };
  })();

  var TIER1 = ['^TNX','^TYX','BZ=F','NVDA','TLT','QQQ'];
  var TIER2 = ['^VIX','SPY','GLD','CL=F'];
  var TIER3 = ['XLE','XLK','XLU','NEE','SMH'];

  function runScoring() {
    updateAggregate([
      updateStack('bonds',    scoreBonds()),
      updateStack('iran-oil', scoreOil()),
      updateStack('ai-capex', scoreAI())
    ]);
    // keep the scoreboard's live (today) row in step with the cards
    try { WeekBoard.render(); } catch (_) {}
    announce();
  }

  function fetchAndScore(tickers) {
    Promise.all(tickers.map(fetchTicker)).then(runScoring);
  }

  function refreshAll() {
    var open = MF.isMarketOpen();
    fetchAndScore(open ? TIER1 : TIER1.concat(TIER2, TIER3));
  }

  Promise.all(TIER1.concat(TIER2, TIER3).map(fetchTicker)).then(function() {
    runScoring();
    WeekBoard.boot();
    setInterval(function(){ if (MF.isMarketOpen()) fetchAndScore(TIER1); },  60 * 1000);
    setInterval(function(){ if (MF.isMarketOpen()) fetchAndScore(TIER2); },   5 * 60 * 1000);
    setInterval(function(){ if (MF.isMarketOpen()) fetchAndScore(TIER3); },  15 * 60 * 1000);
    setInterval(function(){ if (!MF.isMarketOpen()) refreshAll(); }, 10 * 60 * 1000);
  });

})();
