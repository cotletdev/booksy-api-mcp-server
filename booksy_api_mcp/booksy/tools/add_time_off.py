"""Add time off: whole days as Shifts time off, hours as a calendar time reservation (block)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.calendar import (
    TIME_OFF_REASONS,
    business_zone,
    day,
    int_id,
    local,
    ok_json,
    problem,
    request,
    stamp,
    time_off_id,
)
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "staff_id": {"type": "string", "description": "Staff ID from list_staff."},
        "start": {
            "type": "string",
            "description": "A day (YYYY-MM-DD) for whole days off, or an ISO 8601 date-time to block hours.",
        },
        "end": {
            "type": "string",
            "description": "Last day off, inclusive (YYYY-MM-DD), or the end of the blocked hours on the same day.",
        },
        "reason": {
            "type": "string",
            "description": (
                "Whole days: vacation, sick_day, personal_day, training or other (other text is kept as a note). "
                "Hours: any label, e.g. Lunch."
            ),
        },
    },
    "required": ["staff_id", "start", "end"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "time_off_id": "off-49254738",
    "kind": "time_off",
    "staff_id": "882081",
    "start": "2026-10-27",
    "end": "2026-10-27",
    "reason": "vacation",
}


def _is_day(value: str) -> bool:
    return len(value.strip()) == 10


async def _days_off(ctx: ToolContext, staff: int, first: date, last: date, reason: str) -> dict[str, Any]:
    code = reason if reason in TIME_OFF_REASONS else "other"
    body = {
        "reason_code": code,
        "approved": True,
        "start_date": first.isoformat(),
        "end_date": last.isoformat(),
        "hour_from": None,
        "hour_till": None,
        "resource_ids": [staff],
        "all_day": True,
    }
    if code != reason:
        body["note"] = reason
    answer = await ok_json(ctx, "POST", "/shifts/resources/time_offs", body=body)
    if answer.get("failed") or answer.get("warnings"):
        warnings = answer.get("warnings") or []
        said = "; ".join(str(w.get("message") or w.get("description") or w) for w in warnings if w) or "it conflicts"
        raise ToolError(f"Booksy did not add the time off: {said}.", ErrorCode.TARGET_ERROR)
    created = _created(answer, staff, first, last, code)
    if created is None:
        week = first - timedelta(days=first.weekday())
        created = _created(
            await ok_json(ctx, "GET", "/shifts", params={"week_start_date": week.isoformat()}), staff, first, last, code
        )
    if created is None:
        raise ToolError("Booksy saved the time off but did not return it; see list_time_off.", ErrorCode.TARGET_ERROR)
    return {
        "time_off_id": time_off_id("time_off", created),
        "kind": "time_off",
        "staff_id": str(staff),
        "start": first.isoformat(),
        "end": last.isoformat(),
        "reason": reason or code,
    }


def _created(shifts: dict[str, Any], staff: int, first: date, last: date, code: str) -> int | None:
    """The newest matching time off of `staff` in a Shifts answer."""
    ids = [
        off["id"]
        for row in (shifts.get("schedule") or {}).get("resources") or []
        if (row.get("resource") or {}).get("id") == staff
        for entry in row.get("schedule") or []
        for off in entry.get("time_offs") or []
        if off.get("start_date") == first.isoformat()
        and off.get("end_date") == last.isoformat()
        and off.get("reason_code") == code
    ]
    return max(ids) if ids else None


async def _block(ctx: ToolContext, staff: int, start: datetime, end: datetime, reason: str) -> dict[str, Any]:
    body = {
        "reserved_from": stamp(start),
        "reserved_till": stamp(end),
        "resources": [staff],
        "reason": reason,
        "overbooking": False,
    }
    response = await request(ctx, "POST", "/reservations/", body=body)
    if response.status == 409:
        raise ToolError("Something is already booked in this time. Cancel or move it first.", ErrorCode.TARGET_ERROR)
    if (text := problem(response)) is not None:
        raise ToolError(text, ErrorCode.TARGET_ERROR)
    block = response.json().get("reservation") or {}
    zone = await business_zone(ctx)
    return {
        "time_off_id": time_off_id("block", block.get("id")),
        "kind": "block",
        "staff_id": str(staff),
        "start": datetime.fromisoformat(block.get("reserved_from") or stamp(start)).replace(tzinfo=zone).isoformat(),
        "end": datetime.fromisoformat(block.get("reserved_till") or stamp(end)).replace(tzinfo=zone).isoformat(),
        "reason": block.get("reason") or reason,
    }


@tool(
    name="add_time_off",
    title="Add time off",
    access="write",
    confirm=False,
    description="Block a staff member's calendar so no one can book it: whole days off or a few hours.",
    details=(
        "Two dates (YYYY-MM-DD) add whole days of time off, like Staff > Shifts. Two date-times on the same day "
        "block those hours in the calendar, like a time reservation. Booksy refuses a block over existing "
        "appointments. It reaches no client; remove_time_off takes it back."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /staffs/{staff_id}/time-offs",
    example_response=EXAMPLE_RESPONSE,
)
async def add_time_off(ctx: ToolContext, args: dict[str, Any]) -> Any:
    staff = int_id(args["staff_id"], "staff_id")
    reason = (args.get("reason") or "").strip()
    if _is_day(args["start"]) and _is_day(args["end"]):
        first, last = day(args["start"]), day(args["end"])
        if last < first:
            raise ToolError("end is before start.", ErrorCode.INVALID_INPUT)
        return await _days_off(ctx, staff, first, last, reason or "vacation")
    zone = await business_zone(ctx)
    start, end = local(args["start"], zone), local(args["end"], zone)
    if end <= start or start.date() != end.date():
        raise ToolError(
            "Hours must end after they start, on the same day. Use dates for whole days.", ErrorCode.INVALID_INPUT
        )
    return await _block(ctx, staff, start, end, reason)
