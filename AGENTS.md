# AGENTS.md

## Cursor Cloud specific instructions

### Product overview

**Market Digest** is a static single-page newsletter hosted from `docs/`. There is no build step, package manager, or backend server in this repo. Python scripts in `scripts/` support daily publish and validation only.

### Running the site locally

Serve `docs/` over HTTP (required for `fetch()` of `fred-data.json` and `archive/manifest.json`):

```bash
cd docs && python3 -m http.server 8080
```

Open http://localhost:8080 in a browser. Outbound network is needed for Chart.js CDN, Google Fonts, and the live verdict scoreboard (Yahoo Finance via CORS proxies).

### Validation (lint equivalent)

```bash
python3 scripts/validate_digest.py docs/index.html
```

Requires **Python 3** (stdlib only) and **Node.js** on PATH (inline JS parse check). All 12 structural checks should pass.

### Optional maintenance scripts

| Script | Purpose |
|--------|---------|
| `scripts/update_fred.py` | Refresh `docs/fred-data.json` from FRED CSV API |
| `scripts/repair_main.py` | Repair generated `<main>` HTML before publish |
| `scripts/validate_digest.py` | Structural + JS checks (local file or live GitHub raw URL) |

Publishing requires `GITHUB_TOKEN` in the environment; see `docs/AGENT_HANDOFF.md`.

### Dependencies

No `npm install`, `pip install`, or Docker. System requirements: **Python 3** and **Node.js** only.

### Dev log (all agents: Claude Code, Cursor, v0)

After completing any fix or feature, append a 2–3 line entry to
`dev-log/YYYY-MM.md` (format in `dev-log/README.md`): date + what changed,
why, and any gotchas. If the change redoes something a previous entry
already fixed, add `Redo of: YYYY-MM-DD` to the new entry and append
`→ didn't hold, see YYYY-MM-DD` to the old entry's first line. Do not
create or edit daily market notes — those are written by hand.

### Gotchas

- Do not open `docs/index.html` via `file://` — JSON fetches will fail.
- Only replace `<main>...</main>` for daily content updates; the static template (CSS, JS, nav) must stay intact per `docs/AGENT_HANDOFF.md`.
- Long-running dev server: use tmux if starting `python3 -m http.server` in the background.
- **Vercel vs GitHub Pages:** Both update from the **Publish digest** deploy job — Pages via `deploy-pages`, Vercel via **`VERCEL_DEPLOY_HOOK`**. Disable Vercel git auto-deploy on production; rely on the hook. Hobby plan allows only one cron/day in `vercel.json`.
