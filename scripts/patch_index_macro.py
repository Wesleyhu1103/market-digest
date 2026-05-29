#!/usr/bin/env python3
"""Strip inline FRED blobs from index.html; load docs/fred-data.json instead."""
import re
from pathlib import Path

INDEX = Path(__file__).resolve().parents[1] / "docs" / "index.html"
html = INDEX.read_text()

html = html.replace("function _initAllCharts() {", "async function _initAllCharts() {")

inject = """
  let macro = null;
  try {
    const mr = await fetch('fred-data.json', { cache: 'no-store' });
    if (mr.ok) macro = await mr.json();
  } catch (e) { console.warn('fred-data.json unavailable', e); }
  const fred = (macro && macro.fred) ? macro.fred : { DGS2: [], DGS10: [], DGS30: [] };
  const brent = (macro && macro.brent) ? macro.brent : [];
  const creditData = (macro && macro.credit) ? macro.credit : { HY_OAS: [], IG_OAS: [], VIX: [], TENMINUSTWO: [] };

"""

marker = "  document.querySelectorAll('script#chartData').forEach(el => {"
if marker not in html:
    raise SystemExit("chartData marker not found")
html = html.replace(marker, inject + marker, 1)

html = re.sub(
    r"  // ── 3\. Treasury yields.*?if \(document\.getElementById\('treasuryYields'\)\) \{\n    const fred = \{.*?\};\n",
    "  // ── 3. Treasury yields (docs/fred-data.json) ──\n  if (document.getElementById('treasuryYields') && fred.DGS10 && fred.DGS10.length) {\n",
    html,
    count=1,
    flags=re.DOTALL,
)

html = re.sub(
    r"  // ── 4\. Brent crude.*?if \(document\.getElementById\('brentChart'\)\) \{\n    const brent = \[.*?\];\n",
    "  // ── 4. Brent crude (docs/fred-data.json) ──\n  if (document.getElementById('brentChart') && brent.length) {\n",
    html,
    count=1,
    flags=re.DOTALL,
)

html = re.sub(
    r"  // ── 6 & 7\. Credit \+ Stress.*?const creditData = \{.*?\};\n\n  if \(document\.getElementById\('creditChart'\)\)",
    "  // ── 6 & 7. Credit + Stress (docs/fred-data.json) ──\n  if (document.getElementById('creditChart') && creditData.HY_OAS && creditData.HY_OAS.length)",
    html,
    count=1,
    flags=re.DOTALL,
)

html = html.replace(
    "if (document.getElementById('stressChart')) {",
    "if (document.getElementById('stressChart') && creditData.VIX && creditData.VIX.length) {",
    1,
)

INDEX.write_text(html)
print("Patched", INDEX, "size", INDEX.stat().st_size)
