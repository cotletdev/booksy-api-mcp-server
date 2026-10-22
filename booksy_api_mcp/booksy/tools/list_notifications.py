"""List notifications: the panel's in-app notifications (bookings, cancellations, reviews, Booksy news)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.engagement import business_api
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "unread_only": {"type": "boolean", "description": "Only the new ones. Default: false."},
        "page": {"type": "integer", "minimum": 1, "description": "Page, from 1. Default: 1."},
        "per_page": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Per page. Default: 20."},
    },
    "required": [],
    "additionalProperties": False,
}


@tool(
    name="list_notifications",
    title="List notifications",
    access="read",
    description="Notifications from the panel's bell: new bookings, changes, cancellations, reviews.",
    details=(
        "Reads the notifications Booksy shows under the bell in the panel, newest first. Client chat is not "
        "included. Reading does not mark them seen."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /notifications",
    example_response={
        "notifications": [
            {
                "notification_id": 99120331,
                "type": "booking_created",
                "text": "Mark Ellis booked Haircut with Tom on Oct 20 at 10:00",
                "created": "2026-10-18T14:02",
                "unread": True,
            }
        ],
        "total": 1,
        "page": 1,
        "next_page": None,
    },
)
async def list_notifications(ctx: ToolContext, args: dict[str, Any]) -> Any:
    page = int(args.get("page") or 1)
    per_page = int(args.get("per_page") or 20)
    status = "new" if args.get("unread_only") else "active"
    found = await business_api(ctx, "GET", f"/notification_list/{status}/", params={"page": page, "per_page": per_page})
    total = int(found.get("count") or 0)
    return {
        "notifications": [
            {
                "notification_id": n.get("id"),
                "type": n.get("type") or n.get("notification_type") or n.get("code"),
                "text": n.get("text") or n.get("message") or n.get("content") or n.get("title"),
                "created": n.get("created") or n.get("date"),
                "unread": n.get("status") == "new" if n.get("status") else status == "new",
            }
            for n in found.get("notifications") or []
        ],
        "total": total,
        "page": page,
        "next_page": page + 1 if page * per_page < total else None,
    }
