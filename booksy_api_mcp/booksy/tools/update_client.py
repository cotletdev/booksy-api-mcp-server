"""Update client: change the name, contact details, birthday or private note of a card."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.clients import CLIENT_EXAMPLE, api, client_out, contact_fields
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "client_id": {"type": "integer", "description": "From list_clients or find_client."},
        "name": {"type": "string", "minLength": 1, "description": "Full name; the last word is the last name."},
        "phone": {"type": "string", "description": "Mobile phone; empty string removes it."},
        "email": {"type": "string", "description": "Email address; empty string removes it."},
        "note": {"type": "string", "description": "Private note, replaces the old one; add_client_note appends."},
        "birthday": {"type": "string", "format": "date", "description": "YYYY-MM-DD."},
    },
    "required": ["client_id"],
    "additionalProperties": False,
}


@tool(
    name="update_client",
    title="Update client",
    access="write",
    confirm=False,
    description="Change a client card's name, phone, email, birthday or private note.",
    details=(
        "Changes only the fields given and leaves the rest of the card as it is. The note replaces the "
        "card's private note; add_client_note adds a line instead. The client is not told."
    ),
    input_schema=INPUT_SCHEMA,
    route="PATCH /clients/{client_id}",
    example_response=CLIENT_EXAMPLE,
)
async def update_client(ctx: ToolContext, args: dict[str, Any]) -> Any:
    body = contact_fields(args)
    if not body:
        raise ToolError("Give at least one field to change.", ErrorCode.INVALID_INPUT)
    path = f"/customers/{int(args['client_id'])}"
    return client_out(
        await api(ctx, "PUT", path, payload=body, not_found="No client card with this ID in this business.")
    )
