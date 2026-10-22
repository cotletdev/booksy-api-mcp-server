"""Find open slots: free start times for one service on one day.

The business panel has no slots endpoint. Candidates come from the calendar grid (working hours
minus bookings, blocks and time off, stepped by the variant's time_slot_interval) and each one returned is checked
with Booksy's own appointments/dry_run/.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.calendar import business_zone, calendar, day, int_id, ok_json, service_variant, stamp
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.helpers import limit
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "service_id": {
            "type": "string",
            "description": "service_id from list_services (its first variant), or a variant_id.",
        },
        "date": {"type": "string", "format": "date", "description": "Day to check."},
        "staff_id": {
            "type": "string",
            "description": "Only this staff member. Default: anyone who offers the service.",
        },
        "limit": {"type": "integer", "description": "1 to 30 slots, earliest first. Default: 12."},
    },
    "required": ["service_id", "date"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "date": "2026-10-29",
    "service_id": "8307205",
    "service": "Haircut",
    "duration_minutes": 30,
    "slots": [
        {
            "start": "2026-10-29T10:00:00+01:00",
            "end": "2026-10-29T10:30:00+01:00",
            "staff_id": "882081",
            "staff": "Tom Baker",
        },
        {
            "start": "2026-10-29T10:15:00+01:00",
            "end": "2026-10-29T10:45:00+01:00",
            "staff_id": "882081",
            "staff": "Tom Baker",
        },
    ],
}

# Statuses that no longer hold their time (cancelled, declined, rejected).
_FREED = {"C", "D", "R"}
_CHECKS_AT_ONCE = 4

Span = tuple[datetime, datetime]


def _at(on: date, hour: str) -> datetime:
    return datetime.combine(on, time.fromisoformat(hour if hour != "24:00" else "23:59"))


def busy_spans(grid: dict[str, Any], resource: dict[str, Any], on: date) -> list[Span]:
    """Bookings, blocks and time off of one staff member on one day."""
    key = on.isoformat()
    spans: list[Span] = []
    for booking_id in (resource.get("bookings") or {}).get(key) or []:
        booking = (grid.get("bookings") or {}).get(str(booking_id)) or {}
        if booking.get("booked_from") and booking.get("status") not in _FREED:
            spans.append(
                (datetime.fromisoformat(booking["booked_from"]), datetime.fromisoformat(booking["booked_till"]))
            )
    for block_id in (resource.get("reservations") or {}).get(key) or []:
        block = (grid.get("reservations") or {}).get(str(block_id)) or {}
        if block.get("reserved_from"):
            spans.append(
                (datetime.fromisoformat(block["reserved_from"]), datetime.fromisoformat(block["reserved_till"]))
            )
    for off in (resource.get("time_offs") or {}).get(key) or []:
        if off.get("all_day") or not off.get("hour_from"):
            spans.append((_at(on, "00:00"), _at(on, "23:59")))
        else:
            spans.append((_at(on, off["hour_from"]), _at(on, off["hour_till"])))
    return spans


def candidates(
    grid: dict[str, Any], resource: dict[str, Any], on: date, minutes: int, step: int, now: datetime
) -> list[Span]:
    busy = busy_spans(grid, resource, on)
    length = timedelta(minutes=minutes)
    found: list[Span] = []
    for hours in (resource.get("working_hours") or {}).get(on.isoformat()) or []:
        start, end = _at(on, hours["hour_from"]), _at(on, hours["hour_till"])
        moment = start
        while moment + length <= end:
            slot = (moment, moment + length)
            if moment >= now and not any(slot[0] < b[1] and b[0] < slot[1] for b in busy):
                found.append(slot)
            moment += timedelta(minutes=step)
    return found


async def confirmed(ctx: ToolContext, variant_id: int, staff: int, slot: Span, gate: asyncio.Semaphore) -> bool:
    """Booksy's dry run says this staff member can take this slot."""
    body = {
        "customer": {"mode": "walk-in"},
        "subbookings": [
            {
                "booked_from": stamp(slot[0]),
                "booked_till": stamp(slot[1]),
                "service_variant": {"id": variant_id, "mode": "variant"},
                "staffer_id": staff,
                "appliance_id": None,
                "autoassign": False,
                "addons": [],
            }
        ],
        "overbooking": False,
        "_notification_enabled": False,
    }
    async with gate:
        try:
            answer = await ok_json(ctx, "POST", "/appointments/dry_run/", body=body)
        except ToolError:
            return False
    for sub in (answer.get("appointment") or {}).get("subbookings") or []:
        found = ((sub.get("_availability") or {}).get("staffers") or {}).get(str(staff))
        if found is not None and not found.get("ok"):
            return False
    return True


def _iso(moment: datetime, zone: ZoneInfo) -> str:
    return moment.replace(tzinfo=zone).isoformat()


@tool(
    name="find_open_slots",
    title="Find open slots",
    access="read",
    confirm=False,
    description="Free start times for a service on one day, from working hours, bookings, blocks and time off.",
    details=(
        "Returns free start times for one service on one day, earliest first, for each staff member who offers it "
        "(or only staff_id). Starts follow the service's time slot interval and leave room for its duration; past "
        "times are left out. Booksy's own booking check confirms every slot returned. Pass start and staff_id to "
        "create_appointment."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /services/{service_id}/open-slots",
    example_response=EXAMPLE_RESPONSE,
    timeout_s=90,
)
async def find_open_slots(ctx: ToolContext, args: dict[str, Any]) -> Any:
    zone = await business_zone(ctx)
    service, variant = await service_variant(ctx, args["service_id"])
    offered = [int(s) for s in variant.get("staffers") or service.get("resources") or []]
    if args.get("staff_id"):
        only = int_id(args["staff_id"], "staff_id")
        if only not in offered:
            raise ToolError("This staff member does not offer the service.", ErrorCode.INVALID_INPUT)
        offered = [only]
    on = day(args["date"])
    grid = await calendar(ctx, on, on)
    local_now = grid.get("business_local_time")
    now = datetime.fromisoformat(local_now) if local_now else datetime.now(zone).replace(tzinfo=None)
    minutes = int(variant.get("duration") or 0)
    step = int(variant.get("time_slot_interval") or 15)
    found: list[tuple[datetime, int, str, Span]] = []
    for resource in grid.get("resources") or []:
        if resource.get("id") in offered:
            name = resource.get("name") or ""
            found.extend((s[0], resource["id"], name, s) for s in candidates(grid, resource, on, minutes, step, now))
    found.sort(key=lambda f: (f[0], f[1]))
    wanted = limit(args, 12, 30)
    gate = asyncio.Semaphore(_CHECKS_AT_ONCE)
    slots: list[dict[str, Any]] = []
    # Check a little more than asked, so a refused candidate does not shorten the answer.
    for batch_start in range(0, len(found), wanted + 4):
        batch = found[batch_start : batch_start + wanted + 4]
        checks = await asyncio.gather(
            *(confirmed(ctx, variant["id"], staff, slot, gate) for _, staff, _, slot in batch)
        )
        for (_, staff, name, slot), ok in zip(batch, checks, strict=True):
            if ok and len(slots) < wanted:
                slots.append(
                    {"start": _iso(slot[0], zone), "end": _iso(slot[1], zone), "staff_id": str(staff), "staff": name}
                )
        if len(slots) >= wanted:
            break
    return {
        "date": on.isoformat(),
        "service_id": str(service.get("id")),
        "service": service.get("name") or "",
        "duration_minutes": minutes,
        "slots": slots,
    }
