// ============================================================
// NARRATIVE VERDICT LIVE UPDATER
// Yahoo Finance via CORS proxy chain (GitHub Pages)
// Tier 1  -  Direction + Magnitude:  every 60 seconds
// Tier 2  -  Cross-asset:            every 5 minutes
// Tier 3  -  Sectors + Volatility:   every 15 minutes
// ============================================================
(function() {
  'use strict';

  var YF_BASE = 'https://query1.finance.yahoo.com/v8/finance/chart/';
  // Our own cached Yahoo proxy (Vercel serverless fn) is tried first; it's far
  // more reliable than the public proxies and edge-caches quotes for ~30s.
  // Canonical dynamic origin: the public Vercel PRODUCTION domain in the
  // wesley-hu-s-projects account. (Branch aliases like *-git-main-* sit behind
  // Vercel Authentication and would bounce anonymous readers to an SSO login;
  // the production domain is public.) Used as the cross-origin API base only
  // when viewed on GitHub Pages; served from Vercel, the call stays same-origin.
  var VERCEL_API = 'https://market-digest-liart.vercel.app';
  function quoteEndpoint(u) {
    var enc = encodeURIComponent(u);
    if (/\.github\.io$/i.test(location.hostname)) return VERCEL_API + '/api/quote?url=' + enc;
    return '/api/quote?url=' + enc;
  }
  // Public CORS proxies remain as automatic fallback if our endpoint fails.
  // Tried in order per request; a healthy one is remembered so we don't burn
  // attempts on a dead proxy every cycle.
  var PROXY_BUILDERS = [
    quoteEndpoint,
    function(u) { return 'https://corsproxy.io/?url=' + encodeURIComponent(u); },
    function(u) { return 'https://api.allorigins.win/raw?url=' + encodeURIComponent(u); },
    function(u) { return 'https://thingproxy.freeboard.io/fetch/' + u; },
    function(u) { return 'https://api.codetabs.com/v1/proxy/?quest=' + encodeURIComponent(u); }
  ];
  var preferredProxy = 0;
  var proxyFailures = 0;

  function etOffsetH() {
    var now = new Date(), y = now.getFullYear();
    var dstStart = new Date(y, 2, 8  - new Date(y, 2, 1).getDay());
    var dstEnd   = new Date(y, 10, 1 + (7 - new Date(y, 10, 1).getDay()) % 7);
    return (now >= dstStart && now < dstEnd) ? -4 : -5;
  }
  function nowET() {
    var utc = Date.now() + new Date().getTimezoneOffset() * 60000;
    return new Date(utc + etOffsetH() * 3600000);
  }
  function isMarketOpen() {
    var et = nowET(), d = et.getDay();
    if (d === 0 || d === 6) return false;
    var m = et.getHours() * 60 + et.getMinutes();
    return m >= 570 && m < 960;
  }
  // Human-readable session phase for the "as of" label so off-hours data is
  // clearly marked rather than looking stale or stuck.
  function sessionPhase() {
    var et = nowET(), d = et.getDay();
    if (d === 0 || d === 6) return 'weekend';
    var m = et.getHours() * 60 + et.getMinutes();
    if (m >= 570 && m < 960) return 'live';      // 9:30a–4:00p
    if (m >= 240 && m < 570) return 'pre-market'; // 4:00a–9:30a
    if (m >= 960 && m < 1200) return 'after-hours'; // 4:00p–8:00p
    return 'closed';
  }
  function asOfStr() {
    var phase = sessionPhase();
    if (phase === 'live') return 'live · ' + etStr();
    if (phase === 'pre-market') return 'pre-market · ' + etStr();
    if (phase === 'after-hours') return 'after-hours · ' + etStr();
    if (phase === 'weekend') return 'at Friday close';
    return 'at close · ' + etStr();
  }
  function etStr() {
    var et = nowET(), h = et.getHours(), m = et.getMinutes();
    h = h % 12 || 12;
    return h + ':' + String(m).padStart(2, '0') + ' ET';
  }

  var cache = {};

  function parseYahoo(json) {
    var r = json && json.chart && json.chart.result && json.chart.result[0];
    if (!r || !r.meta) throw new Error('no result');
    var meta = r.meta;
    var price = meta.regularMarketPrice;
    // After the close / pre-market, fall back to the last printed intraday close
    // so cells still reflect the most recent real trade instead of going blank.
    if (price == null && r.indicators && r.indicators.quote && r.indicators.quote[0]) {
      var closes = r.indicators.quote[0].close || [];
      for (var i = closes.length - 1; i >= 0; i--) {
        if (closes[i] != null) { price = closes[i]; break; }
      }
    }
    if (price == null) price = meta.previousClose || meta.chartPreviousClose;
    return { price: price, prevClose: meta.previousClose || meta.chartPreviousClose };
  }

  function fetchViaProxy(url, attempt) {
    attempt = attempt || 0;
    if (attempt >= PROXY_BUILDERS.length) return Promise.reject(new Error('all proxies failed'));
    var idx = (preferredProxy + attempt) % PROXY_BUILDERS.length;
    return fetch(PROXY_BUILDERS[idx](url), { cache: 'no-store' })
      .then(function(res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.text();
      })
      .then(function(text) {
        try { var j = JSON.parse(text); preferredProxy = idx; return j; }
        catch (_) { throw new Error('bad JSON'); }
      })
      .catch(function() { return fetchViaProxy(url, attempt + 1); });
  }

  function fetchTicker(sym) {
    var target = YF_BASE + encodeURIComponent(sym) + '?interval=1m&range=1d';
    return fetchViaProxy(target, 0)
      .then(function(json) {
        cache[sym] = parseYahoo(json);
        proxyFailures = 0;
      })
      .catch(function(e) {
        proxyFailures++;
        console.warn('[verdict]', sym, e.message);
        if (proxyFailures >= 3 && document.getElementById('vaSub')) {
          document.getElementById('vaSub').textContent = 'Quote feed unavailable — retrying (' + etStr() + ')';
        }
      });
  }

  function pctChg(sym)  { var d = cache[sym]; if (!d || !d.prevClose) return null; return (d.price - d.prevClose) / d.prevClose * 100; }
  function bpsChg(sym)  { var d = cache[sym]; if (!d || !d.prevClose) return null; return (d.price - d.prevClose) * 100; }
  function ptChg(sym)   { var d = cache[sym]; if (!d || !d.prevClose) return null; return d.price - d.prevClose; }
  function px(sym)      { return cache[sym] ? cache[sym].price : null; }
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

  function toVerdict(bull, bear, mixed) {
    var p = 5 - bull - bear - mixed;
    if (p >= 3)               return { cls: 'pending',   txt: 'Pending  -  awaiting data' };
    if (bull >= 4)            return { cls: 'confirmed', txt: '✓ Confirmed  -  4+ layers green' };
    if (bear >= 4)            return { cls: 'failed',    txt: '✗ Failed  -  4+ layers red' };
    if (bull===3 && bear===0) return { cls: 'tracking',  txt: 'Tracking  -  3 green, building' };
    if (bear===3 && bull===0) return { cls: 'tracking',  txt: 'Tracking bear  -  3 red layers' };
    if (bull >= 2 && bear<=1) return { cls: 'fragile',   txt: 'Fragile  -  leans bull' };
    if (bear >= 2 && bull<=1) return { cls: 'fragile',   txt: 'Fragile  -  leans bear' };
    return                           { cls: 'fragile',   txt: 'Contested  -  no dominant signal' };
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
    vEl.innerHTML = '<div class="v-label">Verdict</div>' + v.txt +
      ' <small style="opacity:.5;font-size:10px;font-style:normal">' + asOfStr() + '</small>';
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
    if      (delta >=  6) { h = '<span class="bull">Broad risk-on</span>  -  bull layers dominant';  s = B+'/15 green. '+R+' red. '+asOfStr(); }
    else if (delta <= -6) { h = '<span class="bear">Broad risk-off</span>  -  bear layers dominant'; s = R+'/15 red. '+B+' green. '+asOfStr(); }
    else if (delta >   0) { h = '<span class="bull">Mild risk-on</span>  -  bull layers lead';       s = B+' bull / '+R+' bear / '+M+' mixed. '+asOfStr(); }
    else if (delta <   0) { h = '<span class="bear">Mild risk-off</span>  -  bear layers lead';      s = R+' bear / '+B+' bull / '+M+' mixed. '+asOfStr(); }
    else                  { h = 'Contested regime  -  no clear signal';                               s = B+' bull / '+R+' bear / '+M+' mixed. '+asOfStr(); }
    hEl.innerHTML = h; sEl.textContent = s;
  }

  var TIER1 = ['^TNX','^TYX','BZ=F','NVDA','TLT','QQQ'];
  var TIER2 = ['^VIX','SPY','GLD','CL=F'];
  var TIER3 = ['XLE','XLK','XLU','NEE','SMH'];

  function runScoring() {
    // Always render the latest available data — live during the session, and the
    // most recent close/extended-hours print outside of it. Never stay "pending".
    updateAggregate([
      updateStack('bonds',    scoreBonds()),
      updateStack('iran-oil', scoreOil()),
      updateStack('ai-capex', scoreAI())
    ]);
  }

  function fetchAndScore(tickers) {
    Promise.all(tickers.map(fetchTicker)).then(runScoring);
  }

  // Poll fast during the live session; back off when the market is closed so we
  // don't pound the public proxies overnight/weekends (data won't change anyway).
  function refreshAll() {
    var open = isMarketOpen();
    fetchAndScore(open ? TIER1 : TIER1.concat(TIER2, TIER3));
  }
  Promise.all(TIER1.concat(TIER2, TIER3).map(fetchTicker)).then(function() {
    runScoring();
    setInterval(function(){ if (isMarketOpen()) fetchAndScore(TIER1); },  60 * 1000);
    setInterval(function(){ if (isMarketOpen()) fetchAndScore(TIER2); },   5 * 60 * 1000);
    setInterval(function(){ if (isMarketOpen()) fetchAndScore(TIER3); },  15 * 60 * 1000);
    // Closed-market heartbeat: one light refresh every 10 min keeps the last
    // close current (and recovers if the first load hit a dead proxy).
    setInterval(function(){ if (!isMarketOpen()) refreshAll(); }, 10 * 60 * 1000);
  });

})();
