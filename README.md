# Market Digest

Daily market newsletter hosted at [wesleyhu1103.github.io/market-digest](https://wesleyhu1103.github.io/market-digest).

## Repository layout

| Path | Purpose |
|------|---------|
| `docs/` | Static site (GitHub Pages root) — `index.html` is the live digest |
| `docs/archive/` | Prior-day snapshots + `manifest.json` for the archive UI |
| `docs/fred-data.json` | Macro chart data refreshed by `scripts/update_fred.py` |
| `incoming/new-main.html` | Drop zone for daily `<main>` content (consumed by Actions) |
| `scripts/` | Publish, repair, validate, and FRED refresh utilities |
| `.github/workflows/publish-digest.yml` | Daily cron + deploy pipeline |

## Local development

```bash
cd docs && python3 -m http.server 8080
python3 scripts/validate_digest.py docs/index.html
```

See `docs/AGENT_HANDOFF.md` for HTML contracts and the publish flow. See `AGENTS.md` for Cursor Cloud agent notes.

## Auto-update troubleshooting

The weekday cron publishes ~7:30am US/Eastern. If the site looks stale:

1. **GitHub → Actions → Publish digest → Run workflow** (manual catch-up).
2. Confirm repo secret **`ANTHROPIC_API_KEY`** exists (Settings → Secrets → Actions).
3. Optional: **`FRED_API_KEY`** for macro charts when FRED blocks GitHub IPs.
4. After any push to `main`, the workflow auto-runs if `docs/index.html` is behind today's date.

Both [GitHub Pages](https://wesleyhu1103.github.io/market-digest) and Vercel redeploy on every `main` push.
