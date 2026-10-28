# IPO tools

## Anthropic IPO alert
`.github/workflows/anthropic-ipo-alert.yml` runs every 30 minutes and opens a GitHub
issue (assigned to the repo owner, so GitHub emails you) when Anthropic reaches a new IPO stage:
S-1 amendment, exchange registration (8-A12B), SEC effectiveness, pricing (424B4), and
the ticker (`ANT` by default) trading. Filings already on EDGAR at the first run are recorded silently.

Optional phone push: install the ntfy app, subscribe to a hard-to-guess topic, and add it
as the repository secret `NTFY_TOPIC`.

## SpaceX streak analysis
`python scripts/spacex_streaks.py` (or the "SpaceX streak analysis" workflow) fetches SPCX
daily prices since the 12 Jun 2026 IPO and reports next-day odds after up/down streaks,
the swing lows, and whether "buy after N down days" would have caught them.
