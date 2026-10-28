"""Email each alert in a JSON-lines file ({"title", "body"} per line).

    python scripts/send_email.py events.jsonl

Env (set as repository secrets): ALERT_EMAIL (recipient), SMTP_USERNAME,
SMTP_PASSWORD, SMTP_SERVER (default smtp.gmail.com), SMTP_PORT (default 465, SSL).
Does nothing if ALERT_EMAIL is unset.
"""
import json
import os
import smtplib
import sys
from email.message import EmailMessage


def main():
    to = os.environ.get("ALERT_EMAIL")
    if not to:
        return
    with open(sys.argv[1]) as f:
        events = [json.loads(line) for line in f if line.strip()]
    if not events:
        return
    user = os.environ["SMTP_USERNAME"]
    server = os.environ.get("SMTP_SERVER") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or 465)
    with smtplib.SMTP_SSL(server, port, timeout=30) as smtp:
        smtp.login(user, os.environ["SMTP_PASSWORD"])
        for ev in events:
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = user, to, ev["title"]
            msg.set_content(ev.get("body") or ev.get("url", ""))
            smtp.send_message(msg)
            print(f"emailed: {ev['title']}")


if __name__ == "__main__":
    main()
