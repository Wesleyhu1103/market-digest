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

## Step 5: Repair, commit, validate

```python
import base64, json, os, re, subprocess, tempfile, urllib.request
from datetime import date, datetime

TOKEN = os.environ["GITHUB_TOKEN"]
OWNER = "wesleyhu1103"
REPO  = "market-digest"
PATH  = "docs/index.html"
H = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}

def gh_get(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}", headers=H)
    return json.load(urllib.request.urlopen(req))

def gh_put(path, content, message, sha=None):
    payload = {"message": message, "content": base64.b64encode(content.encode()).decode(), "branch": "main"}
    if sha: payload["sha"] = sha
    req = urllib.request.Request(
        f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}",
        data=json.dumps(payload).encode(), method="PUT",
        headers={**H, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))

# ── 1. Fetch current index.html ──
data = gh_get(PATH)
sha  = data["sha"]
current_html = base64.b64decode(data["content"].replace("\n","")).decode()

# ── 2. Archive prior day if different date ──
old_h1   = re.search(r'<h1>([^<]+)</h1>', current_html)
old_meta = re.search(r'<div class="meta">([\s\S]*?)</div>', current_html)
today_iso = date.today().isoformat()

if old_h1:
    try:
        dt = datetime.strptime(old_h1.group(1).strip(), "%A, %B %d, %Y")
        old_date_iso = dt.strftime("%Y-%m-%d")
    except ValueError:
        old_date_iso = None

    if old_date_iso and old_date_iso != today_iso:
        banner = (
            '<div style="background:var(--accent-soft);border-left:4px solid var(--accent);'
            'padding:14px 22px;margin:0 0 18px;font-size:14px;">'
            f'<strong>Archived — {old_date_iso}</strong> · '
            '<a href="../index.html" style="color:var(--accent);">← back to today</a></div>'
        )
        snapshot = re.sub(r'<main>', '<main>\n' + banner, current_html, count=1)
        archive_path = f"docs/archive/{old_date_iso}.html"
        try:
            gh_put(archive_path, snapshot, f"Archive {old_date_iso}")
            print(f"Archived {archive_path}")
        except urllib.error.HTTPError as e:
            if e.code != 422: raise

        summary = ""
        if old_meta:
            summary = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', old_meta.group(1))).strip()[:240]
        new_entry = {"date": old_date_iso, "weekday": dt.strftime("%a"),
                     "h1": old_h1.group(1).strip(), "summary": summary,
                     "url": f"archive/{old_date_iso}.html"}
        try:
            m = gh_get("docs/archive/manifest.json")
            manifest = json.loads(base64.b64decode(m["content"].replace("\n","")).decode())
            manifest_sha = m["sha"]
        except urllib.error.HTTPError as e:
            if e.code == 404: manifest, manifest_sha = [], None
            else: raise
        manifest = [e for e in manifest if e.get("date") != old_date_iso] + [new_entry]
        manifest.sort(key=lambda e: e["date"])
        gh_put("docs/archive/manifest.json", json.dumps(manifest, indent=2),
               f"Manifest entry {old_date_iso}", sha=manifest_sha)
        print(f"Manifest updated ({len(manifest)} entries)")

# ── 3. Repair main HTML ──
# Pull repair_main.py from repo and exec it
repair_src = base64.b64decode(gh_get("scripts/repair_main.py")["content"].replace("\n","")).decode()
exec(compile(repair_src, "repair_main.py", "exec"))
main_html = repair_main_html(NEW_MAIN)   # NEW_MAIN = your generated <main>...</main> string

# ── 4. Replace <main> block ──
new_html = re.sub(r'<main>.*?</main>', main_html, current_html, count=1, flags=re.DOTALL)

# ── 5. Update date strings ──
today = date.today()
new_html = re.sub(r'Market Digest\s*[—\-]\s*[\w,\s]+\d{4}',
                  f'Market Digest — {today.strftime("%a %b %-d, %Y")}', new_html)
new_html = re.sub(r"date:\s*'\d{4}-\d{2}-\d{2}'", f"date: '{today_iso}'", new_html)
new_html = re.sub(r"marketDigest_feedback_\d{4}-\d{2}-\d{2}",
                  f"marketDigest_feedback_{today_iso}", new_html)

# ── 6. JS parse check before commit ──
scripts = re.findall(r'<script>([\s\S]*?)</script>', new_html)
body = max(scripts, key=len) if scripts else ""
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
    f.write(body); tmp = f.name
r = subprocess.run(["node", "-e",
    f"try{{new Function(require('fs').readFileSync('{tmp}','utf8'));console.log('OK')}}"
    f"catch(e){{console.log('FAIL:'+e.message)}}"],
    capture_output=True, text=True, timeout=10)
os.unlink(tmp)
print("JS parse:", r.stdout.strip())
if r.stdout.strip() != "OK":
    raise SystemExit("ABORT: JS parse failed")

# ── 7. Commit ──
result = gh_put(PATH, new_html, f"Daily digest {today_iso}", sha=sha)
print("Published:", result["commit"]["html_url"])
print("Live: https://wesleyhu1103.github.io/market-digest")
```

After publishing, run `scripts/validate_digest.py` (fetch it from the repo the same way as `repair_main.py`) and report PASS/FAIL counts. If any check fails, say so explicitly — do not silently pass.

Also run `update_fred.py` to refresh macro chart data:
```python
fred_src = base64.b64decode(gh_get("scripts/update_fred.py")["content"].replace("\n","")).decode()
exec(compile(fred_src, "update_fred.py", "exec"))
```
