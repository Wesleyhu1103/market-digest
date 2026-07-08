// ============================================================
// MarketFeed — shared live quote/series helper (Yahoo Finance)
// Reuses the same public CORS-proxy chain as the verdict updater.
// Exposed on window so the chart layer can pull live data.
// ============================================================
(function () {
  'use strict';
  var BASE = 'https://query1.finance.yahoo.com/v8/finance/chart/';
  var PROXIES = [
    // Our own cached Yahoo proxy first (reliable); same-origin on Vercel,
    // absolute public production domain when viewed on GitHub Pages. The
    // public proxies below remain as automatic fallback.
    function (u) {
      var base = /\.github\.io$/i.test(location.hostname) ? MD_VERCEL_ORIGIN : '';
      return base + '/api/quote?url=' + encodeURIComponent(u);
    },
    function (u) { return 'https://corsproxy.io/?url=' + encodeURIComponent(u); },
    function (u) { return 'https://api.allorigins.win/raw?url=' + encodeURIComponent(u); },
    function (u) { return 'https://thingproxy.freeboard.io/fetch/' + u; },
    function (u) { return 'https://api.codetabs.com/v1/proxy/?quest=' + encodeURIComponent(u); }
  ];
  var preferred = 0;

  function etOffsetH() {
    var now = new Date(), y = now.getFullYear();
    var dstStart = new Date(y, 2, 8 - new Date(y, 2, 1).getDay());
    var dstEnd = new Date(y, 10, 1 + (7 - new Date(y, 10, 1).getDay()) % 7);
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
  function sessionPhase() {
    var et = nowET(), d = et.getDay();
    if (d === 0 || d === 6) return 'weekend';
    var m = et.getHours() * 60 + et.getMinutes();
    if (m >= 570 && m < 960) return 'live';
    if (m >= 240 && m < 570) return 'pre-market';
    if (m >= 960 && m < 1200) return 'after-hours';
    return 'closed';
  }
  function etStr() {
    var et = nowET(), h = et.getHours(), m = et.getMinutes();
    h = h % 12 || 12;
    return h + ':' + String(m).padStart(2, '0') + ' ET';
  }
  function asOfStr() {
    var p = sessionPhase();
    if (p === 'live') return 'Live · ' + etStr();
    if (p === 'pre-market') return 'Pre-market · ' + etStr();
    if (p === 'after-hours') return 'After-hours · ' + etStr();
    if (p === 'weekend') return 'As of Friday close';
    return 'At close · ' + etStr();
  }

  function viaProxy(url, attempt) {
    attempt = attempt || 0;
    if (attempt >= PROXIES.length) return Promise.reject(new Error('all proxies failed'));
    var idx = (preferred + attempt) % PROXIES.length;
    return fetch(PROXIES[idx](url), { cache: 'no-store' })
      .then(function (res) { if (!res.ok) throw new Error('HTTP ' + res.status); return res.text(); })
      .then(function (text) { try { var j = JSON.parse(text); preferred = idx; return j; } catch (_) { throw new Error('bad JSON'); } })
      .catch(function () { return viaProxy(url, attempt + 1); });
  }

  function parseQuote(json) {
    var r = json && json.chart && json.chart.result && json.chart.result[0];
    if (!r || !r.meta) throw new Error('no result');
    var meta = r.meta, price = meta.regularMarketPrice;
    if (price == null && r.indicators && r.indicators.quote && r.indicators.quote[0]) {
      var closes = r.indicators.quote[0].close || [];
      for (var i = closes.length - 1; i >= 0; i--) { if (closes[i] != null) { price = closes[i]; break; } }
    }
    if (price == null) price = meta.previousClose || meta.chartPreviousClose;
    return { price: price, prevClose: meta.previousClose || meta.chartPreviousClose };
  }

  function quote(sym) {
    return viaProxy(BASE + encodeURIComponent(sym) + '?interval=1m&range=1d', 0).then(parseQuote);
  }
  function series(sym, range, interval) {
    range = range || '3mo'; interval = interval || '1d';
    return viaProxy(BASE + encodeURIComponent(sym) + '?interval=' + interval + '&range=' + range, 0).then(function (json) {
      var r = json && json.chart && json.chart.result && json.chart.result[0];
      if (!r || !r.timestamp) throw new Error('no series');
      var ts = r.timestamp;
      var cl = (r.indicators && r.indicators.quote && r.indicators.quote[0] && r.indicators.quote[0].close) || [];
      var out = [];
      for (var i = 0; i < ts.length; i++) {
        var v = cl[i]; if (v == null) continue;
        var d = new Date(ts[i] * 1000).toISOString().slice(0, 10);
        out.push({ d: d, t: ts[i] * 1000, v: v });
      }
      return out;
    });
  }

  window.MarketFeed = {
    isMarketOpen: isMarketOpen,
    sessionPhase: sessionPhase,
    asOfStr: asOfStr,
    etStr: etStr,
    quote: quote,
    series: series
  };
})();
