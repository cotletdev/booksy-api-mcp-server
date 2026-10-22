#!/usr/bin/env python3
"""Print tomorrow's Booksy appointments, one line each, and the open slots left for a service.

    python tomorrows_appointments.py
    python tomorrows_appointments.py --date 2026-10-27 --staff-id 882081
    python tomorrows_appointments.py --open-slots-for 8307205

Times are local to the business. Run it every evening from cron to see the next day at a glance.
"""

import argparse
from datetime import date, timedelta

from booksy_api_mcp.scripting import call, run


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--date", default=str(date.today() + timedelta(days=1)), help="YYYY-MM-DD, default tomorrow")
    parser.add_argument("--staff-id", help="Only this staff member (list_staff)")
    parser.add_argument("--open-slots-for", metavar="SERVICE_ID", help="Also list free starts for this service")
    args = parser.parse_args()

    found = call("list_appointments", {"from": args.date, "to": args.date, "staff_id": args.staff_id})
    visits = [a for a in found["appointments"] if a["status"] not in ("cancelled", "declined")]
    print(f"{args.date}: {len(visits)} appointments")
    for a in sorted(visits, key=lambda a: a["start"]):
        print(
            f"  {a['start'][11:16]}-{a['end'][11:16]}  {a['client']:<24} {a['service']:<24} {a['staff']} ({a['status']})"
        )

    if args.open_slots_for:
        slots = call(
            "find_open_slots", {"service_id": args.open_slots_for, "date": args.date, "staff_id": args.staff_id}
        )
        print(f"Open for {slots['service']}: " + (", ".join(s["start"][11:16] for s in slots["slots"]) or "none"))


if __name__ == "__main__":
    run(main)
