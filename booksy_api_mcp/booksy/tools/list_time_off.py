"""List time off: Shifts time off and calendar blocks in a date range."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.calendar import business_zone, calendar, day, int_id, iso, staff_names, time_off_id
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "from": {"type": "string", "format": "date", "description": "First day, inclusive."},
        "to": {"type": "string", "format": "date", "description": "Last day, inclusive. At most 31 days after from."},
        "staff_id": {"type": "string", "description": "Only one staff member, from list_staff."},
    },
    "required": ["from", "to"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "time_off": [
        {
            "time_off_id": "off-49254738",
            "kind": "time_off",
            "staff_id": "882081",
            "staff": "Tom Baker",
            "start": "2026-10-27",
            "end": "2026-10-27",
            "hours": None,
            "reason": "Vacation",
        },
        {
            "time_off_id": "block-731496390",
            "kind": "block",
            "staff_id": "882081",
            "staff": "Tom Baker",
            "start": "2026-10-28T12:00:00+01:00",
            "end": "2026-10-28T13:00:00+01:00",
            "hours": None,
            "reason": "Lunch",
        },
    ]
}


@tool(
    name="list_time_off",
    title="List time off",
    access="read",
    confirm=False,
    description="Staff time off and blocked hours in a date range.",
    details=(
        "Lists time off from Shifts (kind time_off: dates, hours only when it is part of a day) and blocked hours "
        "in the calendar (kind block: date-times) between two days, 31 at most. time_off_id goes to remove_time_off."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /time-offs",
    example_response=EXAMPLE_RESPONSE,
)
async def list_time_off(ctx: ToolContext, args: dict[str, Any]) -> Any:
    zone = await business_zone(ctx)
    grid = await calendar(ctx, day(args["from"]), day(args["to"]))
    names = staff_names(grid)
    only = int_id(args["staff_id"], "staff_id") if args.get("staff_id") else None
    found: dict[str, dict[str, Any]] = {}
    for resource in grid.get("resources") or []:
        staff = resource.get("id")
        if only is not None and staff != only:
            continue
        for offs in (resource.get("time_offs") or {}).values():
            for off in offs or []:
                key = time_off_id("time_off", off.get("id"))
                found.setdefault(
                    key,
                    {
                        "time_off_id": key,
                        "kind": "time_off",
                        "staff_id": str(staff),
                        "staff": names.get(staff, ""),
                        "start": off.get("start_date"),
                        "end": off.get("end_date"),
                        "hours": None if off.get("all_day") else f"{off.get('hour_from')}-{off.get('hour_till')}",
                        "reason": off.get("note") or off.get("reason") or off.get("reason_code") or "",
                    },
                )
        for ids in (resource.get("reservations") or {}).values():
            for block_id in ids or []:
                block = (grid.get("reservations") or {}).get(str(block_id)) or {}
                key = time_off_id("block", block_id)
                found.setdefault(
                    key,
                    {
                        "time_off_id": key,
                        "kind": "block",
                        "staff_id": str(staff),
                        "staff": names.get(staff, ""),
                        "start": iso(block.get("reserved_from"), zone),
                        "end": iso(block.get("reserved_till"), zone),
                        "hours": None,
                        "reason": block.get("reason") or block.get("business_note") or "",
                    },
                )
    return {"time_off": sorted(found.values(), key=lambda t: t["start"] or "")}
