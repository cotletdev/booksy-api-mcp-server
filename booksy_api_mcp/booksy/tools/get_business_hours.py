"""Get business hours: the weekly opening hours of the business and its time zone."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.clients import WEEKDAYS, api, ranges
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


@tool(
    name="get_business_hours",
    title="Get business hours",
    access="read",
    confirm=False,
    description="Weekly opening hours, time zone and booking lead times of the business.",
    details=(
        "Reads the opening hours set in Business details: open ranges for each day (an empty list is "
        "closed), the note shown with them, the business's time zone and address, and how early and how late "
        "clients may book or change a visit."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /business-hours",
    example_response={
        "business_id": 100001,
        "name": "Fade Factory",
        "time_zone": "Europe/Warsaw",
        "address": "Main St 1, Springfield",
        "hours": {"mon": ["10:00-19:00"], "tue": ["10:00-19:00"], "sat": [], "sun": []},
        "note": "",
        "booking_min_lead_time": {"minutes": 30},
        "booking_max_lead_time": {"months": 3},
        "booking_max_modification_time": {"hours": 1},
    },
)
async def get_business_hours(ctx: ToolContext, args: dict[str, Any]) -> Any:
    business = (await api(ctx, "GET", "")).get("business") or {}
    days = business.get("business_opening_hours")
    hours: dict[str, list[str]] = {}
    if days:
        for day in sorted(days, key=lambda d: (d.get("day_of_week", 0) + 6) % 7):
            hours[WEEKDAYS[day["day_of_week"]]] = ranges(day.get("hours"))
    else:
        hours = {name: [] for name in (*WEEKDAYS[1:], WEEKDAYS[0])}
        for slot in business.get("open_hours") or []:
            hours[WEEKDAYS[slot["day_of_week"]]] += ranges([slot])
    location = business.get("location") or {}
    address = ", ".join(p for p in (location.get("address"), location.get("zipcode"), location.get("city")) if p)
    return {
        "business_id": business.get("id"),
        "name": business.get("name"),
        "time_zone": location.get("time_zone_name"),
        "address": address,
        "hours": hours,
        "note": business.get("opening_hours_note") or "",
        "booking_min_lead_time": business.get("booking_min_lead_time"),
        "booking_max_lead_time": business.get("booking_max_lead_time"),
        "booking_max_modification_time": business.get("booking_max_modification_time"),
    }
