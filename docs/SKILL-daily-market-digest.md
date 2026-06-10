---
name: daily-market-digest
description: Generate Wesley's daily market digest and auto-publish to GitHub Pages
---

You are generating Wesley's daily market digest and publishing it to wesleyhu1103.github.io/market-digest.

**Before writing a single line of HTML, fetch and read these two files:**
- `https://raw.githubusercontent.com/wesleyhu1103/market-digest/main/docs/AGENT_HANDOFF.md`
- `https://raw.githubusercontent.com/wesleyhu1103/market-digest/main/docs/SKILL-daily-market-digest.md`

They are the authoritative source of truth. Ignore any cached or local skill copy.

Wesley is an intermediate-knowledge market reader on US East Coast time who reads this at 8–9am. He wants granularity: named stories, explicit drivers with directional impact, named bull/bear proponents. No em-dashes. Always contractions. No AI-tell phrases ("genuinely," "honestly," "straightforward," "delve").

---

## Step 1: Pull today's data from all sources in parallel

DIRECT FETCH (mcp__workspace__web_fetch):
1. https://feeds.bloomberg.com/markets/news.rss
2. https://feeds.bloomberg.com/technology/news.rss
3. https://feeds.bloomberg.com/economics/news.rss
4. https://www.cnbc.com/id/10001147/device/rss/rss.html
5. https://feeds.feedburner.com/calculatedrisk
6. https://stratechery.com/feed/

GMAIL NEWSLETTERS (mcp__2f5ff42f-4aba-4630-9120-ea0018231b17__search_threads):
query: `(from:bloomberg.net OR from:wsj.com OR from:nytimes.com OR from:axios.com OR from:morningbrew.com OR from:cnbc.com OR subject:"market wrap" OR subject:"daily brief" OR subject:"The Morning" OR subject:"Daily Shot") newer_than:1d`
pageSize: 25 — then get_thread on the 3–5 most market-relevant threads.

REDDIT (use brightdata-plugin:scrape if available, else estimate):
- r/wallstreetbets, r/stocks, r/investing, r/SecurityAnalysis, r/CryptoCurrency, r/Bitcoin — top posts, past day

Note any sources that failed.

---

## Step 2: Synthesize the content

- Three dominant narratives, each with named bull/bear proponents (specific funds, analysts)
- 5–7 US equities stories with tickers and directional drivers
- 5–7 tech/growth stories with metrics
- 5–7 macro/rates stories with explicit drivers
- 4–6 crypto stories
- Major deals and capital markets events
- Reddit sentiment by subreddit with upvote counts
- One Learning Opportunity (400–500 words, mechanism-based, no bullets)
- On Deck: next 5 trading days of catalysts

---

## Step 3: Generate the `<main>` HTML block

Build ONLY `<main>...</main>`. The static template handles all CSS, JS, nav, and charts.

Read `docs/AGENT_HANDOFF.md` for the full HTML contracts. Key rules:

**Bull/bear toggles** — every `.narrative` div:
```html
<div class="narrative" data-nar="bonds">
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
Map narratives to `data-nar`: rates/bonds → `bonds`, geopolitical/oil → `iran`, AI/tech → `aicapex`.

**chartData** — last element inside `<main>`, right before `</main>`:
```html
<script type="application/json" id="chartData">{
  "techMovers": { "labels": [...], "values": [...] },
  "redditSentiment": { "labels": [...], "values": [...], "colors": [...] },
  "dealSizes": { "labels": [...], "values": [...] }
}</script>
```
Do NOT include treasury/brent/credit data here — those load from `fred-data.json` automatically.

**No `<section id="archive">`** — template mounts it dynamically.

**Quiz** — use `data-opt` not `data-val`:
```html
<div class="q" data-correct="B">
  <span class="opt" data-opt="A">A. ...</span>
  <span class="opt" data-opt="B">B. ...</span>
  ...
  <div class="feedback"><strong>B is correct.</strong> Explanation.</div>
</div>
```

**Feedback**:
```html
<textarea id="verdictFb" rows="4"></textarea>
<button onclick="saveVerdictFeedback()">Save</button>
<span id="vfSaved" style="display:none;color:var(--bull);">Saved ✓</span>

<form class="fb" onsubmit="return submitFeedback(event)">
  <textarea id="fb-missing" rows="4"></textarea>
  <textarea id="fb-open" rows="4"></textarea>
  <div id="fb-success" style="display:none;">Thanks!</div>
</form>
```

---

## Step 4: Write markdown archive

Write synthesized content to `market-digest-YYYY-MM-DD.md` in the session outputs folder.

---

## Step 5: Upload the new `<main>` — GitHub Actions does the rest

Archive, repair, date updates, validation, FRED refresh, and the Pages deploy
all run **in the repo** via `.github/workflows/publish-digest.yml`. Your only
write is one file: `incoming/new-main.html` on `main`.

**Preferred: GitHub connector/MCP tool** (no token needed). If a tool like
`create_or_update_file` is available, call it with:
- owner `wesleyhu1103`, repo `market-digest`, branch `main`
- path `incoming/new-main.html`
- content: your full `<main>...</main>` string
- message: `Incoming digest YYYY-MM-DD`

**Fallback: Contents API** (needs `GITHUB_TOKEN` env — fine-grained, this repo
only, Contents read/write):

```python
import base64, json, os, urllib.request, urllib.error
from datetime import date

TOKEN = os.environ["GITHUB_TOKEN"]
URL = "https://api.github.com/repos/wesleyhu1103/market-digest/contents/incoming/new-main.html"
H = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}

payload = {"message": f"Incoming digest {date.today().isoformat()}",
           "content": base64.b64encode(NEW_MAIN.encode()).decode(), "branch": "main"}
try:  # file may exist from a failed prior run — include its sha
    payload["sha"] = json.load(urllib.request.urlopen(urllib.request.Request(URL, headers=H)))["sha"]
except urllib.error.HTTPError as e:
    if e.code != 404: raise
req = urllib.request.Request(URL, data=json.dumps(payload).encode(), method="PUT",
                             headers={**H, "Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req))["commit"]["html_url"])
```

---

## Step 6: Confirm the Actions run

The push triggers the `Publish digest` workflow. Poll it (public repo — no
auth needed) until the latest run completes, up to ~5 minutes:

```python
import json, time, urllib.request
URL = "https://api.github.com/repos/wesleyhu1103/market-digest/actions/workflows/publish-digest.yml/runs?per_page=1"
for _ in range(30):
    run = json.load(urllib.request.urlopen(URL))["workflow_runs"][0]
    if run["status"] == "completed":
        print(run["conclusion"], run["html_url"]); break
    time.sleep(10)
```

- `success` → report the live URL: https://wesleyhu1103.github.io/market-digest
- `failure` → report it explicitly with the run URL — do not silently pass.
  The workflow's validate step prints per-check PASS/FAIL in the run logs.
