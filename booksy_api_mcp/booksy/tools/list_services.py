"""List services: the service menu with variants, prices, durations and the staff who do each."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.clients import api
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

# Variant `type`: how the price shows on the profile.
PRICE_TYPES = {"X": "fixed", "S": "starts_at", "V": "varies", "F": "free", "D": "hidden"}


def _price(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@tool(
    name="list_services",
    title="List services",
    access="read",
    confirm=False,
    description="Your service menu with category, variants, duration, price and the staff who offer each.",
    details=(
        "Reads the services of the business: name, category, description, whether clients can book it online, "
        "and its variants with duration in minutes, price (number and as shown, with currency), price type "
        "and the staff IDs who perform it. create_appointment and find_open_slots take service_id (its first "
        "variant) or a variant_id for another variant."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /services",
    example_response={
        "services": [
            {
                "service_id": 8307205,
                "name": "Men's haircut",
                "category": "Hair",
                "description": "",
                "bookable_online": True,
                "duration_minutes": 30,
                "price": 60.0,
                "price_label": "60,00 zł",
                "staff_ids": [882081],
                "variants": [
                    {
                        "variant_id": 23187741,
                        "label": "",
                        "duration_minutes": 30,
                        "price": 60.0,
                        "price_label": "60,00 zł",
                        "price_type": "fixed",
                        "staff_ids": [882081],
                    }
                ],
            }
        ]
    },
)
async def list_services(ctx: ToolContext, args: dict[str, Any]) -> Any:
    found = await api(ctx, "GET", "/services")
    categories = await api(ctx, "GET", "/service_categories")
    names = {
        c.get("id"): c.get("name") for c in categories.get("categories") or categories.get("service_categories") or []
    }
    out = []
    for service in found.get("services") or []:
        variants = [
            {
                "variant_id": v.get("id"),
                "label": v.get("label") or "",
                "duration_minutes": v.get("duration"),
                "price": _price(v.get("price")),
                "price_label": v.get("service_price") or "",
                "price_type": PRICE_TYPES.get(v.get("type") or "", v.get("type")),
                "staff_ids": v.get("staffers") or [],
            }
            for v in service.get("variants") or []
        ]
        first = variants[0] if variants else {}
        out.append(
            {
                "service_id": service.get("id"),
                "name": service.get("name"),
                "category": names.get(service.get("service_category_id")),
                "description": service.get("description") or "",
                "bookable_online": bool(service.get("is_available_for_customer_booking")),
                "duration_minutes": first.get("duration_minutes"),
                "price": first.get("price"),
                "price_label": service.get("service_price") or first.get("price_label") or "",
                "staff_ids": sorted({s for v in variants for s in v["staff_ids"]}),
                "variants": variants,
            }
        )
    return {"services": out}
