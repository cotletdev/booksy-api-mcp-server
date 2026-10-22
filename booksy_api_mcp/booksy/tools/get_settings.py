"""Get settings: text message plan, client message channels and the owner's notification settings."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.engagement import business_api
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

# Notification channel letters (`notifications/`, 21.10.2026): E email, P push; S sms by the same scheme.
CHANNEL = {"E": "email", "P": "push", "S": "sms"}


@tool(
    name="get_settings",
    title="Get settings",
    access="read",
    description="Text message allowance and usage, client message channels and your notification settings.",
    details=(
        "Reads the settings an agent needs before messaging clients: whether SMS and email to clients are on, the "
        "free and paid text allowance with this period's usage and price per text part, and which booking "
        "events notify you by email or push. Changes stay in the Booksy app."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /settings",
    example_response={
        "sms": {
            "enabled": True,
            "email_enabled": True,
            "period": "2026-10",
            "free_limit": 2000,
            "free_used": 640,
            "paid_limit": 16000,
            "paid_used": 0,
            "price_per_part": 0.02,
            "cost_due": "$0.00",
        },
        "notifications": [
            {"code": "biz_booking_status_change", "name": "Booking status changes", "channels": ["email", "push"]}
        ],
    },
)
async def get_settings(ctx: ToolContext, args: dict[str, Any]) -> Any:
    sms, notes = await asyncio.gather(
        business_api(ctx, "GET", "/sms/management/"),
        business_api(ctx, "GET", "/notifications/"),
    )
    stats = (sms.get("statistics") or [{}])[0]
    return {
        "sms": {
            "enabled": bool(sms.get("business_global_sms_enable")),
            "email_enabled": bool(sms.get("business_global_email_enable")),
            "period": stats.get("period"),
            "free_limit": stats.get("limit_free", sms.get("current_limit_free")),
            "free_used": stats.get("count_free", 0),
            "paid_limit": stats.get("limit_paid", sms.get("current_limit_paid")),
            "paid_used": stats.get("count_paid", 0),
            "price_per_part": sms.get("part_price"),
            "cost_due": stats.get("payable_cost_formatted"),
        },
        "notifications": [
            {
                "code": n.get("code"),
                "name": n.get("name"),
                "channels": [
                    CHANNEL.get(t.get("type"), t.get("type")) for t in n.get("types") or [] if t.get("active")
                ],
            }
            for n in notes.get("notifications") or []
        ],
    }
