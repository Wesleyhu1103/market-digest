# Dev log

Running log of fixes and features in this repo, one markdown file per month
(`YYYY-MM.md`). Entries are appended automatically by coding agents
(Claude Code, Cursor, v0) at the end of each session — see the
"Dev log" section in [CLAUDE.md](../CLAUDE.md) and [AGENTS.md](../AGENTS.md).

## Entry format

```markdown
## 2026-07-02 — Short title of the change
- What: one line on what changed
- Why: one line on why
- Gotcha: anything that bit us (omit if none)
- Redo of: 2026-06-18 (only if this redoes an earlier "fix")
```

## Outcome tracking (what was good vs bad)

A fix is judged by whether it holds. When an agent re-fixes something,
it marks the earlier entry's first line with `→ didn't hold, see
YYYY-MM-DD`. So reading the log in Obsidian:

- **Entries never flagged** = changes that held. The good list.
- **Entries flagged `didn't hold`** = the bad list. Search `didn't hold`
  (Cmd+Shift+F in Obsidian) to see every fix that had to be redone.

Weekly 5-minute review: search `didn't hold`, and for anything that has
been redone twice, the fix is treating a symptom — write one line about
what the real cause might be.

## Reading this in Obsidian (one-time setup)

1. Open Obsidian → **File → Open Vault → Open folder as vault**
2. Pick either:
   - the `market-digest` repo folder (dev log only), or
   - a parent folder containing both `market-digest/` and your
     `market-notes/` vault, so `[[links]]` work across both.
3. That's it — these files are plain markdown, so Obsidian is just a viewer.
   The log is versioned with the code via normal git commits.

Daily market notes (your 3-bullet judgment notes) stay manual and live
outside this folder — don't let agents write those.
