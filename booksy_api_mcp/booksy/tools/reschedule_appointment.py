"""Reschedule appointment: the details panel's Change: a new start, another staff member or other services."""

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
from booksy_api_mcp.booksy.tools.create_appointment import EXAMPLE_RESPONSE, SERVICES_SCHEMA, segments, unavailable
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
            "description": "New start, ISO 8601. Without a time zone it is the business's local time. "
            "Default: unchanged.",
        },
        "staff_id": {
            "type": "string",
            "description": "New staff member for every service, from list_staff. Default: unchanged.",
        },
        "services": {
            **SERVICES_SCHEMA,
            "description": "Replaces the services: the full new list in order, back to back from start. Leave "
            "a service out to remove it, add one to add it. Default: unchanged.",
        },
        "notify_client": {
            "type": "boolean",
            "description": "Tell the client about the new time through Booksy. Default: false.",
        },
    },
    "required": ["appointment_id"],
    "additionalProperties": False,
}


def replaced(appointment: dict[str, Any], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The new services' subbookings; one in the same place with the same variant keeps its id and fields."""
    old = appointment.get("subbookings") or []
    out: list[dict[str, Any]] = []
    for i, sub in enumerate(new):
        kept = old[i] if i < len(old) else {}
        if (kept.get("service_variant") or {}).get("id") == sub["service_variant"]["id"]:
            same = {k: v for k, v in kept.items() if k not in ("_availability", "staffer")}
            out.append({**same, **{k: sub[k] for k in ("booked_from", "booked_till", "staffer_id")}})
        else:
            out.append(sub)
    return out


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
    description="Change an appointment: a new start time, another staff member, or other services.",
    details=(
        "Without services, moves every service of the appointment by the same amount, so the first one starts at "
        "start. With services, the list replaces the appointment's services, each with its own staff member, back "
        "to back from start (default: the current start). Booksy's dry run checks the new slots first and a busy "
        "one is refused. The client hears about it only with notify_client. Booksy refuses appointments it no "
        "longer lets you change (can in get_appointment)."
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
    if not (args.get("start") or staff or args.get("services")):
        raise ToolError("Give start, staff_id or services to change.", ErrorCode.INVALID_INPUT)
    subs = appointment.get("subbookings") or []
    if not subs:
        raise ToolError("This appointment has no services to change.", ErrorCode.TARGET_ERROR)
    start = local(args["start"], zone) if args.get("start") else datetime.fromisoformat(subs[0]["booked_from"])
    if args.get("services"):
        if staff is not None:
            raise ToolError("With services, give staff_id inside each service.", ErrorCode.INVALID_INPUT)
        subbookings = replaced(appointment, await segments(ctx, args["services"], start))
    else:
        subbookings = moved(appointment, start, staff)
    body = {
        **appointment,
        "subbookings": subbookings,
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
