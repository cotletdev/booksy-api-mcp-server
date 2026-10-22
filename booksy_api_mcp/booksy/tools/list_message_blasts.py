"""List Message Blasts: the automated and one-time templates of Message Blasts and the scheduled sends."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.engagement import business_api
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

# Booksy's automated_status (message_blast/, 21.10.2026); None on one-time templates.
STATUS = {"A": "active", "I": "inactive"}

EXAMPLE_TEMPLATE: dict[str, Any] = {
    "template_id": 4,
    "name": "Invite for the next visit",
    "description": "Sent 21 days after the last visit when no next visit is booked",
    "group": "Reactivate",
    "kind": "automated",
    "status": "inactive",
    "recommended": True,
}


def _templates(group: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """A group's templates, and the groups its link entries point to (one-time messages, occasions)."""
    found, links = [], []
    for t in group.get("business_templates") or []:
        if t.get("link_to_group"):
            links.append(t["link_to_group"])
            continue
        automated = t.get("automated_status")
        found.append(
            {
                "template_id": t.get("id"),
                "name": t.get("name"),
                "description": t.get("description") or None,
                "group": group.get("title"),
                "kind": "automated" if automated else "one_time",
                "status": STATUS.get(automated, automated) if automated else None,
                "recommended": bool(t.get("recommended")),
            }
        )
    return found, links


@tool(
    name="list_message_blasts",
    title="List Message Blasts",
    access="read",
    description="Message Blast templates (automated and one-time) and the blasts scheduled to go out.",
    details=(
        "Reads Promotion > Message Blasts: every automated template with its trigger and whether it is on, "
        "every one-time template, and the blasts scheduled for later. send_message_blast sends a one-time "
        "message; estimate_message_blast counts recipients and SMS cost first."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /message-blasts",
    example_response={
        "templates": [EXAMPLE_TEMPLATE],
        "scheduled": [{"template_id": 15, "name": "Your own message", "scheduled_for": "2026-10-24 08:00"}],
    },
)
async def list_message_blasts(ctx: ToolContext, args: dict[str, Any]) -> Any:
    main, scheduled = await asyncio.gather(
        business_api(ctx, "GET", "/message_blast/"),
        business_api(ctx, "GET", "/message_blast/scheduled/"),
    )
    templates: list[dict[str, Any]] = []
    links: list[str] = []
    for group in main.get("groups") or []:
        found, more = _templates(group)
        templates += found
        links += more
    for linked in await asyncio.gather(*(business_api(ctx, "GET", f"/message_blast/group/{g}/") for g in links)):
        found, _ = _templates(linked.get("group") or {})
        templates += found
    seen: set[Any] = set()
    unique = [t for t in templates if not (t["template_id"] in seen or seen.add(t["template_id"]))]
    return {
        "templates": unique,
        "scheduled": [
            {
                "template_id": b.get("id") or b.get("template_id"),
                "name": b.get("name") or b.get("title"),
                "scheduled_for": " ".join(
                    str(v) for v in (b.get("scheduled_date"), b.get("date_hour")) if v is not None
                )
                or None,
            }
            for b in scheduled.get("message_blasts") or []
        ],
    }
