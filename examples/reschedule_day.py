#!/usr/bin/env python3
"""Move one staff member's appointments on a day to colleagues who are free at about the same time.

    python reschedule_day.py --staff-id 882081 --date 2026-10-27
    python reschedule_day.py --staff-id 882081 --date 2026-10-27 --apply --notify

Without --apply it only prints the plan. With --apply each move is asked for, unless --yes. Appointments
nobody can take that day are listed so you can call those clients yourself.
"""

import argparse
from datetime import datetime

from booksy_api_mcp.scripting import call, run


def best_slot(appointment: dict, staff_id: str) -> dict | None:
    """The free start nearest the original time, with another staff member, within an hour."""
    detail = call("get_appointment", {"appointment_id": appointment["appointment_id"]})
    service_id = detail["services"][0]["service_id"]
    original = datetime.fromisoformat(appointment["start"])
    slots = call("find_open_slots", {"service_id": service_id, "date": appointment["start"][:10], "limit": 50})["slots"]
    others = [s for s in slots if s["staff_id"] != staff_id]
    others.sort(key=lambda s: abs((datetime.fromisoformat(s["start"]) - original).total_seconds()))
    if others and abs((datetime.fromisoformat(others[0]["start"]) - original).total_seconds()) <= 3600:
        return others[0]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--staff-id", required=True, help="Who is out, from list_staff")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--apply", action="store_true", help="Make the moves")
    parser.add_argument("--notify", action="store_true", help="Booksy tells each client the new time")
    parser.add_argument("--yes", action="store_true", help="Do not ask before each move")
    args = parser.parse_args()

    found = call("list_appointments", {"from": args.date, "to": args.date, "staff_id": args.staff_id})
    todo = [a for a in found["appointments"] if a["status"] in ("confirmed", "unconfirmed")]
    stuck = []
    for a in sorted(todo, key=lambda a: a["start"]):
        slot = best_slot(a, args.staff_id)
        if slot is None:
            stuck.append(a)
            continue
        print(f"{a['start'][11:16]} {a['client']} ({a['service']}) -> {slot['start'][11:16]} with {slot['staff']}")
        if args.apply and (args.yes or input("  Move? [y/N] ").strip().lower() == "y"):
            params = {
                "appointment_id": a["appointment_id"],
                "start": slot["start"],
                "staff_id": slot["staff_id"],
                "notify_client": args.notify,
            }
            moved = call("reschedule_appointment", params)
            print(f"  moved, {moved['status']}")
    for a in stuck:
        print(f"No colleague free: {a['start'][11:16]} {a['client']} ({a['service']})")


if __name__ == "__main__":
    run(main)
