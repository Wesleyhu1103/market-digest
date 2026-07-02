# What to log in Obsidian (from the digest)

Everything in the daily digest that's worth capturing by hand in
`market-notes/`, mapped section by section. The dev log next to this file
is the automated half; this guide is for the manual half. Log the
*judgment*, not the content — the digest itself is already archived in
`docs/archive/`.

## Log daily (the 5-minute note in `market-notes/daily/`)

| Digest section | What to write in your note |
|---|---|
| **Today's Verdict** | The single highest-value log. Before close: which way you'd lean on each of the three narratives (Bonds/Rates vs 4.56–4.70% on 10Y, Iran/Oil vs $70–80 Brent, AI Capex vs $205–220 NVDA). Next morning: what the verdict actually was and whether you agreed for the right reason. This is a graded track record the site computes for you. |
| **Dominant Narratives** | Which narrative you think is overpriced or underpriced today, one line each, with `[[links]]` (e.g. `[[oil]]`, `[[Fed]]`, `[[AI capex]]`). |
| **Framing** (top of digest) | Only if your own framing differs — "digest says X, I think the real story is Y." |

## Log when notable (append to theme notes in `market-notes/themes/`)

| Digest section | What to capture |
|---|---|
| **Macro & Rates** | Level changes that cross a threshold you care about (10Y through 4.70%, curve moves). One line in `[[rates]]` with the date. |
| **US Equities / Tech & Growth** | New names entering the story. One line in that ticker's note (`[[NVDA]]`) — why it appeared, not what it did. |
| **Crypto** | Regime shifts only (correlation flips, ETF flow reversals), not daily moves. |
| **Deals & Capital Markets** | Every named deal — one line in `[[deals]]`: deal, multiple/size, why it printed now. This becomes IB interview prep for "talk about a recent deal." |
| **Buyside Positioning** | When positioning contradicts the narrative sections — that tension is usually the trade. |
| **Reddit & Retail Sentiment** | Extremes only. Note them in the relevant ticker's theme note as a contrarian timestamp. |
| **Learning Opportunity** | If the concept was new to you, make it a permanent note in `themes/` in your own words (e.g. `[[leveraged ETF decay]]`). Rewriting it is what makes it stick. |
| **On Deck Next Week** | Copy the one event you think matters most into tomorrow's daily note as the "question to revisit." |
| **Quick Quiz** | If you got it wrong, one line in the relevant theme note about why. |

## Log weekly (Friday, 10 minutes)

- **Week Scoreboard** (in the Verdict section): your hit rate vs the three
  narratives this week. One summary line in a `[[scoreboard]]` note —
  where you were systematically wrong (always too bullish on rates?).
- **Community Votes / Feedback**: only if reader feedback changed what
  you'd cover — one line in `[[digest-direction]]`.

## Never log by hand

- Anything in `dev-log/` — pipeline fixes, workflow changes, deploy issues.
  Agents (Claude Code, Cursor, v0) append those automatically.
- The digest content itself — `docs/archive/` already keeps every day's
  HTML snapshot. Link to it, don't copy it.

## Daily note template (copy into Obsidian)

```markdown
## Moves
- 

## Verdict leans (before close)
- Bonds/Rates: 
- Iran/Oil: 
- AI Capex: 

## Yesterday's grade
- Verdict said:  · I said:  · Right/wrong because: 

## Question for tomorrow
- 
```
