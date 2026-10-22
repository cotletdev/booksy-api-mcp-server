"""List clients: the Clients page, with search, and Booksy's smart groups with their counts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.clients import CLIENT_EXAMPLE, api, client_out
from booksy_api_mcp.core.helpers import limit, page_cursor
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Name, email or phone to search for."},
        "not_visited_days": {
            "type": "integer",
            "minimum": 1,
            "description": "Only clients whose last visit is older than this many days (or who never visited).",
        },
        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Page size. Default: 50."},
        "cursor": {"type": "string", "description": "next_cursor from the previous call."},
    },
    "required": [],
    "additionalProperties": False,
}


def _older_than(last_visit: str | None, days: int) -> bool:
    if not last_visit:
        return True
    try:
        seen = datetime.fromisoformat(last_visit[:19])
    except ValueError:
        return True
    return seen < datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)


@tool(
    name="list_clients",
    title="List clients",
    access="read",
    confirm=False,
    description="Clients with contact details, visit counts and last visit, plus Booksy's client groups.",
    details=(
        "Reads the Clients list of the business, A to Z: name, email, phone, private note, tags, visits, "
        "no-shows, cancellations, revenue and the last visit. Search by name, email or phone, or keep only "
        "clients who have not visited for a number of days (filtered on each page). `groups` gives Booksy's "
        "smart groups (new, most loyal, slipping away, prospects, upcoming birthdays ...) with their counts."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /clients",
    example_response={
        "clients": [CLIENT_EXAMPLE],
        "total": 1,
        "groups": [
            {
                "group": "new_customers",
                "label": "New Clients",
                "description": "Clients registered in the last 30 days",
                "count": 1,
            }
        ],
        "next_cursor": None,
    },
)
async def list_clients(ctx: ToolContext, args: dict[str, Any]) -> Any:
    page = page_cursor(args.get("cursor"))
    per_page = limit(args, 50, 100)
    found = await api(
        ctx, "GET", "/customers", params={"page": page, "per_page": per_page, "query": args.get("query") or None}
    )
    rows = [client_out(entry) for entry in found.get("customers") or []]
    if days := args.get("not_visited_days"):
        rows = [row for row in rows if _older_than(row["last_visit"], int(days))]
    total = int(found.get("count") or 0)
    groups = await api(ctx, "GET", "/customer_groups")
    return {
        "clients": rows,
        "total": total,
        "groups": [
            {
                "group": g.get("name"),
                "label": g.get("label"),
                "description": g.get("description") or "",
                "count": g.get("count") or 0,
            }
            for g in groups.get("groups") or []
        ],
        "next_cursor": str(page + 1) if page * per_page < total else None,
    }
