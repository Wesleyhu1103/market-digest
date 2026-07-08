// Repair agent-generated <main> markup before binding event listeners
function repairMainDOM() {
  const main = document.querySelector('main');
  if (!main) return;

  const chartHeights = { techMovers: 320, treasuryYields: 280, brentChart: 280, creditChart: 240, stressChart: 240, redditSentiment: 240, dealSizes: 240 };
  Object.keys(chartHeights).forEach(id => {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (parent && parent.style && parent.style.position === 'relative' && parent.style.height) return;
    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:relative;height:' + chartHeights[id] + 'px;width:100%';
    canvas.replaceWith(wrap);
    wrap.appendChild(canvas);
  });

  const chartNodes = [...main.querySelectorAll('script#chartData')];
  let merged = {};
  chartNodes.forEach(el => {
    try { merged = Object.assign(merged, JSON.parse(el.textContent)); } catch (_) {}
  });
  chartNodes.forEach(el => el.remove());
  if (Object.keys(merged).length) {
    const tag = document.createElement('script');
    tag.type = 'application/json';
    tag.id = 'chartData';
    tag.textContent = JSON.stringify(merged);
    main.appendChild(tag);
  }

  main.querySelectorAll('.narrative, .buyside-summary').forEach(n => {
    let bb = n.querySelector('.bullbear');
    const legacy = n.querySelector('.bull-bear-toggle');
    if (legacy && !bb) {
      bb = document.createElement('div');
      bb.className = 'bullbear show-bull';
      const parts = legacy.querySelectorAll('.bb-content, [class*="bb-content"]');
      if (parts.length >= 2) {
        const bull = document.createElement('div'); bull.className = 'bull'; bull.innerHTML = parts[0].innerHTML;
        const bear = document.createElement('div'); bear.className = 'bear'; bear.innerHTML = parts[1].innerHTML;
        bb.append(bull, bear);
      }
      legacy.replaceWith(bb);
    }
    let toggles = n.querySelector('.toggles');
    if (!toggles) {
      toggles = document.createElement('div');
      toggles.className = 'toggles';
      if (bb) n.insertBefore(toggles, bb);
      else n.appendChild(toggles);
    }
    if (!toggles.querySelector('[data-side="bull"]')) {
      toggles.innerHTML = '<button type="button" class="bull on" data-side="bull">Bull</button><button type="button" class="bear" data-side="bear">Bear</button><button type="button" data-side="both">Both</button>';
    } else if (!toggles.querySelector('[data-side="both"]')) {
      const bothBtn = document.createElement('button');
      bothBtn.type = 'button';
      bothBtn.dataset.side = 'both';
      bothBtn.textContent = 'Both';
      toggles.appendChild(bothBtn);
    }
    if (!bb) return;
    if (!bb.querySelector('.bull') || !bb.querySelector('.bear')) return;
    const onBtn = toggles.querySelector('button.on') || toggles.querySelector('[data-side="bull"]');
    toggles.querySelectorAll('button').forEach(b => b.classList.remove('on'));
    if (onBtn) onBtn.classList.add('on');
    bb.classList.remove('show-bull', 'show-bear');
    const side = onBtn ? onBtn.dataset.side : 'bull';
    if (side === 'bear') bb.classList.add('show-bear');
    else if (side !== 'both') bb.classList.add('show-bull');
  });

  main.querySelectorAll('.quiz .opt').forEach(opt => {
    if (!opt.dataset.opt && opt.dataset.val) opt.dataset.opt = String(opt.dataset.val).toLowerCase();
    if (opt.dataset.opt) opt.dataset.opt = String(opt.dataset.opt).toLowerCase();
  });
  main.querySelectorAll('.quiz .q').forEach(q => {
    if (q.dataset.correct) q.dataset.correct = String(q.dataset.correct).toLowerCase();
  });

  ['fb-missing', 'fb-open'].forEach(id => {
    const el = document.getElementById(id);
    if (el && el.tagName !== 'TEXTAREA') {
      const ta = document.createElement('textarea');
      ta.id = id;
      ta.rows = 4;
      ta.className = el.className || '';
      ta.placeholder = el.getAttribute('placeholder') || '';
      ta.value = el.textContent || '';
      el.replaceWith(ta);
    }
  });
}
repairMainDOM();
