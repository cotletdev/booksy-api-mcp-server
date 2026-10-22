"""Send Message Blast: one one-time message to chosen clients by email, SMS or push, sent now."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.engagement import CHANNELS, audience, business_api, channel_priority, client_ids, estimate
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "channel": {"type": "string", "enum": list(CHANNELS), "description": "email, sms or push."},
        "message": {"type": "string", "minLength": 1, "description": "Message text."},
        "client_ids": {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 1,
            "description": "Recipients from list_clients.",
        },
        "subject": {"type": "string", "description": "Email subject and push title. Default: the message's start."},
    },
    "required": ["channel", "message", "client_ids"],
    "additionalProperties": False,
}

# The one-time "Create your own message" template (group one_time_message, 21.10.2026).
OWN_MESSAGE = "own_message"


async def _own_template(ctx: ToolContext) -> int:
    group = (await business_api(ctx, "GET", "/message_blast/group/one_time_message/")).get("group") or {}
    for t in group.get("business_templates") or []:
        if t.get("internal_name") == OWN_MESSAGE and t.get("id"):
            return int(t["id"])
    raise ToolError("Booksy offers no one-time message on this account.", ErrorCode.TARGET_ERROR)


@tool(
    name="send_message_blast",
    title="Send Message Blast",
    access="write",
    confirm=True,
    description="Send one message to chosen clients by email, SMS or push notification.",
    details=(
        "Sends one Message Blast now to the clients you list, by email, SMS or a push notification to the Booksy "
        "Client App, as Promotion > Message Blasts > Create your own message does. Where the law asks for "
        "marketing consent (EU), only the listed clients who agreed get it; the call fails when none can. SMS "
        "comes from an automated number, so clients cannot reply, and uses the plan's text allowance. Run "
        "estimate_message_blast first to see the count and cost. Needs a paid Booksy plan: on the free trial Booksy "
        "refuses one-time messages. By default you confirm each call; you can switch that off for this tool."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /message-blasts",
    example_response={"template_id": 15, "channel": "email", "recipients": 3, "sms_cost_total": 0, "status": "sent"},
)
async def send_message_blast(ctx: ToolContext, args: dict[str, Any]) -> Any:
    ids = client_ids(args)
    channel, message = args["channel"], str(args["message"]).strip()
    if not message:
        raise ToolError("message is empty.", ErrorCode.INVALID_INPUT)
    # The estimate checks the ids and gives the count and SMS cost the panel sends with the blast.
    receivers = await estimate(ctx, ids, channel, message)
    consent = bool(receivers.get("gdpr"))
    reach = audience(receivers.get("with_gdpr_agreement" if consent else "without_gdpr_agreement") or {})
    if reach["recipients"] == 0:
        raise ToolError(
            "None of these clients can get this blast: no marketing consent or no "
            f"{'phone' if channel == 'sms' else channel} on the card.",
            ErrorCode.INVALID_INPUT,
        )
    if channel == "sms" and reach["sms_limit_reached"]:
        raise ToolError("The plan's text message allowance is used up.", ErrorCode.TARGET_ERROR)
    template_id = await _own_template(ctx)
    subject = str(args.get("subject") or "").strip() or message.splitlines()[0][:60]
    await business_api(
        ctx,
        "POST",
        f"/message_blast/{template_id}/one_time_send/",
        payload={
            "title": subject,
            "body": message,
            "body_short": message,
            "image": None,
            "recipients": {"ids": ids, "excluded": [], "with_agreements": consent},
            "channel_priority": channel_priority(channel),
            "estimated_sms_cost": reach["sms_cost_total"],
        },
    )
    return {
        "template_id": template_id,
        "channel": channel,
        "recipients": reach["recipients"],
        "sms_cost_total": reach["sms_cost_total"],
        "status": "sent",
    }
