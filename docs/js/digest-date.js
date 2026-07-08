// Shared digest edition date parsing (mirrors scripts/digest_date.py).
(function () {
  'use strict';

  var MONTHS = {
    January: 0, February: 1, March: 2, April: 3, May: 4, June: 5,
    July: 6, August: 7, September: 8, October: 9, November: 10, December: 11
  };

  function parseH1Text(text) {
    if (!text) return null;
    var meta = String(text).match(/date:\s*'(\d{4}-\d{2}-\d{2})'/);
    if (meta) return { iso: meta[1] };
    var m = String(text).match(/(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})/);
    if (!m || MONTHS[m[2]] == null) return null;
    var mo = MONTHS[m[2]] + 1;
    var day = String(m[3]).padStart(2, '0');
    var iso = m[4] + '-' + String(mo).padStart(2, '0') + '-' + day;
    return {
      iso: iso,
      weekday: m[1],
      month: m[2],
      day: Number(m[3]),
      year: Number(m[4]),
      shortLabel: m[1].slice(0, 3) + ' ' + mo + '/' + m[3]
    };
  }

  function parseFromHtml(html) {
    var meta = html && html.match(/date:\s*'(\d{4}-\d{2}-\d{2})'/);
    if (meta) return { iso: meta[1] };
    var h1 = html && html.match(/<h1>([^<]+)<\/h1>/);
    return h1 ? parseH1Text(h1[1].trim()) : null;
  }

  function headerEdition() {
    var h1 = document.querySelector('header.head h1');
    return h1 ? parseH1Text(h1.textContent.trim()) : null;
  }

  function editionDayLabel() {
    var ed = headerEdition();
    return ed && ed.shortLabel ? ed.shortLabel : '';
  }

  window.DigestDate = {
    parseH1Text: parseH1Text,
    parseFromHtml: parseFromHtml,
    headerEdition: headerEdition,
    editionDayLabel: editionDayLabel
  };
})();
