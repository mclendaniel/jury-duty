#!/usr/bin/env python3
"""Alameda County jury duty checker for group 143.

Fetches the court's jury reporting page, determines if group 143
must report or remains on standby, and sends a push notification
via ntfy.sh.
"""

import re
import sys
from datetime import date

import requests
from bs4 import BeautifulSoup

GROUP = 143
NTFY_TOPIC = "morgan-jury-duty-143"
URL = "https://www.alameda.courts.ca.gov/juryreporting"
LAST_DAY = date(2026, 3, 12)


def fetch_page():
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_instructions(html):
    """Parse the jury reporting page and return status for our group.

    Returns a dict with:
      - must_report: bool
      - message: str (human-readable summary)
    """
    soup = BeautifulSoup(html, "html.parser")
    blockquotes = soup.find_all("blockquote")

    for bq in blockquotes:
        text = bq.get_text(" ", strip=True)

        # Look for group number ranges like "1 - 10" or "11-170"
        range_match = re.search(r"Group\s+Numbers?\s*:\s*(\d+)\s*[-–]\s*(\d+)", text, re.IGNORECASE)
        if not range_match:
            # Also check for a single group number
            single_match = re.search(r"Group\s+Numbers?\s*:\s*(\d+)\b", text, re.IGNORECASE)
            if single_match:
                low = high = int(single_match.group(1))
            else:
                continue
        else:
            low = int(range_match.group(1))
            high = int(range_match.group(2))

        if not (low <= GROUP <= high):
            continue

        # This blockquote covers our group — check if it's a report or standby
        is_standby = "not needed" in text.lower() or "standby" in text.lower()

        if is_standby:
            return {
                "must_report": False,
                "message": f"No action: Group {GROUP} is still on standby.",
            }

        # Extract date, time, location from the blockquote
        date_match = re.search(r"Date:\s*(.+?)(?:\s{2,}|$)", text)
        time_match = re.search(r"Time:\s*(.+?)(?:\s{2,}|$)", text)
        loc_match = re.search(r"Location:\s*(.+?)(?:\s{2,}|$)", text)

        details = []
        if date_match:
            details.append(f"Date: {date_match.group(1).strip()}")
        if time_match:
            details.append(f"Time: {time_match.group(1).strip()}")
        if loc_match:
            details.append(f"Location: {loc_match.group(1).strip()}")

        detail_str = "\n".join(details) if details else "(check website for details)"

        return {
            "must_report": True,
            "message": f"REPORT: Group {GROUP} must report tomorrow!\n{detail_str}",
        }

    # Group not found on the page at all
    return {
        "must_report": None,
        "message": f"WARNING: Could not find group {GROUP} on the jury reporting page. Check manually: {URL}",
    }


def notify(message, priority="default"):
    """Send a push notification via ntfy.sh."""
    headers = {"Title": f"Jury Duty - Group {GROUP}"}
    if priority != "default":
        headers["Priority"] = priority
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers=headers,
        timeout=15,
    )


def main():
    today = date.today()
    if today > LAST_DAY:
        sys.exit(0)

    html = fetch_page()
    result = parse_instructions(html)

    priority = "default"
    if result["must_report"]:
        priority = "urgent"
    elif result["must_report"] is None:
        priority = "high"

    notify(result["message"], priority=priority)
    print(result["message"])


if __name__ == "__main__":
    main()
