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

## Price alerts
`.github/workflows/price-alert.yml` checks every 15 minutes during US market hours and opens a
GitHub issue (plus an ntfy push if `NTFY_TOPIC` is set) when a stock's day low reaches a level.
It fires once per crossing and re-arms after the price recovers 5% above the level.
Current alert: SPCX at $108 (20% below the $135 IPO price). Add more by adding lines to
the "Check prices" step.

## Email alerts to another address
Both alert workflows also email each alert when these repository secrets are set
(Settings → Secrets and variables → Actions):

- `ALERT_EMAIL`: where to send alerts
- `SMTP_USERNAME` / `SMTP_PASSWORD`: the sending account. For Gmail, use the full address and an
  [app password](https://myaccount.google.com/apppasswords) (needs 2-step verification).
- `SMTP_SERVER` / `SMTP_PORT`: only for providers other than Gmail (default `smtp.gmail.com`, 465)
