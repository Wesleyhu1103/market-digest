# Market Digest — Agent Handoff

Last updated: 2026-05-29. Read this before touching anything.

## Architecture

Single-page app at `wesleyhu1103.github.io/market-digest`.

```
.github/workflows/
  publish-digest.yml ← Actions pipeline: archive, repair, validate, FRED, Pages deploy
docs/
  index.html        ← the entire site; only <main> changes daily
  fred-data.json    ← macro chart data (FRED); refreshed by update_fred.py
  archive/
    manifest.json   ← list of prior digests; updated by publish_digest.py
    YYYY-MM-DD.html ← snapshots of prior days
incoming/
  new-main.html     ← drop zone: the digest agent's ONLY write; consumed by Actions
scripts/
  publish_digest.py ← runs in Actions: archive prior day, repair, splice <main>, update dates
  repair_main.py    ← run on generated main_html before committing
  validate_digest.py← structural + JS parse checks after committing
  update_fred.py    ← fetches FRED series daily; write to fred-data.json
```

**You only replace `<main>...</main>` daily.** Everything else — CSS, JS, nav, chart rendering, archive mounting, verdict updater — is in the static template and must not be touched.

---

## Daily publish sequence

**Fully automated (default):** the `Publish digest` workflow's weekday cron
(7:30am ET) runs `scripts/generate_digest.py` on GitHub's servers — fetches
the RSS feeds, calls the Claude API (`ANTHROPIC_API_KEY` repo secret) to
rewrite `<main>` from the current template, then archives the prior day,
repairs, splices, validates, refreshes FRED, commits, and deploys Pages.
No local machine or Claude session needed. Reddit sentiment is estimated
from headlines and labeled as such; Gmail newsletters are not available in
automated runs (historically ~2% of content).

**Manual override (Claude session):** steps 1-6 below still work — a session
can synthesize richer content (Gmail, Reddit scrape) and upload it:

1. Fetch market data (feeds, Gmail, Reddit)
2. Synthesize content
3. Generate `<main>...</main>` HTML
4. Upload it as `incoming/new-main.html` on `main` (GitHub connector tool preferred, Contents API fallback)
5. The `Publish digest` workflow does everything else in the repo: archive prior day, `repair_main.py`, splice into `index.html`, date updates, `validate_digest.py` gate, `update_fred.py`, commit, Pages deploy
6. Poll the workflow run (public API, no auth) and report success/failure

The cron also refreshes FRED data even when no digest lands.

---

## Token

The pipeline itself needs no PAT — Actions uses the built-in `GITHUB_TOKEN`.
The agent's single upload should use the GitHub connector/MCP tool when
available. If a token fallback is needed, use a **fine-grained PAT** scoped to
this repo with Contents read/write only, read from `os.environ["GITHUB_TOKEN"]`.
Never put a token in any file committed to the repo or in the skill file.
Note: regenerating a PAT on github.com invalidates the old value immediately —
update every stored copy the moment you regenerate, or runs will 401.

GitHub Pages must be set to **Settings → Pages → Source: GitHub Actions**
(one-time). Pushes made with the built-in `GITHUB_TOKEN` don't trigger the
legacy deploy-from-branch build, so the workflow deploys Pages explicitly.

---

## HTML contracts — what the static JS expects

### Bull/bear toggles

Every `.narrative` div must have exactly this structure:

```html
<div class="narrative" data-nar="bonds">   <!-- bonds | iran | aicapex -->
  <!-- content -->
  <div class="toggles">
    <button class="bull on" data-side="bull">Bull</button>
    <button class="bear" data-side="bear">Bear</button>
    <button data-side="both">Both</button>
  </div>
  <div class="bullbear show-bull">
    <div class="bull">...bull case...</div>
    <div class="bear">...bear case...</div>
  </div>
</div>
```

- `class="bull on"` — the `on` sets the active state on load
- `class="bullbear show-bull"` — makes bull content visible before first click
- Never use `bb-toggle-bar`, `bb-panel`, `bb-btn`, `bb-content`, or `onclick="toggleBB()"` — these are dead patterns that break silently

### chartData

Must be the **last element inside `<main>`**, right before `</main>`:

```html
<script type="application/json" id="chartData">{
  "techMovers": { "labels": [...], "values": [...] },
  "redditSentiment": { "labels": [...], "values": [...], "colors": [...] },
  "dealSizes": { "labels": [...], "values": [...] }
}</script>
</main>
```

- Exactly one `id="chartData"` tag
- `treasuryYields`, `brentChart`, `creditChart`, `stressChart` load from `fred-data.json` — do NOT include them here
- Positive `techMovers` values render green, negative red automatically

### Chart canvas wrappers

Every canvas must be in an explicit-height wrapper:

```html
<div style="position:relative;height:320px;width:100%"><canvas id="techMovers"></canvas></div>
```

Heights: `techMovers` 320px, `treasuryYields`/`brentChart` 280px, `creditChart`/`stressChart`/`redditSentiment`/`dealSizes` 240px.

`repair_main.py` will fix missing wrappers at publish time, but generate them correctly to avoid silent fallback.

### Quiz

```html
<div class="q" data-correct="B">
  <p><strong>1. Question?</strong></p>
  <span class="opt" data-opt="A">A. ...</span>
  <span class="opt" data-opt="B">B. ...</span>
  <span class="opt" data-opt="C">C. ...</span>
  <span class="opt" data-opt="D">D. ...</span>
  <div class="feedback"><strong>B is correct.</strong> Explanation.</div>
</div>
```

- `data-opt` not `data-val` — using `data-val` makes every answer show red

### Feedback

```html
<textarea id="verdictFb" rows="4" placeholder="Notes on today's verdict..."></textarea>
<button onclick="saveVerdictFeedback()">Save</button>
<span id="vfSaved" style="display:none;color:var(--bull);">Saved ✓</span>

<form class="fb" onsubmit="return submitFeedback(event)">
  <textarea id="fb-missing" rows="4" placeholder="What was missing?"></textarea>
  <textarea id="fb-open" rows="4" placeholder="Other thoughts?"></textarea>
  <div id="fb-success" style="display:none;">Thanks! Feedback saved.</div>
</form>
```

- `fb-missing` and `fb-open` must be `<textarea>` elements — `.value` is undefined on `<div>`
- `vfSaved` span must exist — JS calls `getElementById('vfSaved')` and errors silently without it

### Archive section

**Do NOT include `<section id="archive">` in `<main>`.** The template JS mounts the archive dynamically from `docs/archive/manifest.json` into `<div id="archive-mount">`. The commit script maintains the manifest.

### Verdict stacks

```html
<div class="narrative-stack" data-narrative="bonds">   <!-- bonds | iran-oil | ai-capex -->
  <div class="stack-cell pending">
    <span class="cell-name">N · Label</span><span class="cell-val">pending</span>
  </div>
  <!-- 5 cells total per stack -->
  <div class="ns-verdict pending">Verdict: Pending</div>
</div>
```

15 stack cells total (5 per narrative), all `class="stack-cell pending"` on morning publish.

---

## Section order inside `<main>`

1. `<header class="head">` — kicker, h1 date, meta
2. `<section id="narratives">` — three `.narrative` divs
3. `<section id="equities">`
4. `<section id="tech">` — includes `techMovers` chart
5. `<section id="macro">` — includes `treasuryYields`, `brentChart`, `creditChart`, `stressChart` canvases
6. `<section id="verdict" class="verdict-section">` — three narrative-stacks, scoreboard, feedback
7. `<section id="crypto">`
8. `<section id="deals">` — includes `dealSizes` chart
9. `<section id="buyside">`
10. `<section id="sentiment">` — includes `redditSentiment` chart
11. `<section id="learn">`
12. `<section id="ondeck">`
13. `<section id="sources">`
14. `<section id="quiz" class="quiz">`
15. `<section id="feedback">`
16. `<script type="application/json" id="chartData">...</script>` ← LAST, before `</main>`

---

## Repair and validate scripts

Always run both before/after publish:

```python
# Before commit — repair_main.py
import sys
sys.path.insert(0, 'scripts')
from repair_main import repair_main_html
main_html = repair_main_html(main_html)

# After commit — validate_digest.py
python3 scripts/validate_digest.py
```

`repair_main.py` aborts with `SystemExit` if toggle structure can't be fixed (fewer than 3 bull-on / show-bull found after repair). Fix the source HTML, don't suppress the error.

---

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Bear toggle shows blank | Missing `show-bull` on `.bullbear` | `repair_main.py` or fix source |
| All quiz answers red | `data-val` instead of `data-opt` | `repair_main.py` |
| Charts blank | Canvas not in height wrapper | `repair_main.py` |
| ALL interactivity dead | Unescaped apostrophe in JS string | Find `'...'s...'` pattern, escape or use double quotes |
| Archive not loading | Missing `archive-mount` div or manifest empty | Template mounts dynamically — don't add static archive HTML |
| Feedback save broken | `fb-missing`/`fb-open` on `<div>` not `<textarea>` | Fix source HTML |
