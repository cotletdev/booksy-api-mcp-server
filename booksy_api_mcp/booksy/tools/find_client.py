"""Find client: the search box of the Clients page, by name, email or phone."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.clients import CLIENT_EXAMPLE, api, client_out
from booksy_api_mcp.core.helpers import limit
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 2, "description": "Name, email or phone (or a part of one)."},
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 50,
            "description": "Most matches to return. Default: 10.",
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}


@tool(
    name="find_client",
    title="Find client",
    access="read",
    confirm=False,
    description="Client cards matching a name, email or phone.",
    details=(
        "Searches the client list the way the Clients page's search box does and returns the matching cards "
        "with contact details, note and visit counts. A card added a moment ago can take a few seconds to "
        "show up in search; get_client reads it by ID at once."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /clients/search",
    example_response={"clients": [CLIENT_EXAMPLE], "total": 1},
)
async def find_client(ctx: ToolContext, args: dict[str, Any]) -> Any:
    found = await api(
        ctx, "GET", "/customers", params={"page": 1, "per_page": limit(args, 10, 50), "query": args["query"].strip()}
    )
    return {"clients": [client_out(e) for e in found.get("customers") or []], "total": int(found.get("count") or 0)}
