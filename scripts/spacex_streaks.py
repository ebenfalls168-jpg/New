"""Is the SpaceX (SPCX) post-IPO trough predictable from streaks?

Usage:
    python scripts/spacex_streaks.py                 # fetch via yfinance
    python scripts/spacex_streaks.py --csv data.csv  # Date,Open,High,Low,Close[,Volume]

Questions answered:
  1. After N up (or down) days in a row, how often is the next day up?
     Compared with the base rate, with an exact binomial p-value.
  2. Where were the swing lows (troughs), what led into them, and what followed?
  3. Would a simple "buy after N down days" rule have landed near those troughs?
"""
import argparse
import math
import os
import sys

import pandas as pd

IPO_PRICE = 135.0
IPO_DATE = "2026-06-12"


def load(csv, ticker):
    if csv:
        df = pd.read_csv(csv, parse_dates=["Date"]).set_index("Date")
    else:
        import yfinance as yf
        df = yf.download(ticker, start=IPO_DATE, auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].dropna().sort_index()
    if df.empty:
        sys.exit(f"No price data for {ticker}")
    return df


def binom_p(k, n, p):
    """Two-sided exact binomial test."""
    if n == 0:
        return float("nan")
    pmf = [math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(n + 1)]
    return min(1.0, sum(x for x in pmf if x <= pmf[k] * (1 + 1e-9)))


def streak_lengths(ret):
    """Signed length of the streak ending on each day (+3 = third up day in a row)."""
    out, cur = [], 0
    for r in ret:
        if r > 0:
            cur = cur + 1 if cur > 0 else 1
        elif r < 0:
            cur = cur - 1 if cur < 0 else -1
        else:
            cur = 0
        out.append(cur)
    return pd.Series(out, index=ret.index)


def streak_table(ret, max_n):
    streak = streak_lengths(ret)
    nxt = ret.shift(-1)
    base = (ret > 0).mean()
    rows = []
    for direction, sign in (("up", 1), ("down", -1)):
        for n in range(1, max_n + 1):
            mask = (streak * sign >= n) & nxt.notna()
            k = int((nxt[mask] > 0).sum())
            cnt = int(mask.sum())
            rows.append({
                "after": f"{n}+ {direction}",
                "cases": cnt,
                "next up %": round(100 * k / cnt, 1) if cnt else None,
                "avg next %": round(100 * nxt[mask].mean(), 2) if cnt else None,
                "p vs base": round(binom_p(k, cnt, base), 3) if cnt else None,
            })
    return pd.DataFrame(rows), base


def swing_lows(df, w):
    lo = df["Low"]
    is_min = lo == lo.rolling(2 * w + 1, center=True).min()
    return df.index[is_min.fillna(False)]


def down_into(streak, i):
    """Down-close streak leading into day i (the low day itself may close up)."""
    for j in (i, i - 1):
        if j >= 0 and streak.iloc[j] < 0:
            return int(-streak.iloc[j])
    return 0


def trough_table(df, ret, w):
    streak = streak_lengths(ret)
    close = df["Close"]
    rows = []
    for d in swing_lows(df, w):
        i = df.index.get_loc(d)
        peak = df["High"].iloc[: i + 1].max()
        peak_day = df["High"].iloc[: i + 1].idxmax()
        fwd = lambda h: round(100 * (close.iloc[i + h] / close.iloc[i] - 1), 1) if i + h < len(df) else None
        rows.append({
            "date": d.date(),
            "low": round(df["Low"].iloc[i], 2),
            "off peak %": round(100 * (df["Low"].iloc[i] / peak - 1), 1),
            "days from peak": (df.index[i] - peak_day).days,
            "down days into it": down_into(streak, i),
            "fwd 5d %": fwd(5),
            "fwd 10d %": fwd(10),
        })
    return pd.DataFrame(rows)


def rule_check(df, ret, max_n, w, tol):
    """For 'buy at close after N down days': how many signals were within tol days of a swing low?"""
    streak = streak_lengths(ret)
    lows = [df.index.get_loc(d) for d in swing_lows(df, w)]
    close = df["Close"]
    rows = []
    for n in range(1, max_n + 1):
        sig = [df.index.get_loc(d) for d in streak.index[streak == -n]]
        near = sum(any(abs(s - l) <= tol for l in lows) for s in sig)
        caught = sum(any(abs(s - l) <= tol for s in sig) for l in lows)
        f5 = [close.iloc[s + 5] / close.iloc[s] - 1 for s in sig if s + 5 < len(df)]
        rows.append({
            "N down": n,
            "signals": len(sig),
            f"signals near a low (±{tol}d)": near,
            f"lows caught ({len(lows)} total)": caught,
            "avg fwd 5d %": round(100 * sum(f5) / len(f5), 2) if f5 else None,
        })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--ticker", default="SPCX")
    ap.add_argument("--max-streak", type=int, default=5)
    ap.add_argument("--window", type=int, default=3, help="swing-low half-width in trading days")
    args = ap.parse_args()

    df = load(args.csv, args.ticker)
    ret = df["Close"].pct_change().dropna()
    close = df["Close"]
    low_day = df["Low"].idxmin()

    out = []
    p = out.append
    p(f"# {args.ticker} streak & trough analysis\n")
    p(f"- Data: {df.index[0].date()} → {df.index[-1].date()}, {len(df)} trading days")
    p(f"- IPO price ${IPO_PRICE:.2f}; first close ${close.iloc[0]:.2f}; last close ${close.iloc[-1]:.2f} "
      f"({100 * (close.iloc[-1] / IPO_PRICE - 1):+.1f}% vs IPO)")
    p(f"- All-time high ${df['High'].max():.2f} on {df['High'].idxmax().date()}; "
      f"lowest low ${df['Low'].min():.2f} on {low_day.date()} "
      f"(trading day #{df.index.get_loc(low_day) + 1})")
    p(f"- Daily volatility {100 * ret.std():.2f}%, up days {100 * (ret > 0).mean():.1f}%\n")

    table, base = streak_table(ret, args.max_streak)
    p(f"## 1. What happens after a streak? (base rate: next day up {100 * base:.1f}%)\n")
    p(table.to_markdown(index=False))
    n_tests = int(table["cases"].gt(0).sum())
    p(f"\n{n_tests} tests run → Bonferroni threshold p < {0.05 / max(n_tests, 1):.4f}. "
      f"Rows with fewer than ~20 cases cannot distinguish a real edge from noise.\n")

    p(f"## 2. Swing lows (lowest low within ±{args.window} trading days)\n")
    p(trough_table(df, ret, args.window).to_markdown(index=False))

    p("\n## 3. Does 'buy after N down days in a row' find the troughs?\n")
    p(rule_check(df, ret, args.max_streak, args.window, tol=1).to_markdown(index=False))

    text = "\n".join(out)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
