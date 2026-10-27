"""Create appointment: the calendar's New appointment, checked with Booksy's dry run before saving."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.calendar import (
    appointment_view,
    business_zone,
    int_id,
    local,
    ok_json,
    problem,
    request,
    service_variant,
    stamp,
)
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

# Several services in one appointment, each with its own staff member, booked back to back (Booksy's subbookings).
SERVICES_SCHEMA: dict[str, Any] = {
    "type": "array",
    "minItems": 1,
    "maxItems": 10,
    "description": "Services of the appointment in order, each starting when the one before ends.",
    "items": {
        "type": "object",
        "properties": {
            "service_id": {"type": "string", "description": "service_id or variant_id from list_services."},
            "staff_id": {
                "type": "string",
                "description": "Staff ID from list_staff. Default: the first one who offers the service.",
            },
        },
        "required": ["service_id"],
        "additionalProperties": False,
    },
}

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "client_id": {"type": "string", "description": "Client ID from list_clients or add_client."},
        "service_id": {
            "type": "string",
            "description": "service_id from list_services (its first variant), or a variant_id. Or use services.",
        },
        "services": SERVICES_SCHEMA,
        "start": {
            "type": "string",
            "format": "date-time",
            "description": "ISO 8601. Without a time zone it is the business's local time.",
        },
        "staff_id": {
            "type": "string",
            "description": "Staff ID from list_staff, with service_id. Default: the first one who offers the service.",
        },
        "note": {"type": "string", "description": "Internal note, only staff see it."},
        "notify_client": {
            "type": "boolean",
            "description": "Send Booksy's booking confirmation to the client. Default: false.",
        },
        "dry_run": {
            "type": "boolean",
            "description": "Only check the time and price; nothing is saved. Default: false.",
        },
    },
    "required": ["client_id", "start"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "saved": True,
    "appointment_id": "785472311",
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


def wanted_services(args: dict[str, Any]) -> list[dict[str, Any]]:
    """`services`, or the single `service_id` with `staff_id`; exactly one of the two."""
    if bool(args.get("services")) == bool(args.get("service_id")):
        raise ToolError("Give either service_id or services.", ErrorCode.INVALID_INPUT)
    if args.get("services"):
        if args.get("staff_id"):
            raise ToolError("With services, give staff_id inside each service.", ErrorCode.INVALID_INPUT)
        return list(args["services"])
    return [{"service_id": args["service_id"], "staff_id": args.get("staff_id")}]


async def segments(ctx: ToolContext, services: list[dict[str, Any]], start: datetime) -> list[dict[str, Any]]:
    """New subbookings for `services`, back to back from `start`, as the panel sends them."""
    out: list[dict[str, Any]] = []
    for item in services:
        service, variant = await service_variant(ctx, item["service_id"])
        staffers = variant.get("staffers") or service.get("resources") or []
        staff = int_id(item["staff_id"], "staff_id") if item.get("staff_id") else (staffers[0] if staffers else None)
        if staff is None:
            raise ToolError(f"No staff member offers {service.get('name') or 'this service'}.", ErrorCode.INVALID_INPUT)
        end = start + timedelta(minutes=int(variant.get("duration") or 0))
        out.append(
            {
                "booked_from": stamp(start),
                "booked_till": stamp(end),
                "service_variant": {"id": variant["id"], "mode": "variant"},
                "staffer_id": staff,
                "appliance_id": None,
                "autoassign": False,
                "addons": [],
            }
        )
        start = end
    return out


async def booking(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """The body the panel sends for a new appointment."""
    zone = await business_zone(ctx)
    return {
        "customer": {"mode": "customer-card", "id": int_id(args["client_id"], "client_id")},
        "subbookings": await segments(ctx, wanted_services(args), local(args["start"], zone)),
        "business_note": "",
        "business_secret_note": args.get("note") or "",
        "overbooking": False,
        "_notification_enabled": bool(args.get("notify_client")),
        "_notify_about_reschedule": False,
        "_preserve_order": False,
    }


def unavailable(appointment: dict[str, Any]) -> str | None:
    """Booksy's reason a chosen staff member cannot take their slot, from the dry run."""
    for sub in appointment.get("subbookings") or []:
        staffers = (sub.get("_availability") or {}).get("staffers") or {}
        found = staffers.get(str(sub.get("staffer_id")))
        if found and not found.get("ok"):
            return found.get("message") or "The staff member is not free at this time."
    return None


@tool(
    name="create_appointment",
    title="Create appointment",
    access="write",
    confirm=True,
    description="Book a client for one or more services at a start time; Booksy checks the slots first.",
    details=(
        "Books one client card for service_id, or for several services in one appointment, each with its own "
        "staff member, back to back from start. Each end follows the service's duration. Booksy's dry run checks "
        "every staff member is free first; a busy slot is refused, never double-booked. The client gets Booksy's "
        "confirmation only with notify_client. dry_run returns the same answer with saved false and keeps nothing."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /clients/{client_id}/appointments",
    example_response=EXAMPLE_RESPONSE,
)
async def create_appointment(ctx: ToolContext, args: dict[str, Any]) -> Any:
    body = await booking(ctx, args)
    zone = await business_zone(ctx)
    checked = await ok_json(ctx, "POST", "/appointments/dry_run/", body=body)
    if (reason := unavailable(checked.get("appointment") or {})) is not None:
        raise ToolError(f"Booksy says the slot is not available: {reason}", ErrorCode.TARGET_ERROR)
    if args.get("dry_run"):
        return {"saved": False, **appointment_view(checked.get("appointment") or {}, checked.get("customer"), zone)}
    response = await request(ctx, "POST", "/appointments/", body=body)
    if response.status == 409:
        raise ToolError("The slot was taken in the meantime. Pick another one.", ErrorCode.TARGET_ERROR)
    if (text := problem(response)) is not None:
        raise ToolError(text, ErrorCode.TARGET_ERROR)
    saved = response.json()
    return {"saved": True, **appointment_view(saved.get("appointment") or {}, saved.get("customer"), zone)}
