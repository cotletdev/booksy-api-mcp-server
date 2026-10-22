#!/usr/bin/env python3
"""Block time off in the Booksy calendar: whole days off, or a few hours on one day.

    python block_time_off.py --staff-id 882081 --start 2026-11-02 --end 2026-11-06 --reason vacation
    python block_time_off.py --staff-id 882081 --start 2026-11-02T13:00 --end 2026-11-02T14:00 --reason Lunch
    python block_time_off.py --staff-id 882081 --remove off-731676884

Booksy refuses a block over appointments still in the calendar: move them first (reschedule_day.py).
"""

import argparse
import json

from booksy_api_mcp.scripting import call, run


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--staff-id", required=True, help="From list_staff")
    parser.add_argument("--start", help="YYYY-MM-DD for days off, or YYYY-MM-DDTHH:MM for hours")
    parser.add_argument("--end", help="Last day off (inclusive), or the end time on the same day")
    parser.add_argument("--reason", help="vacation, sick_day, personal_day, training, other, or a label for hours")
    parser.add_argument("--remove", metavar="TIME_OFF_ID", help="Remove this time off instead (off-... or block-...)")
    args = parser.parse_args()

    if args.remove:
        result = call("remove_time_off", {"staff_id": args.staff_id, "time_off_id": args.remove})
    else:
        if not (args.start and args.end):
            parser.error("--start and --end are required")
        params = {"staff_id": args.staff_id, "start": args.start, "end": args.end, "reason": args.reason}
        result = call("add_time_off", params)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run(main)
