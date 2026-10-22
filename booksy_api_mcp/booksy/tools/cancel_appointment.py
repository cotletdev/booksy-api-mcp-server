"""Cancel appointment: the details panel's Cancel."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.calendar import appointment_view, business_zone, ok_json, read_appointment
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "appointment_id": {"type": "string", "description": "Appointment ID from list_appointments."},
        "reason": {"type": "string", "description": "Why it is cancelled; saved as the appointment's note."},
        "notify_client": {
            "type": "boolean",
            "description": "Tell the client by email and SMS through Booksy. Default: false.",
        },
    },
    "required": ["appointment_id"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "appointment_id": "785472840",
    "status": "cancelled",
    "client": {"client_id": "132355750", "name": "Anna Novak"},
    "start": "2026-10-29T11:00:00+01:00",
    "end": "2026-10-29T11:30:00+01:00",
}


@tool(
    name="cancel_appointment",
    title="Cancel appointment",
    access="write",
    confirm=True,
    description="Cancel an appointment and free its time in the calendar.",
    details=(
        "Cancels one appointment as the business. The client is told only with notify_client. A deposit, if any, "
        "follows the business's deposit settings. Booksy refuses appointments it no longer lets you cancel "
        "(can in get_appointment). There is no undo; book again with create_appointment."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /appointments/{appointment_id}/cancel",
    example_response=EXAMPLE_RESPONSE,
)
async def cancel_appointment(ctx: ToolContext, args: dict[str, Any]) -> Any:
    zone = await business_zone(ctx)
    found = await read_appointment(ctx, args["appointment_id"])
    appointment = found.get("appointment") or {}
    if not (appointment.get("actions") or {}).get("cancel"):
        raise ToolError("Booksy does not let you cancel this appointment now.", ErrorCode.TARGET_ERROR)
    notify = bool(args.get("notify_client"))
    body = {
        "action": "cancel",
        "_version": appointment.get("_version"),
        "business_note": args.get("reason") or "",
        "_notify_about_cancel_email": notify,
        "_notify_about_cancel_sms": notify,
        "_update_future_bookings": False,
    }
    saved = await ok_json(ctx, "POST", f"/appointments/{appointment['appointment_uid']}/action", body=body)
    view = appointment_view(
        saved.get("appointment") or appointment, saved.get("customer") or found.get("customer"), zone
    )
    if not saved.get("appointment"):
        view["status"] = "cancelled"
    return {k: view[k] for k in ("appointment_id", "status", "client", "start", "end")}
