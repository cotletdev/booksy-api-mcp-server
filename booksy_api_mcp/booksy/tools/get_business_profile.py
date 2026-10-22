"""Get business profile: the business as clients see it on Booksy, plus its plan and booking policy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.engagement import business_api
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

# Booksy's business status (`~`, 21.10.2026): T trial; the others from the panel bundle's labels.
STATUS = {"T": "trial", "P": "paid", "B": "blocked", "S": "setup", "V": "verification"}
DAYS = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")


def _hours(business: dict[str, Any]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {d: [] for d in DAYS[1:] + DAYS[:1]}
    for day in business.get("business_opening_hours") or []:
        index = day.get("day_of_week")
        if isinstance(index, int) and 0 <= index < 7:
            found[DAYS[index]] = [f"{h['hour_from']}-{h['hour_till']}" for h in day.get("hours") or []]
    return found


def _lead(value: Any) -> str | None:
    """`{"months": 3}` as "3 months"."""
    if not isinstance(value, dict) or not value:
        return None
    return ", ".join(f"{n} {unit}" for unit, n in value.items())


@tool(
    name="get_business_profile",
    title="Get business profile",
    access="read",
    description="Your business's name, address, contact, opening hours, booking policy, rating and plan status.",
    details=(
        "Reads the business record behind your Booksy profile: name, address and time zone, phone, public "
        "email, website, description, weekly opening hours, how far ahead clients can book and change, review "
        "rating, whether the profile is visible in the Booksy marketplace, and the plan status with the trial "
        "end date."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /business",
    example_response={
        "business_id": 100001,
        "name": "Fade Factory",
        "category": "Barber shop",
        "address": "512 Elm Street, Austin, 78701",
        "time_zone": "America/Chicago",
        "phone": "+1 512 555 0142",
        "email": "hello@fadefactory.com",
        "website": "https://fadefactory.com",
        "description": "Cuts and shaves since 2014.",
        "opening_hours": {"mon": ["09:00-18:00"], "tue": ["09:00-18:00"], "sun": []},
        "booking": {
            "mode": "automatic",
            "policy": "Changes allowed up to 1 hours before visit",
            "min_lead_time": "30 minutes",
            "max_lead_time": "3 months",
            "change_until": "1 hours",
        },
        "rating": {"average": 4.9, "reviews": 128},
        "visible_in_marketplace": True,
        "profile_url": "https://cdl.booksy.com/J0LfoJ4mq7b",
        "staff_count": 3,
        "status": "paid",
        "trial_till": None,
    },
)
async def get_business_profile(ctx: ToolContext, args: dict[str, Any]) -> Any:
    b = (await business_api(ctx, "GET", "")).get("business") or {}
    loc = b.get("location") or {}
    parts = (loc.get("address"), loc.get("address2"), loc.get("city"), loc.get("zipcode"))
    address = ", ".join(str(p) for p in parts if p)
    return {
        "business_id": b.get("id"),
        "name": b.get("name"),
        "category": b.get("primary_category_internal_name"),
        "address": address or None,
        "time_zone": loc.get("time_zone_name") or b.get("timezone"),
        "phone": b.get("phone_with_prefix") or b.get("phone") or None,
        "email": b.get("public_email") or None,
        "website": b.get("website") or None,
        "description": b.get("description") or None,
        "opening_hours": _hours(b),
        "booking": {
            # booking_mode A = automatic confirmation, M = manual (the panel's booking settings).
            "mode": {"A": "automatic", "M": "manual"}.get(str(b.get("booking_mode")), b.get("booking_mode")),
            "policy": b.get("booking_policy") or None,
            "min_lead_time": _lead(b.get("booking_min_lead_time")),
            "max_lead_time": _lead(b.get("booking_max_lead_time")),
            "change_until": _lead(b.get("booking_max_modification_time")),
        },
        "rating": {"average": b.get("reviews_rank"), "reviews": b.get("reviews_count") or 0},
        "visible_in_marketplace": bool(b.get("is_visible_in_marketplace")),
        "profile_url": b.get("mp_deeplink"),
        "staff_count": b.get("active_staffers_count"),
        "status": STATUS.get(str(b.get("status")), b.get("status")),
        "trial_till": b.get("trial_till"),
    }
