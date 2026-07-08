// ============================================================
// INTERACTIVE ARTIFACT 1 — LIVE MARKET CHART
// Self-mounts into #equities. Reuses window.MarketFeed (Yahoo via
// CORS proxies) + Chart.js. Lives in the static template, so it
// survives daily <main> regeneration automatically.
// ============================================================
(function() {
  'use strict';
  if (!window.MarketFeed || typeof Chart === 'undefined') return;
  var section = document.getElementById('equities');
  if (!section || section.querySelector('.mkt-card')) return;

  var SYMBOLS = [
    { sym: '^GSPC', label: 'S&P 500', source: 'S&P Dow Jones Indices' },
    { sym: '^IXIC', label: 'Nasdaq', source: 'Nasdaq' },
    { sym: '^DJI',  label: 'Dow Jones', source: 'S&P Dow Jones Indices' },
    { sym: '^TNX',  label: '10-Yr Yield', source: 'Cboe / U.S. Treasury' }
  ];
  var RANGES = [
    { key: '1d', label: '1D', range: '1d',  interval: '5m' },
    { key: '1w', label: '1W', range: '5d',  interval: '30m' },
    { key: '1m', label: '1M', range: '1mo', interval: '1d' },
    { key: '1y', label: '1Y', range: '1y',  interval: '1d' }
  ];

  var state = { sym: '^GSPC', range: '1d' };
  var chart = null;
  var pollTimer = null;
  var reqToken = 0;

  function tc() {
    var s = getComputedStyle(document.documentElement);
    return {
      ink:   s.getPropertyValue('--ink').trim()   || '#1f1d1a',
      muted: s.getPropertyValue('--muted').trim() || '#6b665d',
      rule:  s.getPropertyValue('--rule').trim()  || '#d8cdb8',
      bull:  s.getPropertyValue('--bull').trim()  || '#166534',
      bear:  s.getPropertyValue('--bear').trim()  || '#991b1b',
      surface: s.getPropertyValue('--surface').trim() || '#fbf6ec',
      bg:    s.getPropertyValue('--bg').trim()    || '#f4ede0'
    };
  }
  function fmt(v) { return Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function rangeMeta() { for (var i = 0; i < RANGES.length; i++) if (RANGES[i].key === state.range) return RANGES[i]; return RANGES[0]; }
  function symMeta() { for (var i = 0; i < SYMBOLS.length; i++) if (SYMBOLS[i].sym === state.sym) return SYMBOLS[i]; return SYMBOLS[0]; }

  var MKT_SANS = '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  var mktAxisFont = { size: 11, family: MKT_SANS, weight: '500' };

  if (!window._mktDividersRegistered) {
    Chart.register({
      id: 'mktDayDividers',
      beforeDatasetsDraw: function (chart) {
        var bounds = chart.config._mktDividers;
        if (!bounds || !bounds.length) return;
        var xScale = chart.scales.x, yScale = chart.scales.y;
        if (!xScale || !yScale) return;
        var rule = getComputedStyle(document.documentElement).getPropertyValue('--rule').trim() || '#d8cdb8';
        var ctx = chart.ctx;
        ctx.save();
        ctx.strokeStyle = rule;
        ctx.lineWidth = 1;
        bounds.forEach(function (idx) {
          var px = xScale.getPixelForValue(idx);
          ctx.beginPath();
          ctx.moveTo(px, yScale.top);
          ctx.lineTo(px, yScale.bottom);
          ctx.stroke();
        });
        ctx.restore();
      }
    });
    window._mktDividersRegistered = true;
  }

  function fmtAxisY(v, dp) {
    if (state.sym === '^TNX') return mdFmtNum(v, dp != null ? dp : 2) + '%';
    var n = Number(v);
    if (Math.abs(n) >= 10000) return mdFmtNum(n / 1000, 1) + 'k';
    return mdFmtNum(n, dp != null ? dp : 0);
  }
  function fmtTooltip(v) {
    if (state.sym === '^TNX') return mdFmtNum(v, 3) + '%';
    return fmt(v);
  }
  function mktYScale(values, t) {
    var yAxis = mdLinearAxis(mdAxisFromValues(values, 5, 0.04), fmtAxisY, { font: mktAxisFont, color: t.muted, padding: 10 });
    return Object.assign({
      position: 'right',
      border: { display: false },
      grid: { color: t.rule, drawBorder: false, tickLength: 0 }
    }, yAxis);
  }

  // One x-axis label per time bucket; vertical dividers at day/week/month boundaries.
  function buildMktAxis(series) {
    var labels = mdTimeAxisLabels(series, state.range);
    var dividers = [], prevKey = null, i, d, key;
    for (i = 0; i < series.length; i++) {
      if (!labels[i]) continue;
      d = new Date(series[i].t);
      if (state.range === '1d') {
        key = d.toISOString().slice(0, 10) + '-' + d.getHours();
      } else if (state.range === '1w' || state.range === '1m') {
        key = String(i);
      } else {
        key = d.getFullYear() + '-' + d.getMonth();
      }
      if (prevKey !== null && key !== prevKey) dividers.push(i);
      prevKey = key;
    }
    return { labels: labels, dividers: dividers };
  }

  function mktChartOptions(t, values) {
    return {
      animation: false,
      interaction: { mode: 'index', intersect: false },
      layout: { padding: { top: 8, right: 4, left: 4 } },
      plugins: {
        legend: { display: false }, datalabels: { display: false },
        tooltip: {
          displayColors: false,
          titleFont: { family: MKT_SANS, size: 12, weight: '600' },
          bodyFont: { family: MKT_SANS, size: 12, weight: '500' },
          padding: 10, cornerRadius: 4,
          callbacks: {
            title: function (items) {
              if (!items.length) return '';
              var chart = items[0].chart;
              var idx = items[0].dataIndex;
              var lbl = chart.data.labels[idx];
              if (lbl) return lbl;
              var pt = chart.config._mktSeries && chart.config._mktSeries[idx];
              if (pt) {
                var dd = new Date(pt.t);
                if (state.range === '1d') return dd.toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' });
                return dd.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
              }
              return '';
            },
            label: function (ctx) { return fmtTooltip(ctx.parsed.y); }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: Object.assign({ font: mktAxisFont }, mdCategoryTickOpts(t, 11, MKT_SANS))
        },
        y: mktYScale(values, t)
      }
    };
  }

  // Build DOM
  var card = document.createElement('div');
  card.className = 'mkt-card';
  card.innerHTML =
    '<div class="mkt-head">'
    + '<div>'
    +   '<div class="mkt-title-row"><h3 class="mkt-title" data-el="title">Loading\u2026</h3><span class="mkt-dot" data-el="dot"></span></div>'
    +   '<div class="mkt-price-row"><span class="mkt-price" data-el="price">\u2014</span><span class="mkt-change" data-el="change"></span></div>'
    + '</div>'
    + '<div class="mkt-syms" data-el="syms"></div>'
    + '</div>'
    + '<div class="mkt-body">'
    +   '<div class="mkt-chart-wrap" data-el="chartWrap"><canvas data-el="canvas"></canvas></div>'
    +   '<div class="mkt-foot"><div class="mkt-ranges" data-el="ranges"></div><span class="mkt-source" data-el="source"></span></div>'
    + '</div>';

  function q(sel) { return card.querySelector('[data-el="' + sel + '"]'); }

  SYMBOLS.forEach(function(s) {
    var b = document.createElement('button');
    b.textContent = s.label;
    b.className = s.sym === state.sym ? 'active' : '';
    b.addEventListener('click', function() {
      if (state.sym === s.sym) return;
      state.sym = s.sym;
      syncToggles();
      load();
    });
    q('syms').appendChild(b);
  });
  RANGES.forEach(function(r) {
    var b = document.createElement('button');
    b.textContent = r.label;
    b.className = r.key === state.range ? 'active' : '';
    b.addEventListener('click', function() {
      if (state.range === r.key) return;
      state.range = r.key;
      syncToggles();
      load();
    });
    q('ranges').appendChild(b);
  });
  function syncToggles() {
    var sb = q('syms').children, rb = q('ranges').children, i;
    for (i = 0; i < sb.length; i++) sb[i].className = SYMBOLS[i].sym === state.sym ? 'active' : '';
    for (i = 0; i < rb.length; i++) rb[i].className = RANGES[i].key === state.range ? 'active' : '';
  }

  // Inject after story dropdowns, before anchor/deeper blocks
  var anchor = section.querySelector('.anchor');
  if (anchor) anchor.insertAdjacentElement('beforebegin', card);
  else {
    var lastDeal = section.querySelector('details.deal:last-of-type');
    if (lastDeal) lastDeal.insertAdjacentElement('afterend', card);
    else section.appendChild(card);
  }

  function render(series, quote) {
    var t = tc();
    var up = (quote.price - quote.prevClose) >= 0;
    var color = up ? t.bull : t.bear;
    var meta = symMeta();

    q('title').textContent = meta.label;
    q('price').textContent = fmt(quote.price);
    var chg = quote.price - quote.prevClose;
    var pct = quote.prevClose ? (chg / quote.prevClose) * 100 : 0;
    var chgEl = q('change');
    chgEl.className = 'mkt-change ' + (up ? 'up' : 'down');
    chgEl.textContent = (up ? '+' : '') + fmt(chg) + ' (' + (up ? '+' : '') + pct.toFixed(2) + '%)';
    var live = window.MarketFeed.sessionPhase && window.MarketFeed.sessionPhase() === 'live';
    q('dot').className = 'mkt-dot' + (live ? ' live' : '');
    q('source').textContent = 'Source: ' + meta.source;

    var axis = buildMktAxis(series);
    var labels = axis.labels;
    var values = series.map(function(p) { return p.v; });

    if (chart) {
      chart.data.labels = labels;
      chart.data.datasets[0].data = values;
      chart.data.datasets[0].borderColor = color;
      chart.data.datasets[0].backgroundColor = color + '24';
      chart.config._mktDividers = axis.dividers;
      chart.config._mktSeries = series;
      chart.options.scales.x.ticks.color = t.muted;
      Object.assign(chart.options.scales.y, mktYScale(values, t));
      chart.update('none');
      return;
    }
    chart = new Chart(q('canvas'), {
      type: 'line',
      data: { labels: labels, datasets: [{
        data: values, borderColor: color, backgroundColor: color + '24',
        fill: true, tension: 0.18, pointRadius: 0, borderWidth: 1.75,
        pointHoverRadius: 4, pointHoverBackgroundColor: color, pointHoverBorderColor: t.bg, pointHoverBorderWidth: 1.5
      }]},
      options: mktChartOptions(t, values)
    });
    chart.config._preserveOnReinit = true;
    chart.config._mktDividers = axis.dividers;
    chart.config._mktSeries = series;
    window.allCharts = window.allCharts || [];
    window.allCharts.push(chart);
    requestAnimationFrame(function() { if (chart) chart.resize(); });
    return;
  }

  function load() {
    var token = ++reqToken;
    var meta = rangeMeta();
    var wrap = q('chartWrap');
    q('source').textContent = 'Syncing\u2026';
    Promise.all([
      window.MarketFeed.series(state.sym, meta.range, meta.interval),
      window.MarketFeed.quote(state.sym)
    ]).then(function(res) {
      if (token !== reqToken) return;
      var series = res[0] || [], quote = res[1] || {};
      if (!series.length) throw new Error('no series');
      if (quote.price == null) { quote.price = series[series.length - 1].v; quote.prevClose = series[0].v; }
      wrap.innerHTML = '<canvas data-el="canvas"></canvas>';
      chart = null;
      render(series, quote);
    }).catch(function(e) {
      if (token !== reqToken) return;
      if (chart) { chart.destroy(); chart = null; }
      wrap.innerHTML = '<div class="mkt-error">Live market data unavailable.</div>';
      q('source').textContent = '';
      console.warn('[mkt-chart]', e && e.message);
    });

    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(function() {
      if (document.hidden) return;
      window.MarketFeed.quote(state.sym).then(function(quote) {
        if (!chart || quote.price == null) return;
        window.MarketFeed.series(state.sym, meta.range, meta.interval).then(function(series) {
          if (series && series.length) render(series, quote);
        });
      }).catch(function() {});
    }, state.range === '1d' ? 30000 : 60000);
  }

  function bootMktChart() {
    requestAnimationFrame(function() {
      requestAnimationFrame(load);
    });
  }
  window._liveChartReloaders = window._liveChartReloaders || [];
  window._liveChartReloaders.push(load);
  if (document.readyState === 'complete') bootMktChart();
  else window.addEventListener('load', bootMktChart);
})();
