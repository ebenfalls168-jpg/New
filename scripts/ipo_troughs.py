"""How deep was the post-IPO trough, and when did it come? Across many hot IPOs.

For each IPO, within its first year of trading (default 252 trading days):
  - first-day pop vs the offer price
  - the peak before the trough
  - the trough: lowest low, which trading day it came on, and how far it was
    below the offer price, the first-day close and the earlier peak
  - where it trades now vs the offer price and the first-day close

    python scripts/ipo_troughs.py [--days 252]
"""
import argparse
import os

import pandas as pd
import yfinance as yf

# ticker: (first trading day, offer price per share as at IPO)
IPOS = {
    "META": ("2012-05-18", 38.0),   # Facebook
    "BABA": ("2014-09-19", 68.0),
    "SNAP": ("2017-03-02", 17.0),
    "LYFT": ("2019-03-29", 72.0),
    "PINS": ("2019-04-18", 19.0),
    "ZM":   ("2019-04-18", 36.0),
    "BYND": ("2019-05-02", 25.0),
    "UBER": ("2019-05-10", 45.0),
    "SNOW": ("2020-09-16", 120.0),
    "DASH": ("2020-12-09", 102.0),
    "ABNB": ("2020-12-10", 68.0),
    "BMBL": ("2021-02-11", 43.0),
    "HOOD": ("2021-07-29", 38.0),
    "RIVN": ("2021-11-10", 78.0),
    "ARM":  ("2023-09-14", 51.0),
    "CART": ("2023-09-19", 30.0),
    "KVYO": ("2023-09-20", 30.0),
    "ALAB": ("2024-03-20", 36.0),
    "RDDT": ("2024-03-21", 34.0),
    "CRWV": ("2025-03-28", 40.0),
    "CRCL": ("2025-06-05", 31.0),
    "CHYM": ("2025-06-12", 27.0),
    "FIG":  ("2025-07-31", 33.0),
    "SPCX": ("2026-06-12", 135.0),
}


def split_factor(ticker, after):
    """Cumulative split ratio since `after`, to put the offer price on Yahoo's split-adjusted scale."""
    s = yf.Ticker(ticker).splits
    if s.empty:
        return 1.0
    s.index = s.index.tz_localize(None)
    return float(s[s.index > pd.Timestamp(after)].prod() or 1.0)


def analyse(ticker, first_day, offer, days):
    df = yf.download(ticker, start=first_day, auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["High", "Low", "Close"]].dropna()
    if df.empty:
        return None
    last = df["Close"].iloc[-1]
    last_date = df.index[-1].date().isoformat()
    df = df.head(days)
    offer /= split_factor(ticker, first_day)
    lo_i = int(df["Low"].values.argmin())
    pre = df.iloc[: lo_i + 1]
    pk_i = int(pre["High"].values.argmax())
    first_close = df["Close"].iloc[0]
    trough = df["Low"].iloc[lo_i]
    return {
        "ticker": ticker,
        "ipo": first_day,
        "data from": df.index[0].date().isoformat(),
        "days": len(df),
        "day-1 pop %": 100 * (first_close / offer - 1),
        "peak day": pk_i + 1,
        "trough day": lo_i + 1,
        "trough date": df.index[lo_i].date().isoformat(),
        "vs offer %": 100 * (trough / offer - 1),
        "vs day-1 close %": 100 * (trough / first_close - 1),
        "vs peak %": 100 * (trough / pre["High"].iloc[pk_i] - 1),
        "below offer": trough < offer,
        # Trough on the last day(s) of the window: still falling, so the true low came later.
        "still falling": lo_i >= len(df) - 5,
        "latest close": last,
        "latest date": last_date,
        "now vs offer %": 100 * (last / offer - 1),
        "now vs day-1 close %": 100 * (last / first_close - 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=252)
    args = ap.parse_args()

    rows = [r for t, (d, p) in IPOS.items() if (r := analyse(t, d, p, args.days))]
    df = pd.DataFrame(rows)
    full = df[df["days"] >= args.days]  # IPOs with a complete first year

    out = []
    p = out.append
    p(f"# Post-IPO troughs: first {args.days} trading days\n")
    p(df.round(1).to_markdown(index=False))
    for label, d in (("All IPOs", df), (f"Only IPOs with a full {args.days} days of data", full)):
        p(f"\n## {label} (n={len(d)})\n")
        p(f"- Trough day: median {d['trough day'].median():.0f}, mean {d['trough day'].mean():.0f}, "
          f"middle half between day {d['trough day'].quantile(.25):.0f} and {d['trough day'].quantile(.75):.0f}")
        for col in ("vs offer %", "vs day-1 close %", "vs peak %"):
            p(f"- Trough {col}: median {d[col].median():.1f}, mean {d[col].mean():.1f}, "
              f"range {d[col].min():.1f} to {d[col].max():.1f}")
        p(f"- Fell below the offer price: {int(d['below offer'].sum())} of {len(d)}")
        p(f"- Still falling at the end of the window: {int(d['still falling'].sum())} of {len(d)}")
        p(f"- Peak day: median {d['peak day'].median():.0f}")
    p("\n## Where are they now?\n")
    now = df[["ticker", "ipo", "latest date", "latest close", "now vs offer %", "now vs day-1 close %"]]
    p(now.sort_values("now vs offer %", ascending=False).round(1).to_markdown(index=False))
    p(f"\n- Above the offer price now: {int((df['now vs offer %'] > 0).sum())} of {len(df)}")
    p(f"- Above the first-day close now: {int((df['now vs day-1 close %'] > 0).sum())} of {len(df)}")
    bins = [0, 21, 63, 126, 189, args.days]
    labels = ["month 1", "months 2-3", "months 4-6", "months 7-9", "months 10-12"]
    p(f"\n## When did the trough come? (full-year IPOs)\n")
    p(pd.cut(full["trough day"], bins, labels=labels).value_counts().sort_index().to_markdown())

    text = "\n".join(out)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
