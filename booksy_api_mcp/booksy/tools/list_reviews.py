"""List reviews: the reviews clients left on the business profile, with the owner's replies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.engagement import business_api
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

# The panel's sort keys (profile/reviews, 21.10.2026).
SORTS = {"newest": "D", "highest": "H", "lowest": "L"}

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "sort": {"type": "string", "enum": list(SORTS), "description": "Order. Default: newest."},
        "page": {"type": "integer", "minimum": 1, "description": "Page, from 1. Default: 1."},
        "per_page": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Reviews per page. Default: 20."},
    },
    "required": [],
    "additionalProperties": False,
}

EXAMPLE_REVIEW: dict[str, Any] = {
    "review_id": 4410925,
    "rating": 5,
    "title": "Great cut",
    "text": "Tom took his time and the fade is perfect.",
    "client": "Mark E.",
    "services": ["Haircut"],
    "staff": ["Tom"],
    "appointment_date": "2026-10-14T10:00",
    "created": "2026-10-14T18:22",
    "source": "booksy",
    "photos": 0,
    "reply": "Thanks Mark, see you next month!",
    "replied_at": "2026-10-15T09:01",
}


def review_out(r: dict[str, Any]) -> dict[str, Any]:
    user = r.get("user") or {}
    name = f"{user.get('first_name') or ''} {user.get('last_name') or ''}".strip()
    return {
        "review_id": r.get("id"),
        "rating": r.get("rank"),
        "title": r.get("title") or None,
        "text": r.get("review") or "",
        "client": name or None,
        "services": [s.get("name") for s in r.get("services") or [] if s.get("name")],
        "staff": [s.get("name") for s in r.get("staff") or [] if s.get("name")],
        "appointment_date": r.get("appointment_date"),
        "created": r.get("created"),
        "source": r.get("source"),
        "photos": len(r.get("photos") or []),
        "reply": r.get("reply_content") or None,
        "replied_at": r.get("reply_updated"),
    }


@tool(
    name="list_reviews",
    title="List reviews",
    access="read",
    description="Client reviews of your business with rating, text, services, staff and your reply.",
    details=(
        "Reads the reviews on your Booksy profile, newest first by default: star rating, text, the client's "
        "name as Booksy shows it, services, staff, visit date and your reply if you wrote one. Also returns "
        "the average rating and the count per star. Reply with reply_to_review."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /reviews",
    example_response={
        "reviews": [EXAMPLE_REVIEW],
        "total": 1,
        "average_rating": 5.0,
        "per_rating": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 1},
        "page": 1,
        "next_page": None,
    },
)
async def list_reviews(ctx: ToolContext, args: dict[str, Any]) -> Any:
    page = int(args.get("page") or 1)
    per_page = int(args.get("per_page") or 20)
    found = await business_api(
        ctx,
        "GET",
        "/reviews/",
        params={"reviews_page": page, "reviews_per_page": per_page, "sort": SORTS[args.get("sort") or "newest"]},
    )
    total = int(found.get("reviews_count") or 0)
    return {
        "reviews": [review_out(r) for r in found.get("reviews") or []],
        "total": total,
        "average_rating": found.get("reviews_rank"),
        "per_rating": found.get("num_reviews_per_rank") or {},
        "page": page,
        "next_page": page + 1 if page * per_page < total else None,
    }
