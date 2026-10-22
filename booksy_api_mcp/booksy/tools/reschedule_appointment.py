"""Reschedule appointment: the details panel's Change, moved to a new start and optionally another staff member."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.calendar import (
    appointment_view,
    business_zone,
    int_id,
    local,
    ok_json,
    problem,
    read_appointment,
    request,
    stamp,
)
from booksy_api_mcp.booksy.tools.create_appointment import EXAMPLE_RESPONSE, unavailable
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "appointment_id": {"type": "string", "description": "Appointment ID from list_appointments."},
        "start": {
            "type": "string",
            "format": "date-time",
            "description": "New start, ISO 8601. Without a time zone it is the business's local time.",
        },
        "staff_id": {"type": "string", "description": "New staff member from list_staff. Default: unchanged."},
        "notify_client": {
            "type": "boolean",
            "description": "Tell the client about the new time through Booksy. Default: false.",
        },
    },
    "required": ["appointment_id", "start"],
    "additionalProperties": False,
}


def moved(appointment: dict[str, Any], start: datetime, staff: int | None) -> list[dict[str, Any]]:
    """The subbookings shifted together so the first starts at `start`; durations and gaps stay."""
    subs = appointment.get("subbookings") or []
    if not subs:
        raise ToolError("This appointment has no services to move.", ErrorCode.TARGET_ERROR)
    shift = start - datetime.fromisoformat(subs[0]["booked_from"])
    out: list[dict[str, Any]] = []
    for sub in subs:
        changed = {k: v for k, v in sub.items() if k != "_availability"}
        changed["booked_from"] = stamp(datetime.fromisoformat(sub["booked_from"]) + shift)
        changed["booked_till"] = stamp(datetime.fromisoformat(sub["booked_till"]) + shift)
        if staff is not None:
            changed["staffer_id"] = staff
            changed.pop("staffer", None)
        out.append(changed)
    return out


@tool(
    name="reschedule_appointment",
    title="Reschedule appointment",
    access="write",
    confirm=True,
    description="Move an appointment to a new start time, and optionally to another staff member.",
    details=(
        "Moves every service of the appointment by the same amount, so the first one starts at start. Booksy's dry "
        "run checks the new slot first and a busy one is refused. The client hears about it only with "
        "notify_client. Booksy refuses appointments it no longer lets you change (can in get_appointment)."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /appointments/{appointment_id}/reschedule",
    example_response=EXAMPLE_RESPONSE,
)
async def reschedule_appointment(ctx: ToolContext, args: dict[str, Any]) -> Any:
    zone = await business_zone(ctx)
    found = await read_appointment(ctx, args["appointment_id"])
    appointment = found.get("appointment") or {}
    if not (appointment.get("actions") or {}).get("change_time_or_note"):
        raise ToolError("Booksy no longer lets you change this appointment.", ErrorCode.TARGET_ERROR)
    staff = int_id(args["staff_id"], "staff_id") if args.get("staff_id") else None
    body = {
        **appointment,
        "subbookings": moved(appointment, local(args["start"], zone), staff),
        "overbooking": False,
        "_notification_enabled": False,
        "_notify_about_reschedule": bool(args.get("notify_client")),
        "_update_future_bookings": False,
        "_preserve_order": False,
    }
    uid = appointment["appointment_uid"]
    # The panel sends a change and its dry run with PUT (appointmentSave), POST answers 405.
    checked = await ok_json(ctx, "PUT", f"/appointments/{uid}/dry_run/", body=body)
    if (reason := unavailable(checked.get("appointment") or {})) is not None:
        raise ToolError(f"Booksy says the new slot is not available: {reason}", ErrorCode.TARGET_ERROR)
    response = await request(ctx, "PUT", f"/appointments/{uid}/", body=body)
    if response.status == 409:
        raise ToolError("The new slot is taken. Pick another one.", ErrorCode.TARGET_ERROR)
    if (text := problem(response)) is not None:
        raise ToolError(text, ErrorCode.TARGET_ERROR)
    saved = response.json()
    return {"saved": True, **appointment_view(saved.get("appointment") or {}, saved.get("customer"), zone)}
