// ============================================================
// INTERACTIVE ARTIFACT 2 — FRAMING COMPARE
// Self-mounts into #framing-mount. Reads an optional
// <script type="application/json" id="framingData"> from <main>
// (so the daily pipeline can drive it); otherwise uses a default.
// ============================================================
(function() {
  'use strict';
  var mount = document.getElementById('framing-mount');
  if (!mount || mount.querySelector('.frame-card')) return;

  var DEFAULT_DATA = {
    storyTitle: 'May jobs report comes in below expectations',
    framings: [
      { outlet: 'WSJ', headline: 'Hiring Slows, Clearing a Path for the Fed to Cut', angle: 'Frames the miss as healthy normalization that hands the Fed room.', lean: 28, pull: 'A cooler labor market is exactly what policymakers have been waiting for.' },
      { outlet: 'The Economist', headline: 'America\u2019s labour market is bending, not breaking', angle: 'Measured: cautions against reading one print as a turning point.', lean: 6, pull: 'One soft month is a data point, not yet a trend.' },
      { outlet: 'NYT', headline: 'Job Growth Cools, and Workers Feel the Squeeze', angle: 'Leads with the human cost and downside risk to households.', lean: -34, pull: 'For job seekers, the slowdown is already painful.' },
      { outlet: 'CNBC', headline: 'Markets Rally as Weak Jobs Data Fuels Rate-Cut Bets', angle: 'Market-reaction first; bad news for jobs is good news for stocks.', lean: 58, pull: 'Traders cheered the report, sending equities to session highs.' }
    ]
  };

  var data = DEFAULT_DATA;
  var tag = document.getElementById('framingData');
  if (tag) { try { var parsed = JSON.parse(tag.textContent); if (parsed && parsed.framings && parsed.framings.length) data = parsed; } catch (e) { console.warn('[framing] bad framingData', e); } }

  function leanLabel(l) {
    if (l > 25) return 'Optimistic';
    if (l > 5) return 'Constructive';
    if (l >= -5) return 'Neutral';
    if (l >= -25) return 'Cautious';
    return 'Downbeat';
  }

  var active = 0;
  var card = document.createElement('div');
  card.className = 'frame-card';
  card.innerHTML =
    '<div class="frame-head">'
    +   '<span class="frame-kicker">One story, ' + data.framings.length + ' desks</span>'
    +   '<h3 class="frame-story"></h3>'
    + '</div>'
    + '<div class="frame-tabs" data-el="tabs"></div>'
    + '<div class="frame-body">'
    +   '<p class="frame-outlet" data-el="outlet"></p>'
    +   '<p class="frame-headline" data-el="headline"></p>'
    +   '<p class="frame-angle" data-el="angle"></p>'
    +   '<blockquote class="frame-pull" data-el="pull"></blockquote>'
    +   '<div class="frame-scale">'
    +     '<div class="frame-scale-labels"><span>Bearish</span><span class="lean" data-el="lean"></span><span>Bullish</span></div>'
    +     '<div class="frame-track"><span class="frame-marker" data-el="marker"></span></div>'
    +   '</div>'
    + '</div>';

  function q(sel) { return card.querySelector('[data-el="' + sel + '"]'); }
  card.querySelector('.frame-story').textContent = data.storyTitle;

  data.framings.forEach(function(f, i) {
    var b = document.createElement('button');
    b.type = 'button';
    b.textContent = f.outlet;
    b.className = i === active ? 'active' : '';
    b.addEventListener('click', function() { active = i; sync(); });
    q('tabs').appendChild(b);
  });

  function sync() {
    var f = data.framings[active];
    var tabs = q('tabs').children;
    for (var i = 0; i < tabs.length; i++) tabs[i].className = i === active ? 'active' : '';
    q('outlet').textContent = f.outlet + ' headline';
    q('headline').textContent = '\u201C' + f.headline + '\u201D';
    q('angle').textContent = f.angle;
    q('pull').textContent = f.pull;
    q('lean').textContent = leanLabel(f.lean);
    q('marker').style.left = (((f.lean + 100) / 200) * 100) + '%';
  }

  mount.appendChild(card);
  sync();
})();
