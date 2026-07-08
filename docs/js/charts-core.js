// Charts — initialized after layout so container heights are non-zero
function mdNiceStep(raw) {
  if (!isFinite(raw) || raw <= 0) return 1;
  var mag = Math.pow(10, Math.floor(Math.log10(raw)));
  var norm = raw / mag;
  var nice = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return nice * mag;
}
function mdNiceRange(min, max, tickCount) {
  tickCount = tickCount || 5;
  if (!isFinite(min) || !isFinite(max)) return { min: 0, max: 1, step: 1 };
  if (min === max) { min -= 1; max += 1; }
  var step = mdNiceStep((max - min) / tickCount);
  return {
    min: Math.floor(min / step) * step,
    max: Math.ceil(max / step) * step,
    step: step
  };
}
function mdFmtNum(v, dp) {
  dp = dp == null ? 2 : dp;
  var n = Number(v);
  if (!isFinite(n)) return '';
  var r = Math.round(n * Math.pow(10, dp)) / Math.pow(10, dp);
  var s = r.toFixed(dp);
  if (dp > 0) s = s.replace(/\.?0+$/, '');
  return s;
}
function mdBarLabelColor() {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? '#ffffff' : '#121212';
}
/** Sparse x-axis labels for live/FRED time series (one label per ~N points). */
function mdTimeAxisLabels(series, rangeKey) {
  var labels = [], i, d, key, prevKey = null, step;
  for (i = 0; i < series.length; i++) {
    d = new Date(series[i].t != null ? series[i].t : series[i].date + 'T12:00:00');
    if (rangeKey === '1d') {
      key = d.toISOString().slice(0, 10) + '-' + d.getHours();
      if (d.getMinutes() === 0 && (prevKey === null || key !== prevKey)) {
        labels.push(d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }));
        prevKey = key;
      } else labels.push('');
    } else if (rangeKey === '1w') {
      step = Math.max(1, Math.round(series.length / 6));
      labels.push((i === 0 || i === series.length - 1 || i % step === 0)
        ? d.toLocaleDateString('en-US', { weekday: 'short', month: 'numeric', day: 'numeric' }) : '');
    } else if (rangeKey === '1m') {
      step = Math.max(1, Math.round(series.length / 7));
      labels.push((i === 0 || i === series.length - 1 || i % step === 0)
        ? d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '');
    } else {
      key = d.getFullYear() + '-' + d.getMonth();
      if (key !== prevKey) {
        labels.push(d.toLocaleDateString('en-US', { month: 'short' }));
        prevKey = key;
      } else labels.push('');
    }
  }
  return labels;
}
/** CNBC-style tooltip date/time for macro and live charts. */
function mdMacroTooltipTitle(rangeKey, pt) {
  var d = new Date(pt.t != null ? pt.t : pt.date + 'T12:00:00');
  if (rangeKey === '1d' || rangeKey === '1w') {
    return d.toLocaleString('en-US', {
      weekday: 'short', month: '2-digit', day: '2-digit', year: 'numeric',
      hour: 'numeric', minute: '2-digit'
    });
  }
  return d.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' });
}
function mdCategoryTickOpts(t, fontSize, fontFamily) {
  return {
    font: { size: fontSize || 10, family: fontFamily || '"Inter", -apple-system, sans-serif' },
    maxRotation: 0,
    autoSkip: true,
    autoSkipPadding: 14,
    maxTicksLimit: 7,
    color: t.ink,
    padding: 8,
    callback: function(val, index) {
      var lbl = this.chart.data.labels[index];
      return lbl ? lbl : undefined;
    }
  };
}
function mdAxisFromValues(values, tickCount, padRatio) {
  padRatio = padRatio == null ? 0.05 : padRatio;
  var nums = values.filter(function(v) { return v != null && isFinite(v); });
  if (!nums.length) return { min: 0, max: 1, step: 1 };
  var lo = Math.min.apply(null, nums);
  var hi = Math.max.apply(null, nums);
  var span = Math.max(hi - lo, 1e-9);
  return mdNiceRange(lo - span * padRatio, hi + span * padRatio, tickCount || 5);
}
function mdTickDecimals(step) {
  if (step >= 1) return 0;
  if (step >= 0.1) return 1;
  if (step >= 0.01) return 2;
  return 3;
}
function mdLinearAxis(axis, fmt, tickStyle) {
  var dp = mdTickDecimals(axis.step);
  return {
    min: axis.min,
    max: axis.max,
    ticks: Object.assign({
      stepSize: axis.step,
      callback: function(v) { return fmt(v, dp); }
    }, tickStyle || {})
  };
}

async function _initAllCharts() {
// Chart data for simple bar charts is stored in <script id="chartData"> inside <main> — automatically updates them — no JS surgery needed.
const chartFont = '"Inter", -apple-system, sans-serif';
Chart.defaults.font.family = chartFont;
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;
// Destroy static charts on re-init; preserve live mkt-card charts (equities + macro).
window.allCharts = (window.allCharts || []).filter(function(c) {
  if (c.config && c.config._preserveOnReinit) return true;
  try { c.destroy(); } catch (_) {}
  return false;
});

// Theme-aware color reader
function tc() {
  const s = getComputedStyle(document.documentElement);
  return {
    ink:     s.getPropertyValue('--ink').trim()     || '#1f1d1a',
    muted:   s.getPropertyValue('--muted').trim()   || '#6b665d',
    rule:    s.getPropertyValue('--rule').trim()     || '#d8cdb8',
    bull:    s.getPropertyValue('--bull').trim()     || '#166534',
    bear:    s.getPropertyValue('--bear').trim()     || '#991b1b',
    accent:  s.getPropertyValue('--accent').trim()  || '#0f4f4a',
    accent2: s.getPropertyValue('--accent-2').trim()|| '#c2410c',
    anchor:  s.getPropertyValue('--anchor').trim()  || '#1e3a5f',
    surface: s.getPropertyValue('--surface').trim() || '#fbf6ec'
  };
}
Chart.defaults.color = tc().ink;

// Register plugins
if (window.ChartDataLabels) Chart.register(ChartDataLabels);
Chart.defaults.plugins = Chart.defaults.plugins || {};
Chart.defaults.plugins.datalabels = { display: false };

const lastPointLabel = {
  id: 'lastPointLabel',
  afterDatasetsDraw(chart) {
    try {
      const opt = chart.options && chart.options.plugins && chart.options.plugins.lastPointLabel;
      if (!opt || !opt.show) return;
      const fmt = opt.format || (v => v.toFixed(2));
      const ctx = chart.ctx;
      if (!ctx) return;
      chart.data.datasets.forEach((ds, di) => {
        const meta = chart.getDatasetMeta(di);
        if (!meta || meta.hidden) return;
        const last = meta.data && meta.data[meta.data.length - 1];
        if (!last || typeof last.x !== 'number' || typeof last.y !== 'number') return;
        const val = ds.data[ds.data.length - 1];
        if (val == null) return;
        const label = fmt(val, ds);
        ctx.save();
        ctx.font = '700 11px ' + chartFont;
        ctx.textBaseline = 'middle';
        const w = ctx.measureText(label).width;
        ctx.fillStyle = tc().surface;
        ctx.globalAlpha = 0.92;
        ctx.fillRect(last.x + 4, last.y - 8, w + 8, 16);
        ctx.globalAlpha = 1;
        ctx.fillStyle = ds.borderColor || tc().ink;
        ctx.fillText(label, last.x + 8, last.y);
        ctx.restore();
      });
    } catch (e) { /* swallow */ }
  }
};
Chart.register(lastPointLabel);

// ── Read daily chart data from the JSON tag inside <main> ──────────────
// This is the key architectural fix: chart data lives in <main>, not in JS.
// Replacing <main> in the daily commit script updates charts automatically.
let cd = {};

let macro = null;
try {
  const mr = await fetch('fred-data.json', { cache: 'no-store' });
  if (mr.ok) macro = await mr.json();
} catch (e) { console.warn('fred-data.json unavailable', e); }
const fred = (macro && macro.fred) ? macro.fred : { DGS2: [], DGS10: [], DGS30: [] };
const brent = (macro && macro.brent) ? macro.brent : [];
const creditData = (macro && macro.credit) ? macro.credit : { HY_OAS: [], IG_OAS: [], VIX: [], TENMINUSTWO: [] };

document.querySelectorAll('script#chartData').forEach(el => {
  try { cd = Object.assign(cd, JSON.parse(el.textContent)); } catch(e) { console.warn('chartData parse error', e); }
});

// ── 1. Tech movers ────────────────────────���─────────────���───────────────
if (document.getElementById('techMovers') && cd.techMovers) {
  const d = cd.techMovers;
  const lo = Math.min(...d.values, 0);
  const hi = Math.max(...d.values, 0);
  const xr = mdNiceRange(lo, hi, 5);
  const xAxis = mdLinearAxis(xr, function(v, dp) { return mdFmtNum(v, dp) + '%'; }, { font: { size: 12 }, color: tc().ink });
  window.allCharts.push(new Chart(document.getElementById('techMovers'), {
    type: 'bar',
    data: {
      labels: d.labels,
      datasets: [{
        data: d.values,
        backgroundColor: d.values.map(v => v >= 0 ? tc().bull : tc().bear),
        borderRadius: 2,
        barThickness: 22
      }]
    },
    options: {
      indexAxis: 'y',
      layout: { padding: { right: 48, left: 48 } },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => (ctx.parsed.x > 0 ? '+' : '') + mdFmtNum(ctx.parsed.x, 1) + '%' } },
        datalabels: {
          display: true,
          anchor: ctx => ctx.dataset.data[ctx.dataIndex] >= 0 ? 'end' : 'start',
          align: ctx => ctx.dataset.data[ctx.dataIndex] >= 0 ? 'left' : 'right',
          offset: 6, clip: false,
          color: mdBarLabelColor(),
          font: { size: 12, weight: 700 },
          formatter: v => (v > 0 ? '+' : '') + mdFmtNum(v, 1) + '%'
        }
      },
      scales: {
        x: Object.assign({ grid: { color: tc().rule, drawBorder: false } }, xAxis),
        y: { grid: { display: false }, ticks: { font: { size: 13 }, color: tc().ink } }
      }
    }
  }));
}

// ── 2. Reddit sentiment ─────────────────────────────────────────────────
if (document.getElementById('redditSentiment') && cd.redditSentiment) {
  const d = cd.redditSentiment;
  const rr = mdAxisFromValues(d.values, 4, 0.12);
  window.allCharts.push(new Chart(document.getElementById('redditSentiment'), {
    type: 'bar',
    data: {
      labels: d.labels,
      datasets: [{
        data: d.values,
        backgroundColor: d.colors.map(c => c === 'bull' ? tc().bull : c === 'bear' ? tc().bear : tc().muted),
        borderRadius: 2,
        barThickness: 18
      }]
    },
    options: {
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ctx.parsed.x.toLocaleString() + ' upvotes' } },
        datalabels: {
          display: true, anchor: 'end', align: 'end', clamp: true,
          color: tc().ink, font: { size: 11, weight: 600 },
          formatter: v => v.toLocaleString()
        }
      },
      scales: {
        x: Object.assign({ grid: { color: tc().rule } }, mdLinearAxis(rr, function(v) { return Number(v).toLocaleString('en-US'); }, { font: { size: 11 }, color: tc().muted })),
        y: { grid: { display: false }, ticks: { font: { size: 11 }, color: tc().ink } }
      }
    }
  }));
}

// ── 3–4, 6–7. Macro FRED charts — interactive mkt-cards (see initMacroCharts below) ──

// ── 5. Deal sizes ───────────────────────────────────────────────────────
if (document.getElementById('dealSizes') && cd.dealSizes) {
  const d = cd.dealSizes;
  const dr = mdAxisFromValues(d.values, 4, 0.1);
  dr.min = 0;
  function dealTick(v, dp) {
    var n = Number(v);
    if (n === 0) return '$0';
    if (n < 1) return '$' + mdFmtNum(n, 2) + 'B';
    return '$' + mdFmtNum(n, dp != null ? dp : 1) + 'B';
  }
  const yAxis = mdLinearAxis(dr, dealTick, { font: { size: 12 }, color: tc().muted });
  window.allCharts.push(new Chart(document.getElementById('dealSizes'), {
    type: 'bar',
    data: {
      labels: d.labels,
      datasets: [{
        data: d.values,
        backgroundColor: [tc().accent, tc().bull, tc().muted, tc().accent2, tc().anchor].slice(0, d.labels.length),
        borderRadius: 2,
        barThickness: 48
      }]
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => dealTick(ctx.parsed.y) } },
        datalabels: {
          display: true, anchor: 'end', align: 'top', clip: false, offset: 4,
          color: tc().ink, font: { size: 14, weight: 700 },
          formatter: v => dealTick(v, 1)
        }
      },
      scales: {
        y: Object.assign({ beginAtZero: true, grid: { color: tc().rule } }, yAxis),
        x: { grid: { display: false }, ticks: { font: { size: 12 }, color: tc().ink } }
      }
    }
  }));
}

} // end _initAllCharts

if (document.readyState === 'complete') {
  requestAnimationFrame(_initAllCharts);
} else {
  window.addEventListener('load', function() { requestAnimationFrame(_initAllCharts); });
}
