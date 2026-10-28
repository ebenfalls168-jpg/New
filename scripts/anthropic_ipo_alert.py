"""Watch for Anthropic's IPO milestones and report the ones not seen before.

Checks SEC EDGAR for the filings that mark each IPO stage, and Yahoo Finance
for the ticker actually trading. Prints new events as JSON lines and records
them in a state file so each one is reported once.

    python scripts/anthropic_ipo_alert.py --state .ipo-state.json

Env: SEC_USER_AGENT  enables the EDGAR checks; SEC requires a declared tool name
                     and contact, e.g. "IPO alert you@example.com". Unset = skip EDGAR.
     ANTHROPIC_CIK   skip the CIK lookup
     NTFY_TOPIC      optional phone push via ntfy.sh
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = os.environ.get("SEC_USER_AGENT", "")
YAHOO = "https://query1.finance.yahoo.com"

# EDGAR form type -> what it means for the IPO
STAGES = {
    "S-1": "Public S-1 registration statement filed",
    "S-1/A": "S-1 amended (often adds the price range and share count)",
    "8-A12B": "Registered shares on an exchange (trading usually within days)",
    "EFFECT": "SEC declared the registration effective (pricing imminent)",
    "424B4": "Final prospectus filed: IPO priced",
    "424B1": "Final prospectus filed: IPO priced",
}


def get_json(url, ua=UA):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from {url}") from e


def find_cik():
    if os.environ.get("ANTHROPIC_CIK"):
        return os.environ["ANTHROPIC_CIK"]
    q = urllib.parse.urlencode({"q": '"Anthropic PBC"', "forms": "S-1,S-1/A"})
    hits = get_json(f"https://efts.sec.gov/LATEST/search-index?{q}")["hits"]["hits"]
    for h in hits:
        for cik, name in zip(h["_source"]["ciks"], h["_source"]["display_names"]):
            if name.upper().startswith("ANTHROPIC"):
                return cik
    return None


def edgar_events(cik):
    data = get_json(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
    recent = data["filings"]["recent"]
    for form, date, acc in zip(recent["form"], recent["filingDate"], recent["accessionNumber"]):
        if form in STAGES:
            yield {
                "id": f"edgar:{acc}",
                "title": f"Anthropic IPO: {STAGES[form]} ({form}, {date})",
                "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={urllib.parse.quote(form)}",
            }


def trading_event():
    """Any listed equity named Anthropic with a live price, whatever its ticker."""
    q = urllib.parse.urlencode({"q": "Anthropic", "quotesCount": 10, "newsCount": 0})
    quotes = get_json(f"{YAHOO}/v1/finance/search?{q}", ua="ipo-alert")["quotes"]
    for quote in quotes:
        name = (quote.get("longname") or quote.get("shortname") or "").lower()
        if quote.get("quoteType") != "EQUITY" or not name.startswith("anthropic"):
            continue
        sym = quote["symbol"]
        meta = get_json(f"{YAHOO}/v8/finance/chart/{sym}?range=5d&interval=1d", ua="ipo-alert")["chart"]["result"][0]["meta"]
        if meta.get("regularMarketPrice"):
            return {
                "id": f"trading:{sym}",
                "title": f"Anthropic is TRADING as {sym} on {quote.get('exchDisp', quote.get('exchange'))}: ${meta['regularMarketPrice']:.2f}",
                "url": f"https://finance.yahoo.com/quote/{sym}",
            }
    return None


def push(event):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}", data=event["title"].encode(),
        headers={"Title": "Anthropic IPO alert", "Click": event["url"], "Priority": "high"},
    )
    urllib.request.urlopen(req, timeout=30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=".ipo-state.json")
    args = ap.parse_args()

    seen = set()
    if os.path.exists(args.state):
        seen = set(json.load(open(args.state)))
    first_run = not seen

    events, edgar_ok, quote_ok = [], True, True
    try:
        if not UA:
            raise LookupError("SEC_USER_AGENT not set, skipping EDGAR")
        cik = find_cik()
        if cik:
            events += edgar_events(cik)
        else:
            print("warning: Anthropic not found on EDGAR yet", file=sys.stderr)
    except LookupError as e:
        print(f"notice: {e}", file=sys.stderr)
    except Exception as e:
        print(f"error: EDGAR check failed: {e}", file=sys.stderr)
        edgar_ok = False
    try:
        if ev := trading_event():
            events.append(ev)
    except Exception as e:
        print(f"error: quote check failed: {e}", file=sys.stderr)
        quote_ok = False

    for ev in events:
        if ev["id"] in seen:
            continue
        seen.add(ev["id"])
        # Filings already on file at the first run are recorded, not alerted,
        # except trading, which is always worth an alert.
        if first_run and not ev["id"].startswith("trading:"):
            continue
        print(json.dumps(ev))
        push(ev)

    with open(args.state, "w") as f:
        json.dump(sorted(seen), f, indent=1)
    # Fail the run so a broken check is noticed instead of going quiet.
    if not (edgar_ok and quote_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
