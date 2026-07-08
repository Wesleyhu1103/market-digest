# AGENTS.md

Instructions for all coding agents (Cursor, v0, Claude Code) working in this repo.

## Where to work

Match the task to the right files — do not freehand-edit `index.html` structure:

| Task | Edit | Do NOT touch |
|------|------|--------------|
| Daily digest content | `incoming/new-main.html` (a full `<main>...</main>` block) | CSS, JS, nav, `index.html` template |
| Change the digest's HTML structure/rules | `contracts/digest-main.json` **first**, then run `python3 scripts/digest_contracts.py --check` | inline prompt/regex copies (there are none — the contract is the source) |
| Site template, styling, charts | `docs/css/`, `docs/js/`, `docs/index.html` shell | the daily `<main>` content |
| Shared constants (FRED, Vercel origin, repair) | `docs/site-config.json`, then `python3 scripts/sync_site_config.py` | `docs/js/site-config.js` (generated) |

**The structural contract for the daily `<main>` lives in one place: [`contracts/digest-main.json`](contracts/digest-main.json).** It drives both the Claude generation prompt (`scripts/generate_digest.py`) and the validator (`scripts/validate_digest.py`). Read it before writing `<main>`; edit it (not the scripts) when a rule changes. Human-readable examples and failure modes are in [`docs/AGENT_HANDOFF.md`](docs/AGENT_HANDOFF.md).

### Product overview

**Market Digest** is a static single-page newsletter hosted from `docs/`. There is no build step or bundler in this repo (Python scripts in `scripts/` support daily publish/validation; `api/` is a thin Vercel/Node layer with its own `package.json`).

### Running the site locally

Serve `docs/` over HTTP (required for `fetch()` of `fred-data.json` and `archive/manifest.json`):

```bash
cd docs && python3 -m http.server 8080
```

Open http://localhost:8080 in a browser. Outbound network is needed for Chart.js CDN, Google Fonts, and the live verdict scoreboard (Yahoo Finance via CORS proxies).

### Validation (lint equivalent)

```bash
python3 scripts/digest_contracts.py --check    # contract JSON sane (regexes compile, prompt non-empty)
python3 scripts/validate_digest.py docs/index.html
```

Requires **Python 3** (stdlib only) and **Node.js** on PATH (inline JS parse check). All structural checks should pass. Both commands run in CI (`publish-digest.yml` and `sync-agent-branches.yml`) — a `v0/*` or `claude/*` branch that drifts from the contract fails before it can merge to `main`.

### Optional maintenance scripts

| Script | Purpose |
|--------|---------|
| `scripts/update_fred.py` | Refresh `docs/fred-data.json` from FRED CSV API |
| `scripts/repair_main.py` | Repair generated `<main>` HTML before publish |
| `scripts/validate_digest.py` | Structural + JS checks (local file or live GitHub raw URL) |
| `contracts/digest-main.json` | Shared HTML contract for generate + validate |

Publishing requires `GITHUB_TOKEN` in the environment; see `docs/AGENT_HANDOFF.md`.

### Dependencies

Serving/validating the static site needs no install — just **Python 3** and **Node.js** on PATH. The `api/` Vercel functions have their own `package.json` (Postgres client); that's only needed when working on the API layer, not the digest.

### Dev log (all agents: Claude Code, Cursor, v0)

Before starting any fix, search `dev-log/` for entries about the same
file/feature; entries flagged `→ didn't hold` are failed approaches — do
not repeat them.

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
