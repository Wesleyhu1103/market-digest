// ============================================================
// INTERACTIVE MACRO CHARTS — FRED + live Brent; mkt-card UI
// ============================================================
(function initMacroCharts() {
  'use strict';
  if (typeof Chart === 'undefined') return;
  var macroSection = document.getElementById('macro');
  if (!macroSection || macroSection.dataset.macroChartsReady) return;

  var RANGES = [
    { key: '1d', label: '1D', fredDays: 5, range: '1d', interval: '5m' },
    { key: '1w', label: '1W', fredDays: 7, range: '5d', interval: '30m' },
    { key: '1m', label: '1M', fredDays: 31, range: '1mo', interval: '1d' },
    { key: '1y', label: '1Y', fredDays: 366, range: '1y', interval: '1d' }
  ];
  var MKT_SANS = '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  var fredMacro = null;

  function tc() {
    var s = getComputedStyle(document.documentElement);
    return {
      ink: s.getPropertyValue('--ink').trim() || '#1f1d1a',
      muted: s.getPropertyValue('--muted').trim() || '#6b665d',
      rule: s.getPropertyValue('--rule').trim() || '#d8cdb8',
      bull: s.getPropertyValue('--bull').trim() || '#166534',
      bear: s.getPropertyValue('--bear').trim() || '#991b1b',
      accent: s.getPropertyValue('--accent').trim() || '#0f4f4a',
      accent2: s.getPropertyValue('--accent-2').trim() || '#c2410c',
      anchor: s.getPropertyValue('--anchor').trim() || '#1e3a5f',
      bg: s.getPropertyValue('--bg').trim() || '#f4ede0'
    };
  }
  function rangeMeta(key) {
    for (var i = 0; i < RANGES.length; i++) if (RANGES[i].key === key) return RANGES[i];
    return RANGES[0];
  }
  function sliceFred(rows, rangeKey) {
    if (!rows || !rows.length) return [];
    var meta = rangeMeta(rangeKey);
    if (rangeKey === '1y') {
      var lastY = new Date(rows[rows.length - 1].date + 'T12:00:00');
      var cutY = new Date(lastY);
      cutY.setDate(cutY.getDate() - meta.fredDays);
      return rows.filter(function(row) {
        return new Date(row.date + 'T12:00:00') >= cutY;
      });
    }
    var last = new Date(rows[rows.length - 1].date + 'T12:00:00');
    var cutoff = new Date(last);
    cutoff.setDate(cutoff.getDate() - meta.fredDays);
    return rows.filter(function(row) {
      return new Date(row.date + 'T12:00:00') >= cutoff;
    });
  }
  function dateLabels(rows, rangeKey) {
    if (rangeKey === '1y') {
      return rows.map(function(row, i) {
        var prev = i > 0 ? rows[i - 1].date.slice(0, 7) : null;
        return row.date.slice(0, 7) !== prev
          ? new Date(row.date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short' }) : '';
      });
    }
    var step = Math.max(1, Math.round(rows.length / 7));
    return rows.map(function(row, i) {
      if (i === 0 || i === rows.length - 1 || i % step === 0) {
        return new Date(row.date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }
      return '';
    });
  }
  function fredByDate(series) {
    var map = {};
    (series || []).forEach(function(pt) { map[pt.date] = pt; });
    return map;
  }
  function mapFilled(rows, series, transform) {
    var byDate = fredByDate(series);
    var last = null;
    return rows.map(function(r) {
      var pt = byDate[r.date];
      if (pt) last = transform ? transform(pt) : pt.value;
      return last;
    });
  }
  function fredRowsToPoints(rows) {
    return (rows || []).map(function(r) {
      return { t: new Date(r.date + 'T12:00:00').getTime(), d: r.date, v: r.value };
    });
  }
  function mergeFredOntoLive(master, fredRows, transform) {
    var byDate = fredByDate(fredRows);
    var last = null;
    return master.map(function(pt) {
      var d = pt.d || new Date(pt.t).toISOString().slice(0, 10);
      if (byDate[d]) last = transform ? transform(byDate[d]) : byDate[d].value;
      return last;
    });
  }
  function alignLiveSeries(master, slave) {
    if (!slave || !slave.length) return master.map(function() { return null; });
    var pts = slave.slice().sort(function(a, b) { return a.t - b.t; });
    return master.map(function(m) {
      var t = m.t;
      if (t <= pts[0].t) return pts[0].v;
      if (t >= pts[pts.length - 1].t) return pts[pts.length - 1].v;
      var lo = 0, hi = pts.length - 1;
      while (lo < hi - 1) {
        var mid = (lo + hi) >> 1;
        if (pts[mid].t <= t) lo = mid; else hi = mid;
      }
      var a = pts[lo], b = pts[hi];
      if (a.t === b.t) return a.v;
      var f = (t - a.t) / (b.t - a.t);
      return a.v + f * (b.v - a.v);
    });
  }
  function macroTooltipBase(rangeKey, pointAt) {
    return {
      displayColors: true,
      titleFont: { family: MKT_SANS, size: 12, weight: '600' },
      bodyFont: { family: MKT_SANS, size: 12, weight: '500' },
      padding: 10,
      cornerRadius: 4,
      callbacks: {
        title: function(items) {
          if (!items.length) return '';
          var pt = pointAt(items[0].dataIndex);
          return pt ? mdMacroTooltipTitle(rangeKey, pt) : '';
        }
      }
    };
  }
  function setSource(api, base, live, asOfDate) {
    if (!api.qSource) return;
    var suffix = live && window.MarketFeed && window.MarketFeed.asOfStr
      ? ' · ' + window.MarketFeed.asOfStr() : '';
    if (asOfDate) suffix += ' · through ' + asOfDate;
    api.qSource.textContent = 'Source: ' + base + suffix;
  }
  function setDailySource(api, base, asOfDate) {
    if (!api.qSource) return;
    api.qSource.textContent = 'Source: ' + base + ' · daily close · through ' + asOfDate;
  }
  function macroLegend(t, show) {
    return show
      ? { position: 'top', labels: { font: { size: 11 }, boxWidth: 12, boxHeight: 8, color: t.ink, padding: 12 } }
      : { display: false };
  }
  function macroLineOpts(t) {
    return { animation: false, interaction: { mode: 'index', intersect: false },
      plugins: { datalabels: { display: false } } };
  }
  function macroFeed(call, fallback) {
    fallback = fallback != null ? fallback : [];
    try {
      return call().catch(function() { return fallback; });
    } catch (_) {
      return Promise.resolve(fallback);
    }
  }
  function setHeadline(api, price, prev, fmtPrice, fmtChg) {
    var up = (price - prev) >= 0;
    api.qPrice.textContent = fmtPrice(price);
    api.qChange.className = 'mkt-change ' + (up ? 'up' : 'down');
    var chg = price - prev;
    var pct = prev ? (chg / prev) * 100 : 0;
    api.qChange.textContent = fmtChg(chg, pct, up);
  }
  function yScaleFromValues(values, fmt, t) {
    var nums = values.filter(function(v) { return v != null && isFinite(v); });
    if (!nums.length) nums = [0, 1];
    var axis = mdAxisFromValues(nums, 5, 0.04);
    var dp = mdTickDecimals(axis.step);
    return Object.assign({
      position: 'right',
      min: axis.min,
      max: axis.max,
      border: { display: false },
      grid: { color: t.rule, drawBorder: false, tickLength: 0 },
      ticks: {
        stepSize: axis.step,
        maxTicksLimit: 6,
        font: { size: 11, family: MKT_SANS, weight: '500' },
        color: t.ink,
        padding: 10,
        callback: function(v) { return fmt(v, dp); }
      }
    });
  }
  function renderChart(api, labels, datasets, options, metaPoints) {
    if (api.chart) {
      api.chart.data.labels = labels;
      api.chart.data.datasets = datasets;
      if (options) {
        api.chart.options.plugins = options.plugins;
        api.chart.options.scales = Object.assign({}, options.scales || {});
        if (!options.scales || !options.scales.y2) delete api.chart.options.scales.y2;
        api.chart.options.interaction = options.interaction;
        api.chart.options.animation = options.animation;
      }
      if (metaPoints) api.chart.config._macroPoints = metaPoints;
      api.chart.update('none');
      return;
    }
    api.chart = new Chart(api.canvas, {
      type: 'line',
      data: { labels: labels, datasets: datasets },
      options: options
    });
    api.chart.config._preserveOnReinit = true;
    if (metaPoints) api.chart.config._macroPoints = metaPoints;
    window.allCharts = window.allCharts || [];
    window.allCharts.push(api.chart);
    requestAnimationFrame(function() { if (api.chart) api.chart.resize(); });
  }
  function buildCard(title, source, canvasId, height, opts) {
    opts = opts || {};
    var cardRanges = opts.ranges || RANGES;
    var defaultRange = opts.defaultRange || (cardRanges[0] && cardRanges[0].key) || '1d';
    var canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    var wrap = canvas.closest('.chart-card');
    if (!wrap) return null;
    var card = document.createElement('div');
    card.className = 'mkt-card macro-mkt-card';
    card.innerHTML =
      '<div class="mkt-head"><div>'
      + '<div class="mkt-title-row"><h3 class="mkt-title"></h3></div>'
      + '<div class="mkt-price-row"><span class="mkt-price">—</span><span class="mkt-change"></span></div>'
      + '</div></div>'
      + '<div class="mkt-body">'
      + '<div class="mkt-chart-wrap" style="height:' + height + 'px"><canvas id="' + canvasId + '"></canvas></div>'
      + '<div class="mkt-foot"><div class="mkt-ranges"></div><span class="mkt-source"></span></div>'
      + '</div>';
    card.querySelector('.mkt-title').textContent = title;
    card.querySelector('.mkt-source').textContent = 'Source: ' + source;
    wrap.replaceWith(card);
    var api = {
      canvas: card.querySelector('canvas'),
      qPrice: card.querySelector('.mkt-price'),
      qChange: card.querySelector('.mkt-change'),
      qRanges: card.querySelector('.mkt-ranges'),
      qSource: card.querySelector('.mkt-source'),
      range: defaultRange,
      chart: null,
      reload: null,
      ranges: cardRanges
    };
    cardRanges.forEach(function(r) {
      var b = document.createElement('button');
      b.textContent = r.label;
      b.className = r.key === defaultRange ? 'active' : '';
      b.addEventListener('click', function() {
        if (api.range === r.key) return;
        api.range = r.key;
        var btns = api.qRanges.querySelectorAll('button');
        for (var j = 0; j < btns.length; j++) btns[j].className = cardRanges[j].key === api.range ? 'active' : '';
        if (api.reload) api.reload();
      });
      api.qRanges.appendChild(b);
    });
    return api;
  }

  function initTreasury(api) {
    if (!api) return;
    api.reload = function() {
      var fred = fredMacro && fredMacro.fred;
      var meta = rangeMeta(api.range);
      var t = tc();

      function drawFromLive(tnxSeries, tyxSeries, quote) {
        if (!tnxSeries.length) return;
        var labels = mdTimeAxisLabels(tnxSeries, api.range);
        var d10 = tnxSeries.map(function(p) { return p.v; });
        var d30 = alignLiveSeries(tnxSeries, tyxSeries || []);
        var d2 = fred && fred.DGS2 ? mergeFredOntoLive(tnxSeries, fred.DGS2, function(pt) { return pt.value; }) : d10.map(function() { return null; });
        var vals = d10.concat(d30).concat(d2).filter(function(v) { return v != null && isFinite(v); });
        var last = quote && quote.price != null ? quote.price : d10[d10.length - 1];
        var prev = quote && quote.prevClose != null ? quote.prevClose : (d10.length > 1 ? d10[d10.length - 2] : last);
        setHeadline(api, last, prev, function(v) { return Number(v).toFixed(2) + '% (10Y)'; }, function(chg, pct, up) {
          return (up ? '+' : '') + chg.toFixed(2) + ' (' + (up ? '+' : '') + pct.toFixed(2) + '%)';
        });
        setSource(api, 'Cboe / FRED', true);
        var tip = macroTooltipBase(api.range, function(i) { return tnxSeries[i]; });
        tip.callbacks.label = function(ctx) {
          return ctx.dataset.label + ': ' + Number(ctx.parsed.y).toFixed(2) + '%';
        };
        renderChart(api, labels, [
          { label: '2Y', data: d2, borderColor: t.accent2, backgroundColor: t.accent2, tension: 0.15, pointRadius: 0, borderWidth: 2 },
          { label: '10Y', data: d10, borderColor: t.accent, backgroundColor: t.accent, tension: 0.15, pointRadius: 0, borderWidth: 2 },
          { label: '30Y', data: d30, borderColor: t.anchor, backgroundColor: t.anchor, tension: 0.15, pointRadius: 0, borderWidth: 2.5 }
        ], {
          animation: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { position: 'top', labels: { font: { size: 12 }, boxWidth: 14, boxHeight: 8, color: t.ink } },
            datalabels: { display: false },
            tooltip: tip
          },
          scales: {
            x: { grid: { display: false }, ticks: mdCategoryTickOpts(t, 10) },
            y: yScaleFromValues(vals, function(v) { return Number(v).toFixed(2) + '%'; }, t)
          }
        }, tnxSeries);
      }

      function drawFromFred() {
        if (!fred || !fred.DGS10) return;
        var rows = sliceFred(fred.DGS10, api.range);
        if (!rows.length) return;
        var points = fredRowsToPoints(rows);
        var labels = dateLabels(rows, api.range);
        var vals = [];
        var d2 = mapFilled(rows, fred.DGS2, function(pt) { return pt.value; });
        var d10 = rows.map(function(r) { vals.push(r.value); return r.value; });
        var d30 = mapFilled(rows, fred.DGS30, function(pt) { return pt.value; });
        d2.forEach(function(v) { if (v != null) vals.push(v); });
        d30.forEach(function(v) { if (v != null) vals.push(v); });
        var last = d10[d10.length - 1];
        var prev = d10.length > 1 ? d10[d10.length - 2] : last;
        setHeadline(api, last, prev, function(v) { return v.toFixed(2) + '% (10Y)'; }, function(chg, pct, up) {
          return (up ? '+' : '') + chg.toFixed(2) + ' (' + (up ? '+' : '') + pct.toFixed(2) + '%)';
        });
        setSource(api, 'FRED / U.S. Treasury', false);
        var tip = macroTooltipBase(api.range, function(i) { return points[i]; });
        tip.callbacks.label = function(ctx) {
          return ctx.dataset.label + ': ' + Number(ctx.parsed.y).toFixed(2) + '%';
        };
        renderChart(api, labels, [
          { label: '2Y', data: d2, borderColor: t.accent2, backgroundColor: t.accent2, tension: 0.15, pointRadius: 0, borderWidth: 2 },
          { label: '10Y', data: d10, borderColor: t.accent, backgroundColor: t.accent, tension: 0.15, pointRadius: 0, borderWidth: 2 },
          { label: '30Y', data: d30, borderColor: t.anchor, backgroundColor: t.anchor, tension: 0.15, pointRadius: 0, borderWidth: 2.5 }
        ], {
          animation: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { position: 'top', labels: { font: { size: 12 }, boxWidth: 14, boxHeight: 8, color: t.ink } },
            datalabels: { display: false },
            tooltip: tip
          },
          scales: {
            x: { grid: { display: false }, ticks: mdCategoryTickOpts(t, 10) },
            y: yScaleFromValues(vals, function(v) { return Number(v).toFixed(2) + '%'; }, t)
          }
        }, points);
      }

      if (window.MarketFeed) {
        Promise.all([
          macroFeed(function() { return window.MarketFeed.series('^TNX', meta.range, meta.interval); }),
          macroFeed(function() { return window.MarketFeed.series('^TYX', meta.range, meta.interval); }),
          macroFeed(function() { return window.MarketFeed.quote('^TNX'); }, {})
        ]).then(function(res) {
          if (!res[0] || !res[0].length) { drawFromFred(); return; }
          drawFromLive(res[0], res[1] || [], res[2] || {});
        });
      } else {
        drawFromFred();
      }
    };
    window._liveChartReloaders.push(api.reload);
    api.reload();
  }

  function initBrent(api) {
    if (!api) return;
    api.reload = function() {
      var meta = rangeMeta(api.range);
      var t = tc();
      function drawFromSeries(series) {
        if (!series.length) return;
        var labels = mdTimeAxisLabels(series, api.range);
        var values = series.map(function(p) { return p.v; });
        var last = values[values.length - 1];
        var prev = values.length > 1 ? values[0] : last;
        setHeadline(api, last, prev, function(v) { return '$' + Number(v).toFixed(2); }, function(chg, pct, up) {
          return (up ? '+' : '') + chg.toFixed(2) + ' (' + (up ? '+' : '') + pct.toFixed(2) + '%)';
        });
        setSource(api, 'ICE / Yahoo Finance', true);
        var up = (last - prev) >= 0;
        var color = up ? t.bull : t.bear;
        var tip = macroTooltipBase(api.range, function(i) { return series[i]; });
        tip.callbacks.label = function(ctx) { return '$' + Number(ctx.parsed.y).toFixed(2); };
        renderChart(api, labels, [{
          label: 'Brent', data: values, borderColor: color, backgroundColor: color + '24',
          fill: true, tension: 0.18, pointRadius: 0, borderWidth: 1.75,
          pointHoverRadius: 4, pointHoverBackgroundColor: color
        }], {
          animation: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: false },
            datalabels: { display: false },
            tooltip: tip
          },
          scales: {
            x: { grid: { display: false }, ticks: mdCategoryTickOpts(t, 10) },
            y: yScaleFromValues(values, function(v) { return '$' + Number(v).toFixed(0); }, t)
          }
        }, series);
      }
      if (window.MarketFeed) {
        window.MarketFeed.series('BZ=F', meta.range, meta.interval).then(drawFromSeries).catch(function() {
          if (!fredMacro || !fredMacro.brent) return;
          var rows = sliceFred(fredMacro.brent, api.range);
          drawFromSeries(rows.map(function(r) { return { t: new Date(r.date + 'T12:00:00').getTime(), v: r.value }; }));
        });
      } else if (fredMacro && fredMacro.brent) {
        var rows = sliceFred(fredMacro.brent, api.range);
        drawFromSeries(rows.map(function(r) { return { t: new Date(r.date + 'T12:00:00').getTime(), v: r.value }; }));
      }
    };
    window._liveChartReloaders.push(api.reload);
    api.reload();
  }

  function initCredit(api) {
    if (!api) return;
    api.reload = function() {
      var credit = fredMacro && fredMacro.credit;
      if (!credit) return;
      var rows = sliceFred(credit.HY_OAS, api.range);
      if (!rows.length) return;
      var points = fredRowsToPoints(rows);
      var labels = dateLabels(rows, api.range);
      var hy = rows.map(function(r) { return r.value * 100; });
      var ig = mapFilled(rows, credit.IG_OAS, function(pt) { return pt.value * 100; });
      var vals = hy.concat(ig).filter(function(v) { return v != null; });
      var last = hy[hy.length - 1];
      var prev = hy.length > 1 ? hy[hy.length - 2] : last;
      setHeadline(api, last, prev, function(v) { return Math.round(v) + ' bps (HY)'; }, function(chg, pct, up) {
        return (up ? '+' : '') + Math.round(chg) + ' bps';
      });
      setDailySource(api, 'FRED / ICE BofA OAS', rows[rows.length - 1].date);
      var t = tc();
      var tip = macroTooltipBase(api.range, function(i) { return points[i]; });
      tip.callbacks.label = function(ctx) { return ctx.dataset.label + ': ' + Math.round(ctx.parsed.y) + ' bps'; };
      var lineOpts = macroLineOpts(t);
      renderChart(api, labels, [
        { label: 'HY OAS', data: hy, borderColor: t.bear, tension: 0.15, pointRadius: 0, borderWidth: 2 },
        { label: 'IG OAS', data: ig, borderColor: t.accent, tension: 0.15, pointRadius: 0, borderWidth: 2 }
      ], Object.assign({}, lineOpts, {
        plugins: Object.assign({}, lineOpts.plugins, {
          legend: macroLegend(t, true),
          tooltip: tip
        }),
        scales: {
          x: { grid: { display: false }, ticks: mdCategoryTickOpts(t, 10) },
          y: yScaleFromValues(vals, function(v) { return Math.round(v) + ' bps'; }, t)
        }
      }), points);
    };
    window._liveChartReloaders.push(api.reload);
    api.reload();
  }

  function initStress(api) {
    if (!api) return;
    api.reload = function() {
      var credit = fredMacro && fredMacro.credit;
      var meta = rangeMeta(api.range);
      var t = tc();

      function renderStress(labels, vix, slope, metaPoints, opts) {
        opts = opts || {};
        var includeSpread = !!opts.includeSpread && slope && slope.some(function(v) { return v != null && isFinite(v); });
        var datasets = [{
          label: 'VIX', data: vix, borderColor: t.bear, tension: 0.15, pointRadius: 0,
          borderWidth: 2, yAxisID: 'y', fill: !includeSpread, backgroundColor: includeSpread ? undefined : t.bear + '18'
        }];
        if (includeSpread) {
          datasets.push({
            label: opts.spreadLabel || '2s10s', data: slope, borderColor: t.accent, tension: 0,
            stepped: opts.spreadStepped ? 'before' : false, pointRadius: 0, borderWidth: 2, yAxisID: 'y2'
          });
        }
        var tip = macroTooltipBase(api.range, function(i) { return metaPoints[i]; });
        tip.callbacks.label = function(ctx) {
          if (ctx.dataset.label === 'VIX') return 'VIX: ' + Number(ctx.parsed.y).toFixed(2);
          return ctx.dataset.label + ': ' + Math.round(ctx.parsed.y) + ' bps';
        };
        var scales = {
          x: { grid: { display: false }, ticks: mdCategoryTickOpts(t, 10) },
          y: Object.assign({}, yScaleFromValues(vix, function(v) { return Number(v).toFixed(1); }, t), { position: 'right', grid: { color: t.rule } })
        };
        if (includeSpread) {
          scales.y.position = 'left';
          scales.y2 = Object.assign({}, yScaleFromValues(slope, function(v) { return Math.round(v) + ' bps'; }, t), { position: 'right', grid: { display: false } });
        }
        var lineOpts = macroLineOpts(t);
        renderChart(api, labels, datasets, Object.assign({}, lineOpts, {
          plugins: Object.assign({}, lineOpts.plugins, {
            legend: macroLegend(t, includeSpread),
            tooltip: tip
          }),
          scales: scales
        }), metaPoints);
      }

      function dailySpreadOnTimeline(series) {
        if (!credit || !credit.TENMINUSTWO || !series || !series.length) return null;
        return mergeFredOntoLive(series, credit.TENMINUSTWO, function(pt) { return pt.value * 100; });
      }
      function showLiveSpread() {
        return api.range === '1w' || api.range === '1m' || api.range === '1y';
      }

      function drawLive(vixSeries, quote) {
        if (!vixSeries.length) return;
        var labels = mdTimeAxisLabels(vixSeries, api.range);
        var vix = vixSeries.map(function(p) { return p.v; });
        var includeSpread = showLiveSpread();
        var slope = includeSpread ? dailySpreadOnTimeline(vixSeries) : null;
        var spreadDate = credit && credit.TENMINUSTWO && credit.TENMINUSTWO.length
          ? credit.TENMINUSTWO[credit.TENMINUSTWO.length - 1].date : null;
        var last = quote && quote.price != null ? quote.price : vix[vix.length - 1];
        var prev = quote && quote.prevClose != null ? quote.prevClose : (vix.length > 1 ? vix[vix.length - 2] : last);
        setHeadline(api, last, prev, function(v) { return Number(v).toFixed(2) + ' (VIX)'; }, function(chg, pct, up) {
          return (up ? '+' : '') + chg.toFixed(2) + ' (' + (up ? '+' : '') + pct.toFixed(2) + '%)';
        });
        if (api.qSource) {
          var suffix = window.MarketFeed && window.MarketFeed.asOfStr
            ? ' · ' + window.MarketFeed.asOfStr() : '';
          if (includeSpread && spreadDate) suffix += ' · 2s10s daily through ' + spreadDate;
          api.qSource.textContent = 'Source: Cboe / FRED' + suffix;
        }
        renderStress(labels, vix, slope, vixSeries, {
          includeSpread: includeSpread,
          spreadLabel: '2s10s',
          spreadStepped: includeSpread
        });
      }

      function drawFred() {
        if (!credit || !credit.VIX) return;
        var rows = sliceFred(credit.VIX, api.range);
        if (!rows.length) return;
        var points = fredRowsToPoints(rows);
        var labels = dateLabels(rows, api.range);
        var vix = rows.map(function(r) { return r.value; });
        var includeSpread = api.range === '1w' || api.range === '1m' || api.range === '1y';
        var slope = includeSpread
          ? mapFilled(rows, credit.TENMINUSTWO, function(pt) { return pt.value * 100; })
          : null;
        var last = vix[vix.length - 1];
        var prev = vix.length > 1 ? vix[vix.length - 2] : last;
        setHeadline(api, last, prev, function(v) { return Number(v).toFixed(2) + ' (VIX)'; }, function(chg, pct, up) {
          return (up ? '+' : '') + chg.toFixed(2) + ' (' + (up ? '+' : '') + pct.toFixed(2) + '%)';
        });
        setDailySource(api, 'FRED / CBOE', rows[rows.length - 1].date);
        renderStress(labels, vix, slope, points, {
          includeSpread: includeSpread,
          spreadLabel: '2s10s',
          spreadStepped: includeSpread
        });
      }

      if (window.MarketFeed) {
        Promise.all([
          macroFeed(function() { return window.MarketFeed.series('^VIX', meta.range, meta.interval); }),
          macroFeed(function() { return window.MarketFeed.quote('^VIX'); }, {})
        ]).then(function(res) {
          if (!res[0] || !res[0].length) { drawFred(); return; }
          drawLive(res[0], res[1] || {});
        });
      } else {
        drawFred();
      }
    };
    window._liveChartReloaders.push(api.reload);
    api.reload();
  }

  // Upgrade DOM to mkt-card layout immediately (before data load)
  var FRED_DAILY_RANGES = RANGES.filter(function(r) { return r.key !== '1d'; });
  var treasuryApi = buildCard('US Treasury Yields', 'Cboe / FRED', 'treasuryYields', 280);
  var brentApi = buildCard('Brent Crude', 'ICE / Yahoo Finance', 'brentChart', 280);
  var creditApi = buildCard('Credit Spreads', 'FRED / ICE BofA OAS', 'creditChart', 240, {
    ranges: FRED_DAILY_RANGES,
    defaultRange: '1w'
  });
  var stressApi = buildCard('Market Stress', 'Cboe / FRED', 'stressChart', 240);
  var macroApis = [treasuryApi, brentApi, creditApi, stressApi];
  var macroPollTimer = null;

  function macroFredUrl() {
    return typeof mdMacroFredUrl === 'function' ? mdMacroFredUrl() : '/api/fred-data';
  }

  function staticFredUrl() {
    return typeof mdSitePath === 'function' ? mdSitePath('fred-data.json') : 'fred-data.json';
  }

  function loadFred(url) {
    return fetch(url, { cache: 'no-store' })
      .then(function(r) { return r.ok ? r.json() : null; })
      .catch(function() { return null; });
  }

  function refreshFredMacro() {
    // Primary source is the Vercel /api/fred-data refresh; fall back to the
    // published static snapshot so credit/stress still render when the API is
    // unreachable (local preview, GitHub Pages, or a Vercel outage).
    var primary = macroFredUrl();
    var fallback = staticFredUrl();
    return loadFred(primary).then(function(data) {
      if (data) { fredMacro = data; return data; }
      if (primary === fallback) return null;
      return loadFred(fallback).then(function(fb) {
        if (fb) fredMacro = fb;
        return fb;
      });
    });
  }

  function startMacroPoll() {
    if (macroPollTimer) clearInterval(macroPollTimer);
    var pollMs = 60000;
    macroPollTimer = setInterval(function() {
      if (document.hidden) return;
      refreshFredMacro().finally(function() {
        macroApis.forEach(function(a) { if (a && a.reload) try { a.reload(); } catch (_) {} });
      });
    }, pollMs);
  }

  function bootMacroCharts() {
    initTreasury(treasuryApi);
    initBrent(brentApi);
    initCredit(creditApi);
    initStress(stressApi);
    macroSection.dataset.macroChartsReady = '1';
    startMacroPoll();
  }

  function boot() {
    refreshFredMacro()
      .then(function() { bootMacroCharts(); })
      .catch(function(e) {
        console.warn('[macro charts]', e);
        bootMacroCharts();
      });
  }

  if (document.readyState === 'complete') {
    requestAnimationFrame(function() { requestAnimationFrame(boot); });
  } else {
    window.addEventListener('load', function() {
      requestAnimationFrame(function() { requestAnimationFrame(boot); });
    });
  }
})();
