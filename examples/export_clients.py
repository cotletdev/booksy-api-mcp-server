#!/usr/bin/env python3
"""Export your Booksy clients to CSV or JSON: name, email, phone, note, visits, no-shows, revenue, last visit.

    python export_clients.py --out clients.csv
    python export_clients.py --search nowak
    python export_clients.py --not-visited-days 60 --out slipping-away.csv

Pages are followed automatically.
"""

import argparse

from booksy_api_mcp.scripting import paginate, run, write_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--search", help="Name, email or phone")
    parser.add_argument("--not-visited-days", type=int, help="Only clients whose last visit is older than this")
    parser.add_argument("--max", type=int, help="Stop after this many clients")
    parser.add_argument("--out", help="Save to .csv or .json instead of printing")
    args = parser.parse_args()

    params = {"query": args.search, "not_visited_days": args.not_visited_days, "limit": 100}
    write_rows(list(paginate("list_clients", params, "clients", args.max)), args.out)


if __name__ == "__main__":
    run(main)
