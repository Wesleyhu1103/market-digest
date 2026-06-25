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
| `.github/workflows/publish-digest.yml` | Generate, validate, commit, deploy pipeline |
| `.github/workflows/digest-watchdog.yml` | Morning stale-check; triggers publish when cron is delayed |

## Local development

```bash
cd docs && python3 -m http.server 8080
python3 scripts/validate_digest.py docs/index.html
```

See `docs/AGENT_HANDOFF.md` for HTML contracts and the publish flow. See `AGENTS.md` for Cursor Cloud agent notes.

## Auto-update troubleshooting

The weekday publish window targets **~7:30am US/Eastern**, but GitHub's shared
cron runners are often delayed 1–2 hours at peak load. Two workflows cover this:

| Workflow | Role |
|----------|------|
| **Digest watchdog** | Every 15 min (7–11am ET weekdays); triggers publish only while stale |
| **Publish digest** | Generates, validates, commits, and deploys |

If the site looks stale after 10am ET:

1. **GitHub → Actions → Publish digest → Run workflow** (manual catch-up).
2. Confirm repo secret **`ANTHROPIC_API_KEY`** exists (Settings → Secrets → Actions).
3. **`FRED_API_KEY`** (recommended) for fresh macro charts.
4. Any push to `main` while `docs/index.html` is behind today's date also auto-runs publish.

Both [GitHub Pages](https://wesleyhu1103.github.io/market-digest) and [Vercel](https://market-digest-liart.vercel.app) redeploy on every `main` push.

### v0 / Claude Code → live site

Edits from **v0** or **Claude Code** land on `v0/*` or `claude/*` branches. They are **not** live until merged to `main`. The **Sync agent branch to main** workflow auto-merges those branches after validation passes, which triggers deploy. If a merge conflicts with `main`, open a PR on GitHub and resolve manually.
