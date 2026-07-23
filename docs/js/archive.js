// ============================================================
// ARCHIVE — built from docs/archive/manifest.json
// ============================================================
(function() {
  function sitePath(rel) {
    if (typeof mdSiteRootPath === 'function') return mdSiteRootPath(rel);
    var path = window.location.pathname || '/';
    var archiveAt = path.indexOf('/archive/');
    if (archiveAt !== -1) path = path.slice(0, archiveAt + 1);
    else if (/\.[a-z0-9]+$/i.test(path)) path = path.replace(/[^/]+$/, '');
    else if (!path.endsWith('/')) path += '/';
    return path + String(rel || '').replace(/^\//, '');
  }

  function ensureArchiveSection() {
    var mount = document.getElementById('archive-mount');
    if (mount) return mount;
    var section = document.createElement('section');
    section.id = 'archive';
    section.innerHTML = '<h2>Archive</h2>'
      + '<div id="archive-mount"><p style="font-size:14px;color:var(--muted);">Loading archive\u2026</p></div>';
    var content = document.querySelector('.content');
    if (content) content.appendChild(section);
    else {
      var mainEl = document.querySelector('main');
      if (mainEl) mainEl.insertAdjacentElement('afterend', section);
      else document.body.appendChild(section);
    }
    return document.getElementById('archive-mount');
  }

  var mount = ensureArchiveSection();
  if (!mount) return;
  var todayIso = null;
  var edition = window.DigestDate && DigestDate.headerEdition();
  if (edition) todayIso = edition.iso;
  fetch(sitePath('archive/manifest.json'), { cache: 'no-store' })
    .then(function(r) { return r.ok ? r.json() : []; })
    .catch(function() { return []; })
    .then(function(entries) {
      entries = (entries || []).slice().sort(function(a, b) { return b.date.localeCompare(a.date); });
      if (!entries.length) {
        mount.innerHTML = '<p style="font-size:14px;color:var(--muted);">No archived digests yet.</p>';
        return;
      }
      function fmtShort(iso) {
        var d = new Date(iso + 'T12:00:00');
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      }
      var html = '';
      if (todayIso) {
        html += '<div class="arch-today">'
          + '<span class="arch-date">Today</span>'
          + '<span class="arch-title">' + (document.querySelector('header.head h1') ? document.querySelector('header.head h1').textContent : 'Live digest') + '</span>'
          + '<span class="arch-today-note">You are reading today&apos;s live edition.</span></div>';
      }
      var list = '';
      entries.forEach(function(e) {
        var title = e.summary ? e.summary.slice(0, 120) : (e.h1 || e.date);
        var href = sitePath(e.url || '');
        list += '<a class="arch-item" href="' + href + '">'
          + '<span class="arch-item-date">' + (e.h1 || e.date) + '</span>'
          + '<span class="arch-item-summary">' + title + '</span>'
          + '</a>';
      });
      var range = fmtShort(entries[entries.length - 1].date) + ' \u2013 ' + fmtShort(entries[0].date);
      html += '<details class="arch-group">'
        + '<summary><span class="arch-range">Prior editions \u00b7 ' + range + '</span>'
        + '<span class="arch-count">' + entries.length + ' issues</span></summary>'
        + '<div class="arch-list">' + list + '</div></details>';
      mount.innerHTML = html;
      if (typeof onScroll === 'function') onScroll();
    });
})();
