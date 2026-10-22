#!/usr/bin/env python3
"""List clients who have not been in for N days and have nothing booked in the next 30 days.

    python lapsed_clients.py --days 45
    python lapsed_clients.py --days 90 --out win-back.csv

The list a win-back message goes to (see win_back_blast.py). Clients with an visit booked in the next 30 days are left out.
"""

import argparse
from datetime import date, timedelta

from booksy_api_mcp.scripting import call, paginate, run, write_rows


def lapsed(days: int) -> list[dict]:
    """Clients past the cutoff, minus anyone with a visit booked in the next 31 days."""
    today = date.today()
    upcoming = call("list_appointments", {"from": str(today), "to": str(today + timedelta(days=30))})["appointments"]
    booked = {a["client_id"] for a in upcoming if a["status"] not in ("cancelled", "declined")}
    clients = paginate("list_clients", {"not_visited_days": days, "limit": 100}, "clients")
    return [c for c in clients if str(c["client_id"]) not in booked]


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--days", type=int, default=45, help="Days since the last visit, default 45")
    parser.add_argument("--out", help="Save to .csv or .json instead of printing")
    args = parser.parse_args()
    rows = [
        {k: c.get(k) for k in ("client_id", "name", "email", "phone", "last_visit", "visits", "revenue")}
        for c in lapsed(args.days)
    ]
    write_rows(rows, args.out)


if __name__ == "__main__":
    run(main)
