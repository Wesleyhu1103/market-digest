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

Requires **Python 3** (stdlib only) and **Node.js** on PATH (inline JS parse check). As of setup, 11/12 structural checks pass locally; `fb-missing textarea` fails because the element is a `<div id="fb-missing">`, not a `<textarea>` — pre-existing mismatch between HTML and validator.

### Optional maintenance scripts

| Script | Purpose |
|--------|---------|
| `scripts/update_fred.py` | Refresh `docs/fred-data.json` from FRED CSV API |
| `scripts/repair_main.py` | Repair generated `<main>` HTML before publish |
| `scripts/validate_digest.py` | Structural + JS checks (local file or live GitHub raw URL) |

Publishing requires `GITHUB_TOKEN` in the environment; see `docs/AGENT_HANDOFF.md`.

### Dependencies

No `npm install`, `pip install`, or Docker. System requirements: **Python 3** and **Node.js** only.

### Gotchas

- Do not open `docs/index.html` via `file://` — JSON fetches will fail.
- Only replace `<main>...</main>` for daily content updates; the static template (CSS, JS, nav) must stay intact per `docs/AGENT_HANDOFF.md`.
- Long-running dev server: use tmux if starting `python3 -m http.server` in the background.
