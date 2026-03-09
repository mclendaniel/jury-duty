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


def _parse_group_range(text):
    """Extract (low, high) group range from blockquote text, or None."""
    range_match = re.search(r"Group\s+Numbers?\s*:\s*(\d+)\s*[-–]\s*(\d+)", text, re.IGNORECASE)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    single_match = re.search(r"Group\s+Numbers?\s*:\s*(\d+)\b", text, re.IGNORECASE)
    if single_match:
        n = int(single_match.group(1))
        return n, n
    return None


def _extract_details(text):
    """Extract time and location from a blockquote's text."""
    time_match = re.search(r"Time:\s*(.+?)(?:\s{2,}|$)", text)
    loc_match = re.search(r"Location:\s*(.+?)(?:\s{2,}|$)", text)
    parts = []
    if time_match:
        parts.append(time_match.group(1).strip())
    if loc_match:
        parts.append(loc_match.group(1).strip())
    return ", ".join(parts) if parts else None


def parse_instructions(html):
    """Parse the jury reporting page and return status for our group.

    Returns a dict with:
      - must_report: bool | None
      - message: str (human-readable summary)
    """
    soup = BeautifulSoup(html, "html.parser")
    blockquotes = soup.find_all("blockquote")

    called_groups = []  # list of (range_str, details_str)
    our_status = None   # will be set to a result dict

    for bq in blockquotes:
        text = bq.get_text(" ", strip=True)
        group_range = _parse_group_range(text)
        if not group_range:
            continue

        low, high = group_range
        is_standby = "not needed" in text.lower() or "standby" in text.lower()

        # Collect groups that must report (not standby)
        if not is_standby:
            range_str = str(low) if low == high else f"{low}-{high}"
            details = _extract_details(text)
            called_groups.append((range_str, details))

        # Check if this blockquote covers our group
        if low <= GROUP <= high:
            if is_standby:
                our_status = {"must_report": False}
            else:
                details = _extract_details(text)
                our_status = {"must_report": True, "details": details}

    # Build the called-groups summary
    if called_groups:
        called_lines = []
        for range_str, details in called_groups:
            if details:
                called_lines.append(f"  Groups {range_str}: {details}")
            else:
                called_lines.append(f"  Groups {range_str}")
        called_summary = "Called today:\n" + "\n".join(called_lines)
    else:
        called_summary = "No groups called today."

    # Build the final message
    if our_status is None:
        return {
            "must_report": None,
            "message": f"WARNING: Could not find group {GROUP} on the page. Check manually: {URL}\n\n{called_summary}",
        }

    if our_status["must_report"]:
        detail_str = our_status["details"] or "(check website for details)"
        return {
            "must_report": True,
            "message": f"REPORT: Group {GROUP} must report tomorrow!\n{detail_str}\n\n{called_summary}",
        }

    return {
        "must_report": False,
        "message": f"Group {GROUP} is on standby.\n\n{called_summary}",
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
