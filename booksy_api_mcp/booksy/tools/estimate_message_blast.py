"""Estimate Message Blast: how many of the chosen clients a blast reaches and what its SMS cost, nothing sent."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.engagement import CHANNELS, audience, business_api, client_ids, estimate
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "channel": {"type": "string", "enum": list(CHANNELS), "description": "email, sms or push."},
        "message": {"type": "string", "minLength": 1, "description": "Message text; its length sets the SMS parts."},
        "client_ids": {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 1,
            "description": "Recipients from list_clients.",
        },
    },
    "required": ["channel", "message", "client_ids"],
    "additionalProperties": False,
}

EXAMPLE_AUDIENCE: dict[str, Any] = {
    "recipients": 43,
    "emails": 43,
    "sms": 0,
    "pushes": 0,
    "sms_parts_per_recipient": 1,
    "sms_cost_total": 0,
    "sms_limit_reached": False,
}


@tool(
    name="estimate_message_blast",
    title="Estimate Message Blast",
    access="read",
    description="Count who a Message Blast would reach and its SMS cost, without sending it.",
    details=(
        "Asks Booksy what send_message_blast would do with the same clients, channel and text: how many "
        "clients it reaches, how many emails, texts or push notifications go out and what the texts cost "
        "beyond the plan's free allowance. Where the law asks for marketing consent (EU), consented counts "
        "only the clients who agreed; send_message_blast sends to those. Nothing is sent."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /message-blasts/estimate",
    example_response={
        "channel": "email",
        "consent_required": True,
        "consented": EXAMPLE_AUDIENCE,
        "all": EXAMPLE_AUDIENCE,
        "sms_allowance": {"free_left": 50, "free_limit": 50, "price_per_part": 0.1},
    },
)
async def estimate_message_blast(ctx: ToolContext, args: dict[str, Any]) -> Any:
    ids = client_ids(args)
    receivers, sms = await asyncio.gather(
        estimate(ctx, ids, args["channel"], args["message"]),
        business_api(ctx, "GET", "/sms/management/"),
    )
    stats = (sms.get("statistics") or [{}])[0]
    free_limit = stats.get("limit_free", sms.get("current_limit_free"))
    return {
        "channel": args["channel"],
        "consent_required": bool(receivers.get("gdpr")),
        "consented": audience(receivers.get("with_gdpr_agreement") or {}),
        "all": audience(receivers.get("without_gdpr_agreement") or {}),
        "sms_allowance": {
            "free_left": max(0, int(free_limit or 0) - int(stats.get("count_free") or 0)),
            "free_limit": free_limit,
            "price_per_part": sms.get("part_price"),
        },
    }
