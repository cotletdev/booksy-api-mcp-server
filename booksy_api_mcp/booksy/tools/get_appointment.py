"""Get appointment: one appointment as the calendar's details panel shows it."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.calendar import appointment_view, business_zone, read_appointment
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"appointment_id": {"type": "string", "description": "Appointment ID from list_appointments."}},
    "required": ["appointment_id"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "appointment_id": "785472840",
    "status": "confirmed",
    "client": {"client_id": "132355750", "name": "Anna Novak"},
    "services": [
        {
            "service_id": "8307205",
            "name": "Haircut",
            "price": 60.0,
            "duration_minutes": 30,
            "staff_id": "882081",
            "staff": "Tom Baker",
            "start": "2026-10-29T11:00:00+01:00",
            "end": "2026-10-29T11:30:00+01:00",
        }
    ],
    "staff": "Tom Baker",
    "start": "2026-10-29T11:00:00+01:00",
    "end": "2026-10-29T11:30:00+01:00",
    "total": 60.0,
    "total_text": "60,00 zł",
    "note": "Prefers a scissor cut",
    "client_note": "",
    "can": ["cancel", "change", "change_time_or_note"],
}


@tool(
    name="get_appointment",
    title="Get appointment",
    access="read",
    confirm=False,
    description="One appointment: services, staff, times, price, client and notes.",
    details=(
        "Returns one appointment with each service's staff member, times and price, the client, the total and the "
        "notes. note is the internal note only staff see; client_note is the note shown to the client. can lists "
        "what Booksy allows now (cancel, change, confirm, decline, no_show)."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /appointments/{appointment_id}",
    example_response=EXAMPLE_RESPONSE,
)
async def get_appointment(ctx: ToolContext, args: dict[str, Any]) -> Any:
    zone = await business_zone(ctx)
    found = await read_appointment(ctx, args["appointment_id"])
    return appointment_view(found.get("appointment") or {}, found.get("customer"), zone)
