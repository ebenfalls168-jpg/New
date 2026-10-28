"""Alert when a stock trades at or below a price.

    python scripts/price_alert.py SPCX 108 --state .price-state.json

Uses the day's low, so an intraday dip to the level counts. Alerts once per
crossing; re-arms after the price recovers 5% above the level. Prints one
JSON line ({"title", "body"}) when an alert fires, and nothing otherwise.
"""
import argparse
import json
import os
import sys
import urllib.request

REARM = 1.05


def quote(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "price-alert"})
    with urllib.request.urlopen(req, timeout=30) as r:
        meta = json.load(r)["chart"]["result"][0]["meta"]
    return meta["regularMarketPrice"], meta.get("regularMarketDayLow") or meta["regularMarketPrice"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("level", type=float)
    ap.add_argument("--note", default="", help="extra text for the alert, e.g. why this level")
    ap.add_argument("--state", default=".price-state.json")
    args = ap.parse_args()

    state = json.load(open(args.state)) if os.path.exists(args.state) else {}
    key = f"{args.ticker}<={args.level:g}"
    price, low = quote(args.ticker)
    print(f"{args.ticker}: price {price:.2f}, day low {low:.2f}, alert at {args.level:.2f}", file=sys.stderr)

    if low <= args.level and not state.get(key):
        state[key] = True
        print(json.dumps({
            "title": f"{args.ticker} hit ${low:.2f} (alert level ${args.level:.2f}) — now ${price:.2f}",
            "body": f"https://finance.yahoo.com/quote/{args.ticker}\n\n{args.note}".strip(),
        }))
    elif state.get(key) and price >= args.level * REARM:
        state[key] = False

    with open(args.state, "w") as f:
        json.dump(state, f)


if __name__ == "__main__":
    main()
