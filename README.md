# IPO tools

## Anthropic IPO alert
`.github/workflows/anthropic-ipo-alert.yml` runs every 30 minutes and opens a GitHub
issue (assigned to the repo owner, so GitHub emails you) when any stock named Anthropic
starts trading, whatever its ticker.

Optional repository secrets (Settings → Secrets and variables → Actions):

- `SEC_USER_AGENT`: also alert on each IPO filing stage on SEC EDGAR (S-1 amendment, exchange
  registration 8-A12B, SEC effectiveness, pricing 424B4). SEC only answers tools that declare
  themselves with a contact email, e.g. `IPO alert you@example.com`. Filings already on EDGAR at
  the first run are recorded silently. If SEC still refuses GitHub's runners, the run fails
  (and GitHub emails you); remove the secret to go back to trading-only alerts.
- `NTFY_TOPIC`: phone push. Install the ntfy app and subscribe to a hard-to-guess topic name.

A failed run means a check broke; GitHub emails you about failed scheduled runs.

## SpaceX streak analysis
`python scripts/spacex_streaks.py` (or the "SpaceX streak analysis" workflow) fetches SPCX
daily prices since the 12 Jun 2026 IPO and reports next-day odds after up/down streaks,
the swing lows, and whether "buy after N down days" would have caught them.
