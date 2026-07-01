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
| `api/cron-watchdog.js` | Vercel Cron backup (once daily on Hobby); dispatches publish when stale |
| `vercel.json` | Vercel static output + cron config |

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
| **Digest watchdog** | Every 15 min (7am–2pm ET weekdays); triggers publish only while stale |
| **Publish digest** | Generates, validates, commits, deploys Pages, syncs Vercel |

If the site looks stale after 10am ET:

1. **GitHub → Actions → Publish digest → Run workflow** (manual catch-up).
2. Confirm repo secret **`ANTHROPIC_API_KEY`** exists (Settings → Secrets → Actions).
3. **`FRED_API_KEY`** (recommended) for fresh macro charts.
4. Any push to `main` while `docs/index.html` is behind today's date also auto-runs publish.

Both [GitHub Pages](https://wesleyhu1103.github.io/market-digest) and [Vercel](https://market-digest-liart.vercel.app) update from the same **Publish digest** workflow run — not from arbitrary git pushes alone.

### How both hosts stay in sync

```
Publish digest workflow
  ├─ build   → generate, validate, commit + push to main
  └─ deploy  → GitHub Pages (docs/)  →  POST VERCEL_DEPLOY_HOOK
```

| Host | Mechanism | Why |
|------|-----------|-----|
| **GitHub Pages** | `deploy-pages` in Actions | `GITHUB_TOKEN` pushes don't trigger legacy Pages builds |
| **Vercel** | Deploy hook after Pages | Explicit, runs only after validated content is on `main` |

**Recommended:** In Vercel → **market-digest** → Settings → **Git**, turn off automatic production deploys on push (keep the repo connected for previews if you want). The deploy hook is the single source of truth — git auto-deploy can fail silently (e.g. invalid `vercel.json` cron) or race the hook.

One-time setup (done if `VERCEL_DEPLOY_HOOK` is in repo secrets):

1. Vercel → Settings → **Git** → **Deploy Hooks** → hook for branch `main`
2. GitHub → repo **Secrets → Actions** → **`VERCEL_DEPLOY_HOOK`** = hook URL

Optional Vercel env vars (Project → Settings → Environment Variables):

| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` | PAT with `actions:write` — lets `/api/cron-watchdog` dispatch publish when GitHub cron lags |
| `CRON_SECRET` | Auto-set by Vercel Cron; leave default unless you call the endpoint manually |

**Vercel Hobby cron limit:** one run per day (`vercel.json` uses `0 12 * * 1-5`). Hourly schedules block production deploys on Hobby.

Create the hook from CLI (after `vercel login`):

```bash
npx vercel deploy-hook create "GitHub Actions publish" --ref main
gh secret set VERCEL_DEPLOY_HOOK --body "<hook-url-from-output>"
```

### v0 / Claude Code → live site

Edits from **v0** or **Claude Code** land on `v0/*` or `claude/*` branches. They are **not** live until merged to `main`. The **Sync agent branch to main** workflow auto-merges those branches after validation passes, which triggers deploy. If a merge conflicts with `main`, open a PR on GitHub and resolve manually.
