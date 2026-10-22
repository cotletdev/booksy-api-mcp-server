#!/usr/bin/env python3
"""Compare last week with the week before for each staff member: appointments and revenue, with big moves flagged.

    python weekly_staff_report.py
    python weekly_staff_report.py --threshold 15 --out staff-week.json

Booksy counts whole weeks, Monday to Sunday. The Staff Members category is a Booksy Biz Pro report.
"""

import argparse
import re
from datetime import date, timedelta

from booksy_api_mcp.scripting import call, run, write_rows


def number(value: object) -> float:
    """Booksy formats money as text ("$2,310.00", "1 234,50 zł"): the number in it."""
    if isinstance(value, (int, float)):
        return float(value)
    digits = re.sub(r"[^\d,.-]", "", str(value or "0"))
    if "," in digits and (digits.rfind(",") > digits.rfind(".")):
        digits = digits.replace(".", "").replace(",", ".")
    return float(digits.replace(",", "") or 0)


def staff_rows(monday: date) -> dict[str, dict]:
    report = call(
        "get_report", {"category": "staff_members", "from": str(monday), "to": str(monday + timedelta(days=6))}
    )
    rows: dict[str, dict] = {}
    for section in report["sections"]:
        for row in section.get("rows") or []:
            staffer = row.get("staffer")
            # Booksy names the staff member as text or as {"name": ..., "images": ...}.
            name = staffer.get("name") if isinstance(staffer, dict) else staffer
            if name:
                rows.setdefault(name, {}).update({k: v for k, v in row.items() if k != "staffer"})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--threshold", type=float, default=20, help="Flag changes larger than this percent")
    parser.add_argument("--out", help="Save to .csv or .json instead of printing")
    args = parser.parse_args()

    last = date.today() - timedelta(days=date.today().weekday() + 7)
    now, before = staff_rows(last), staff_rows(last - timedelta(days=7))
    out = []
    for name in sorted(set(now) | set(before)):
        a, b = now.get(name, {}), before.get(name, {})
        revenue, prior = number(a.get("total_revenue")), number(b.get("total_revenue"))
        change = round((revenue - prior) / prior * 100, 1) if prior else None
        out.append(
            {
                "staff": name,
                "appointments": a.get("subbookings_count", 0),
                "appointments_before": b.get("subbookings_count", 0),
                "revenue": a.get("total_revenue"),
                "revenue_before": b.get("total_revenue"),
                "revenue_change_pct": change,
                "flag": change is not None and abs(change) > args.threshold,
            }
        )
    write_rows(out, args.out)


if __name__ == "__main__":
    run(main)
