"""Reply to review: the owner's public reply under a client's review (also edits an existing reply)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.engagement import business_api
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "review_id": {"type": "integer", "description": "Review ID from list_reviews."},
        "reply": {"type": "string", "minLength": 1, "description": "Reply text, public on your profile."},
    },
    "required": ["review_id", "reply"],
    "additionalProperties": False,
}


@tool(
    name="reply_to_review",
    title="Reply to review",
    access="write",
    confirm=True,
    description="Post or change your public reply to a client's review.",
    details=(
        "Writes your reply under one review on your Booksy profile, the way the Reviews page does. A second "
        "call replaces the reply. Everyone who sees your profile sees it and the reviewer is told, so by "
        "default you confirm each call; you can switch that off for this tool."
    ),
    input_schema=INPUT_SCHEMA,
    route="PUT /reviews/{review_id}/reply",
    example_response={
        "review_id": 4410925,
        "reply": "Thanks Mark, see you next month!",
        "replied_at": "2026-10-15T09:01:00Z",
    },
)
async def reply_to_review(ctx: ToolContext, args: dict[str, Any]) -> Any:
    reply = str(args.get("reply") or "").strip()
    if not reply:
        raise ToolError("reply is empty.", ErrorCode.INVALID_INPUT)
    review_id = int(args["review_id"])
    # The panel sends moment() as JSON: UTC ISO time.
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    found = await business_api(
        ctx, "PUT", f"/reviews/{review_id}/reply/", payload={"reply_content": reply, "reply_updated": now}
    )
    return {
        "review_id": review_id,
        "reply": found.get("reply_content") or reply,
        "replied_at": found.get("reply_updated") or now,
    }
