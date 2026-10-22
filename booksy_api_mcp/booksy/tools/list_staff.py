"""List staff: staff members with their week's working hours and the services they do."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.clients import api, ranges
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "week_start_date": {
            "type": "string",
            "format": "date",
            "description": "Any day of the week to show hours for, YYYY-MM-DD. Default: this week.",
        },
    },
    "required": [],
    "additionalProperties": False,
}

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@tool(
    name="list_staff",
    title="List staff",
    access="read",
    confirm=False,
    description="Staff members with their working hours for a week and the services they offer.",
    details=(
        "Reads the staff of the business: name, position, email, phone, access level, whether clients see "
        "them, the services each one performs, and working hours for each day of one week (Monday to Sunday, "
        "from Shifts, time off included). Use staff_id in other tools."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /staff",
    example_response={
        "week_start_date": "2026-10-19",
        "staff": [
            {
                "staff_id": 882081,
                "name": "Tom Baker",
                "position": "",
                "email": "owner@example.com",
                "phone": None,
                "access_level": "owner",
                "visible": True,
                "services": ["Men's haircut", "Beard trim"],
                "hours": {"mon": ["10:00-19:00"], "tue": ["10:00-19:00"], "sat": [], "sun": []},
                "time_off": [{"date": "2026-10-24", "reason": "vacation", "hours": []}],
            }
        ],
    },
)
async def list_staff(ctx: ToolContext, args: dict[str, Any]) -> Any:
    day = date.fromisoformat(args["week_start_date"]) if args.get("week_start_date") else datetime.now(UTC).date()
    monday = day - timedelta(days=day.weekday())
    resources = await api(ctx, "GET", "/resources")
    services = await api(ctx, "GET", "/services")
    shifts = await api(ctx, "GET", "/shifts", params={"week_start_date": monday.isoformat()})
    offered: dict[int, list[str]] = {}
    for service in services.get("services") or []:
        staff = {s for v in service.get("variants") or [] for s in v.get("staffers") or []}
        for staff_id in staff:
            offered.setdefault(staff_id, []).append(service.get("name") or "")
    schedules = {
        (row.get("resource") or {}).get("id"): row.get("schedule") or []
        for row in ((shifts.get("schedule") or {}).get("resources") or [])
    }
    out = []
    for r in resources.get("resources") or []:
        if r.get("type") != "S":
            continue
        hours: dict[str, list[str]] = {}
        time_off: list[dict[str, Any]] = []
        for entry in schedules.get(r.get("id"), []):
            weekday = DAYS[date.fromisoformat(entry["date"]).weekday()]
            hours[weekday] = ranges(entry.get("working_hours"))
            time_off.extend(
                {
                    "date": entry["date"],
                    "reason": off.get("reason_code") or off.get("reason"),
                    "hours": ranges([off]) if not off.get("all_day") else [],
                }
                for off in entry.get("time_offs") or []
            )
        out.append(
            {
                "staff_id": r.get("id"),
                "name": r.get("name"),
                "position": r.get("position") or "",
                "email": r.get("staff_email") or None,
                "phone": r.get("staff_cell_phone_with_prefix") or r.get("staff_cell_phone") or None,
                "access_level": r.get("staff_access_level"),
                "visible": bool(r.get("visible")),
                "services": offered.get(r.get("id"), []),
                "hours": hours,
                "time_off": time_off,
            }
        )
    return {"week_start_date": monday.isoformat(), "staff": out}
