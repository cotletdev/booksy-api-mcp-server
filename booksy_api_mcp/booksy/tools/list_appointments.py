"""List appointments: the calendar grid for a date range, one row per appointment."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.calendar import business_zone, calendar, day, int_id, iso, staff_names, status_name
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
    "appointments": [
        {
            "appointment_id": "785472840",
            "client": "Anna Novak",
            "client_id": "132355750",
            "service": "Haircut",
            "staff": "Tom Baker",
            "staff_id": "882081",
            "start": "2026-10-29T11:00:00+01:00",
            "end": "2026-10-29T11:30:00+01:00",
            "status": "confirmed",
        }
    ]
}


@tool(
    name="list_appointments",
    title="List appointments",
    access="read",
    confirm=False,
    description="Appointments in a date range with client, service, staff, time and status.",
    details=(
        "Lists the Booksy calendar between two days (31 at most), in start order, including unconfirmed requests. "
        "Times carry the business's time zone. A walk-in has an empty client. An appointment with several "
        "services is one row listing them all; get_appointment returns prices and notes."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /appointments",
    example_response=EXAMPLE_RESPONSE,
)
async def list_appointments(ctx: ToolContext, args: dict[str, Any]) -> Any:
    zone = await business_zone(ctx)
    grid = await calendar(ctx, day(args["from"]), day(args["to"]))
    names = staff_names(grid)
    only = int_id(args["staff_id"], "staff_id") if args.get("staff_id") else None
    rows: dict[str, dict[str, Any]] = {}
    for booking in sorted((grid.get("bookings") or {}).values(), key=lambda b: b.get("booked_from") or ""):
        staff = [r.get("id") for r in booking.get("resources") or [] if r.get("id") in names]
        uid = str(booking.get("appointment_uid") or booking.get("id"))
        customer = booking.get("customer") or {}
        row = rows.get(uid)
        service = (booking.get("service") or {}).get("name") or ""
        if row is None:
            rows[uid] = {
                "appointment_id": uid,
                "client": customer.get("name") or "",
                "client_id": str(customer.get("id") or ""),
                "service": service,
                "staff": ", ".join(names[s] for s in staff),
                "staff_id": ",".join(str(s) for s in staff),
                "start": iso(booking.get("booked_from"), zone),
                "end": iso(booking.get("booked_till"), zone),
                "status": status_name(booking.get("status")),
                "_staff": set(staff),
            }
            continue
        row["service"] = f"{row['service']}, {service}" if service else row["service"]
        row["end"] = max(row["end"] or "", iso(booking.get("booked_till"), zone) or "")
        for s in staff:
            if s not in row["_staff"]:
                row["_staff"].add(s)
                row["staff"] = ", ".join(filter(None, [row["staff"], names[s]]))
                row["staff_id"] = ",".join(filter(None, [row["staff_id"], str(s)]))
    found = [r for r in rows.values() if only is None or only in r["_staff"]]
    for row in found:
        del row["_staff"]
    return {"appointments": found}
